import unittest
import random

import numpy

from python_util.util import MovingValue


class TestMovingValue(unittest.TestCase):
    def test_average(self):
        for i in [5, 10]:
            for k in [2, 5, 8, 10, 13]:
                with self.subTest(i=i, k=k):
                    # Moving value able to hold i elements
                    m = MovingValue.MovingValue(i)

                    # Generate k elements ( might be smaller or larget than i) and stuff them into m
                    values = [random.randrange(100) for _ in range(k)]
                    for value in values:
                        m.add(value)

                    # Check that last min(i, k) values match
                    self.assertEqual(m.mean, numpy.mean(values[-min(i, k):]))
