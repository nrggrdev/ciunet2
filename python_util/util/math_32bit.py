"""
Small helper library for 32bit integer math simulation
"""

M32 = 0xffffffff


def m32(n):
    return n & M32


def madd(a, b):
    return m32(a + b)


def msub(a, b):
    return m32(a - b)


def mls(a, b):
    return m32(a << b)
