import datetime


def get_local_date():
    return datetime.datetime.now().strftime("%Y-%m-%d")
