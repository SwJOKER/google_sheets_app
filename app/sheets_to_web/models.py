from django.core.validators import MinLengthValidator
from django.db import models

from .celery import check_sheet_availability


class Order(models.Model):
    # Index is not required for my opinion, but task terms declare that table must be as in sheet
    row_index = models.IntegerField('Row index', null=False)
    order_index = models.IntegerField('Order index', null=False)
    cost = models.DecimalField('Dollar cost', decimal_places=2, max_digits=12, null=False)
    # I think this field is excess. No sense to store it in DB, considering that we have currency courses api.
    # And keep it in radis cache, or just as var
    cost_ruble = models.DecimalField('Ruble cost', decimal_places=2, max_digits=12, null=False)
    delivery_date = models.DateField('Delivery date', null=False)
    delivery_expired = models.BooleanField(null=False, default=False)
    sheet = models.ForeignKey('Sheet', related_name='orders', null=False, on_delete=models.CASCADE)

    def get_vals_tuple(self):
        return self.row_index, self.order_index, self.cost, self.delivery_date


class SheetError(models.Model):
    sheet = models.ForeignKey('Sheet', related_name='errors', null=False, on_delete=models.CASCADE)
    error_text = models.CharField(verbose_name='Error', max_length=256)

    def __str__(self):
        return self.error_text


class Sheet(models.Model):
    name = models.CharField(verbose_name='sheet name', max_length=1000, null=False, default='No name')
    key = models.CharField('sheet key', null=False, max_length=44, validators=[MinLengthValidator(44)],
                           primary_key=True)
    available = models.BooleanField(null=True, default=None)
    md5 = models.CharField(null=True, max_length=32, default=None)

    def save(self, from_task=None, *args, **kwargs):
        super().save(*args, **kwargs)
        if not from_task:
            check_sheet_availability.delay(self.key)


class TelegramSubscriber(models.Model):
    chat_id = models.IntegerField(null=False)
    sheets = models.ManyToManyField('Sheet', related_name='subscribers')
