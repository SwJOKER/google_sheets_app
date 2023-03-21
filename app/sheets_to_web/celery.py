import logging
import os
from _decimal import Decimal

from celery import signals
import googleapiclient
import pygsheets
from celery import Celery, Task, group
from celery.schedules import crontab
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.utils import timezone
from .utils import get_sheet_records_md5, str_to_date, request_dollar_course, get_aware_update_time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('sheets_to_web')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@signals.worker_ready.connect
def on_start(**kwargs):
    get_dollar_course.s()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(10.0, start_update_sheets.s(), name='Update data from sheets')

    if settings.DEBUG:
        sender.add_periodic_task(10.0, check_delivery_date.s(), name='Delivery notifications debug mode')
    else:
        # at start of workday
        sender.add_periodic_task(
            crontab(hour=7, minute=0),
            check_delivery_date.s(),
            name='Delivery notifications'
        )
    sender.add_periodic_task(
        crontab(hour=0, minute=1),
        get_dollar_course.s(force=True),
        name="Get Dollar's Course"
    )


class SheetTask(Task):
    _client = None

    # init google sheets client
    @property
    def client(self):
        if self._client is None:
            self._client = pygsheets.authorize(service_file=settings.SHEETS_JSON_KEY)
        return self._client


@app.task
def check_delivery_date():
    from .models import Sheet, Order

    expired_sheets_keys = list()
    prefetch_current_orders = Prefetch('orders', queryset=Order.objects.filter(archieved=False))
    sheets = Sheet.objects.filter(available=True).prefetch_related(prefetch_current_orders)
    print('check start')
    for sheet in sheets:
        print('Check delivery')
        # delivery status updates in telegram worker on sending notificates
        expired = [order.order_index for order in sheet.orders.all()
                   if order.delivery_date < timezone.now().date() and not order.delivery_expired]
        # Store pks of sheets and orders in redis cache for notificate
        if expired:
            print('find expired')
            cache.set(f'expired_{sheet.key}', expired, 60 * 60 * 3)
            expired_sheets_keys.append(sheet.key)
    print('Send to telegram')
    cache.set('expired_sheets_keys', expired_sheets_keys, 60 * 60 * 3)


# calls when Sheet model object saved
@app.task(base=SheetTask, bind=True)
def check_sheet_availability(self, sheet_key):
    # avoid recursion import
    from .models import Sheet

    sheet = Sheet.objects.filter(key=sheet_key).first()
    try:
        ws = self.client.open_by_key(sheet_key)
        sheet.name = ws.title
        sheet.available = True
        sheet.save(from_task=True)
    except googleapiclient.errors.HttpError:
        sheet.delete()
        print('Sheet is not available')


# store course to redis cache
# scheduled cron task forced updates cache at midnight, when central bank drops new data
# also it updated on restart celery
@app.task
def get_dollar_course(force=False):
    if not force and cache.get('dollar_course'):
        return cache.get('dollar_course')
    else:
        course = request_dollar_course()
        cache.set('dollar_course', course, 60 * 60 * 24)
        return course


# start update tasks for available sheets
@app.task
def start_update_sheets():
    # avoid recursion import
    from .models import Sheet

    # get accessible sheets
    sheets = Sheet.objects.filter(available=True)
    # starts task group. We can scale project by making multiply celery workers
    group(update_sheet.s(sheet.key) for sheet in sheets).apply_async()


