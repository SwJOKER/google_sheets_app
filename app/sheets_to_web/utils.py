import hashlib
import json
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from decimal import Decimal

from django.utils import timezone
from pygsheets import Spreadsheet


def get_sheet_records_md5(records):
    return hashlib.md5(json.dumps(records).encode('UTF-8')).hexdigest()


def get_aware_update_time(sheet: Spreadsheet):
    return timezone.datetime.fromisoformat(sheet.updated[:-1]).astimezone(timezone.get_default_timezone())


def str_to_date(value):
    try:
        return datetime.strptime(value, '%d.%m.%Y').date()
    except TypeError:
        return str(value)


def to_db_formats(order_data: tuple):
    return order_data[0], order_data[1], Decimal(order_data[2]).quantize(Decimal('1.00')), str_to_date(order_data[3])


def request_dollar_course():
    courses = requests.get('https://www.cbr.ru/scripts/XML_daily.asp')
    root = ET.fromstring(courses.text)
    for tag in root.findall('Valute'):
        if tag.attrib['ID'] == 'R01235':
            res = [x for x in list(tag) if x.tag == 'Value'][0].text.replace(',', '.')
            res = Decimal(res).quantize(Decimal("1.00"))
            return res
