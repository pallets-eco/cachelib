from cachelib.base import BaseCache
from cachelib.base import NullCache
from cachelib.file import FileSystemCache
from cachelib.memcached import MemcachedCache
from cachelib.redis import RedisCache
from cachelib.simple import SimpleCache
from cachelib.uwsgi import UWSGICache

__all__ = [
    "BaseCache",
    "NullCache",
    "SimpleCache",
    "FileSystemCache",
    "MemcachedCache",
    "RedisCache",
    "UWSGICache",
]
__version__ = "0.2.0"


import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())
