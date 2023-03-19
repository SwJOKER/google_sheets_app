import hashlib
import json
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from decimal import Decimal


def get_sheet_md5(sheet):
    records = sheet.get_all_records()
    return hashlib.md5(json.dumps(records).encode('UTF-8')).hexdigest()


def str_to_date(value):
    try:
        return datetime.strptime(value, '%d.%m.%Y')
    except TypeError:
        return str(value)


def request_dollar_course():
    courses = requests.get('https://www.cbr.ru/scripts/XML_daily.asp')
    root = ET.fromstring(courses.text)
    for tag in root.findall('Valute'):
        if tag.attrib['ID'] == 'R01235':
            res = [x for x in list(tag) if x.tag == 'Value'][0].text.replace(',', '.')
            res = Decimal(res).quantize(Decimal("1.00"))
            return res
