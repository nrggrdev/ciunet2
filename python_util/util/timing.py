import datetime

from contextlib import contextmanager


@contextmanager
def timeit(name, writer=print):
    start = datetime.datetime.now()
    yield
    end = datetime.datetime.now()
    writer("Section '{}' took {}.".format(name, end - start))
