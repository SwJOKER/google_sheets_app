import hashlib
import json
import pygsheets


def get_sheet():
    # Use a breakpoint in the code line below to debug your script.
    client = pygsheets.authorize(service_file='service-key.json')
    z = client.open_by_key('1MuMERz8I1Qd8Ip4DB8UrbPD4fgdSbmE-YVMPistsqkE')
    z = z.sheet1.get_all_records()
    print(z)
    print(hashlib.md5(json.dumps(z).encode('UTF-8')).hexdigest())


class Sheet:
    client = pygsheets.authorize(service_file='service-key.json')

    # must be only one of arguments sheet_id or sheet_name. Default - sheet1
    def __init__(self, key, sheet_id: int=None, sheet_name: str=''):
        self.wokrsheet = self.client.open_by_key(key)
        self.spreadsheet = self.wokrsheet


