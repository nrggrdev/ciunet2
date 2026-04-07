import importlib

from .StringToBoolean import str2bool


def convert(value, type_):
    """Converts value to type_ specified as string"""
    if type_ == "bool":
        return str2bool(value)
    try:
        # Check if it's a builtin type
        module = importlib.import_module('builtins')
        cls = getattr(module, type_)
    except AttributeError:
        # if not, separate module and class
        module, type_ = type_.rsplit(".", 1)
        module = importlib.import_module(module)
        cls = getattr(module, type_)
    except Exception as e:
        print(e, type(e))
    return cls(value)
