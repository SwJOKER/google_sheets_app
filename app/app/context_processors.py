import os


def export_vars(request):
    data = dict()
    url = f"http://{os.getenv('API_URL', default='localhost:8000')}/api/sheets/"
    data['API_URL'] = url
    return data