class UpdateSheetDBTask(SheetTask):

    # __init__ constructor will only be called once per process
    def init_sheet(self, sheet_key):
        from .models import Sheet, Order

        self._dollar_course = get_dollar_course.s()()
        self._spreadsheet = self.client.open_by_key(sheet_key)
        self._worksheet = self._spreadsheet.sheet1
        self._worksheet_records = self._worksheet.get_all_records()
        self._last_update_time = get_aware_update_time(self._spreadsheet)
        self._md5 = get_sheet_records_md5(self._worksheet_records)
        self._sheet_data_dict = {tuple(r.values())[1]: tuple(r.values()) for r in self._worksheet_records
                                 if all(r.values())}
        self._actual_orders_id_list = list(self._sheet_data_dict.keys())
        actual_orders = Prefetch('orders', queryset=Order.objects.filter(order_index__in=self._actual_orders_id_list))
        self._sheet = Sheet.objects.filter(key=sheet_key).prefetch_related(actual_orders).first()
        self._errors_objects = list()

    def start(self, sheet_key, only_checksum=True):
        self.init_sheet(sheet_key)
        if not only_checksum:
            changed = self.have_updates_by_time()
        else:
            changed = self.have_updates_by_checksum()
        if changed:
            # call order in this section is important.
            self.update_orders()
            self.create_orders()
            self.archieve_orders()
            self.save_errors()
            self._sheet.save(from_task=True)

    # api updates update time too long. Checking only checksum is more faster.
    # if sheet is not too big checksum is better
    def have_updates_by_time(self):
        sheet = self._sheet
        if sheet.update_datetime is None or sheet.update_datetime < self._last_update_time:
            sheet.update_datetime = self._last_update_time
            # additional check md5 hash for changes in sheet, skip if not updates
            if self._md5 == sheet.md5:
                sheet.update('update_datetime')
                return False
            else:
                sheet.errors.all().delete()
                sheet.md5 = self._md5
                return True
        else:
            return False

    def have_updates_by_checksum(self):
        if self._md5 == self._sheet.md5:
            return False
        self._sheet.errors.all().delete()
        self._sheet.md5 = self._md5
        return True

    def update_orders(self):
        from .models import SheetError, Order

        update_objs = list()
        for order in self._sheet.orders.all():
            # extracts processed data from dict, as result there will remain only new data
            order_data = self._sheet_data_dict.pop(order.order_index, None)
            if order_data and (order.get_vals_tuple() != order_data or order.archieved):
                # return order from archieve if it is in sheet
                order.archieved = False
                order.row_index = order_data[0]
                order.cost = order_data[2]
                order.delivery_date = str_to_date(order_data[3])
                cost_ruble = Decimal(order.cost * self._dollar_course).quantize(Decimal('1.00'))
                order.cost_ruble = cost_ruble
                try:
                    order.clean_fields()
                    update_objs.append(order)
                except ValidationError as e:
                    self._errors_objects.append(SheetError(sheet=self._sheet,
                                                           error_text=f'Order {order.order_index}: {e.messages}'))
        Order.objects.bulk_update(update_objs, fields=['archieved', 'row_index', 'cost', 'delivery_date'])

    def create_orders(self):
        from .models import SheetError, Order

        create_objs = list()
        # in _sheet_data_dict remained only new data
        for new_order_data in self._sheet_data_dict.values():
            # order of fields in new order data
            fields_in_tuple = ('row_index', 'order_index', 'cost', 'delivery_date')
            # make dict with pairs attribute:value
            kwargs_for_order = dict(zip(fields_in_tuple, new_order_data))
            # convert date string in tuple to date format
            kwargs_for_order['delivery_date'] = str_to_date(new_order_data[3])
            kwargs_for_order['sheet'] = self._sheet
            cost_ruble = Decimal(new_order_data[2] * self._dollar_course).quantize(Decimal('1.00'))
            new_order = Order(cost_ruble=cost_ruble, **kwargs_for_order)
            try:
                new_order.clean_fields()
                create_objs.append(new_order)
            except ValidationError as e:
                self._errors_objects.append(SheetError(sheet=self._sheet, error_text=e.messages))
        Order.objects.bulk_create(create_objs)

    def archieve_orders(self):
        from .models import Order

        Order.objects.filter(sheet=self._sheet).exclude(order_index__in=self._actual_orders_id_list)\
                                               .exclude(archieved=True)\
                                               .update(archieved=True)

    def save_errors(self):
        from .models import SheetError

        SheetError.objects.bulk_create(self._errors_objects)


@app.task(bind=True, base=UpdateSheetDBTask)
def update_sheet(self, sheet_key):
    self.start(sheet_key)


@app.task(bind=True)
def debug_task(self):
    print('Request: {}'.format(self.request))
