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
from django.utils import timezone

from .utils import get_sheet_md5, str_to_date, request_dollar_course

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
    sender.add_periodic_task(
        crontab(hour=0, minute=1),
        check_delivery_date.s(),
        name='Delivery notifications'
    )
    sender.add_periodic_task(
        crontab(hour=0, minute=1),
        get_dollar_course.s(force=True),
        name="Get Dollar's Course"
    )


class SheetUpdateTask(Task):
    _client = None

    # init google sheets client
    @property
    def client(self):
        if self._client is None:
            self._client = pygsheets.authorize(service_file=settings.SHEETS_JSON_KEY)
        return self._client


@app.task
def check_delivery_date():
    from .models import Sheet

    expired_sheets_keys = list()
    sheets = Sheet.objects.filter(available=True).prefetch_related('orders')
    for sheet in sheets:
        # delivery status updates in telegram worker on sending notificates
        expired = [order.order_index for order in sheet.orders.all()
                   if order.delivery_date < timezone.now().date() and not order.delivery_expired]
        print(expired)
        # Store sheets and orders for notificate in redis cache
        if expired:
            cache.set(f'expired_{sheet.key}', expired, 60*60*3)
            expired_sheets_keys.append(sheet.key)
    print(expired_sheets_keys)
    cache.set('expired_sheets_keys', expired_sheets_keys, 60*60*3)


# calls when Sheet model object saved
@app.task(base=SheetUpdateTask, bind=True)
def check_sheet_availability(self, sheet_key):
    # avoid recursion import
    from .models import Sheet

    try:
        sheet = Sheet.objects.filter(key=sheet_key).first()
        ws = self.client.open_by_key(sheet_key)
        sheet.name = ws.title
        sheet.available = True
        sheet.save(from_task=True)
    except googleapiclient.errors.HttpError:
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
        cache.set('dollar_course', course, 60*60*24)
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


@app.task(bind=True, base=SheetUpdateTask)
def update_sheet(self, sheet_key):
    # avoid recursion import
    from .models import Sheet, Order, SheetError

    sheet = Sheet.objects.filter(key=sheet_key).prefetch_related('orders').first()
    dollar_course = get_dollar_course.s()()
    worksheet = self.client.open_by_key(sheet.key).sheet1
    # check md5 hash for changes in sheet, skip if not updates
    md5_checksum = get_sheet_md5(worksheet)
    if md5_checksum == sheet.md5:
        return
    else:
        sheet.errors.all().delete()
        sheet.md5 = md5_checksum
    # make dict where order_index is key, tuple of cells data is value
    sheet_data = {tuple(r.values())[1]: tuple(r.values()) for r in worksheet.get_all_records()}
    actual_orders_list = list(sheet_data.keys())
    update_objs = list()
    # update order if updates exist
    errors_objs = list()
    for order in sheet.orders.all():
        # extracts processed data from dict, as result there will remain only new data
        order_data = sheet_data.pop(order.order_index, None)
        if order.get_vals_tuple() != order_data:
            order.row_index = order_data[0]
            order.cost = order_data[2]
            order.delivery_date = str_to_date(order_data[3])
            cost_ruble = Decimal(order.cost * dollar_course).quantize(Decimal('1.00'))
            order.cost_ruble = cost_ruble
            try:
                order.clean_fields()
                update_objs.append(order)
            except ValidationError as e:
                errors_objs.append(SheetError(sheet=sheet, error_text=e.messages))
    create_objs = list()
    # in sheet_data remained only new data
    for new_order_data in sheet_data.values():
        # order of fields in new order data
        fields_in_tuple = ('row_index', 'order_index', 'cost', 'delivery_date')
        # make dict with pairs attribute:value
        kwargs_for_order = dict(zip(fields_in_tuple, new_order_data))
        # convert date string in tuple to date format
        kwargs_for_order.update({'delivery'})
        kwargs_for_order['delivery_date'] = str_to_date(new_order_data[3])
        kwargs_for_order['sheet'] = sheet
        cost_ruble = Decimal(new_order_data[2] * dollar_course).quantize(Decimal('1.00'))
        new_order = Order(cost_ruble=cost_ruble, **kwargs_for_order)
        try:
            new_order.clean_fields()
            create_objs.append(new_order)
        except ValidationError as e:
            errors_objs.append(SheetError(sheet=sheet, error_text=e.messages))
    # save changes in DB
    Order.objects.bulk_create(create_objs)
    Order.objects.bulk_update(update_objs, fields=['row_index', 'cost', 'delivery_date'])
    SheetError.objects.bulk_create(errors_objs)
    # drop deleted rows from DB
    sheet.orders.exclude(order_index__in=actual_orders_list).delete()
    sheet.save()


@app.task(bind=True)
def debug_task(self):
    print('Request: {}'.format(self.request))

