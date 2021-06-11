# flake8: noqa
import sys

text_type = str
string_types = (str,)
integer_types = (int,)
iteritems = lambda d, *args, **kwargs: iter(d.items(*args, **kwargs))


def to_native(x, charset=sys.getdefaultencoding(), errors="strict"):
    if x is None or isinstance(x, str):
        return x
    return x.decode(charset, errors)
