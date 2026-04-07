import warnings
import functools

import numpy
import inspect

class cache:
    """ decorator to catch all unhandled exceptions, log them and discard them"""
    def __init__(self, func):
        self.func = func
        self.v = False
        self.y = 0
        self.n = 0
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        if self.v:
            return self.c
        self.c = self.func(*args, **kwargs)
        self.v = True
        return self.c

    def reset(self):
        self.v = False


def calc_fun(fun, value):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return fun(value)


class MovingValue:
    """Class containing a list of moving value, with easy access for calculating various statistics."""
    def __init__(self, size):
        super().__init__()
        self.set_size(size)
        self.accessors = []
        self._current = self.add_accessor(cache(lambda: self._value[0]))
        self._mean = self.add_accessor(cache(lambda: calc_fun(numpy.nanmean, self._value)))
        self._min = self.add_accessor(cache(lambda: calc_fun(numpy.nanmin, self._value)))
        self._max = self.add_accessor(cache(lambda: calc_fun(numpy.nanmax, self._value)))
        self._std_dev = self.add_accessor(cache(lambda: calc_fun(numpy.nanstd, self._value)))
        self._variation = self.add_accessor(cache(lambda: calc_fun(numpy.nanvar, self._value)))

    def add_accessor(self, a):
        self.accessors.append(a)
        return a

    def set_size(self, size):
        """Change window size"""
        self._value = numpy.zeros(size)
        self.clear()

    def clear(self):
        """Clear data"""
        self._value[:] = numpy.nan

    def add(self, value):
        """Add data point"""
        orig = self._value
        modified = numpy.roll(orig, 1)
        modified[0] = value
        self._value = modified
        for a in self.accessors:
            a.reset()

    @property
    def current(self):
        """Last data point value"""
        return self._current()

    @property
    def mean(self):
        return self._mean()

    @property
    def min(self):
        return self._min()

    @property
    def max(self):
        return self._max()

    @property
    def std_dev(self):
        return self._std_dev()

    @property
    def variation(self):
        return self._variation()

    def __str__(self):
        return "c={:.2f} avg={:.2f} std={:.3f} min={:.2f} max={:.2f}".format(self.current, self.mean, self.std_dev, self.min, self.max)
