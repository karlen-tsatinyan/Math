from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")


def today():
    return datetime.now(PACIFIC).date()


def today_str():
    return str(today())


def now():
    return datetime.now(PACIFIC)