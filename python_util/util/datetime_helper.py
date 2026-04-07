import datetime
import logging

from dateutil import tz


def current_local_time():
    return datetime.datetime.now(tz=tz.tzlocal())


def current_utc_time():
    return datetime.datetime.now(tz=tz.tzutc())


class LoggingFormatter(logging.Formatter):
    def formatTime(self, record, _datefmt=None):
        dt = datetime.datetime.fromtimestamp(record.created, tz=tz.tzlocal())
        try:
            if self.hide_subseconds:
                dt = dt.replace(microsecond=0)
        except Exception:
            pass
        return str(dt)
