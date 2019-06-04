# -*- coding: utf-8 -*-

from cachelib.base import BaseCache, NullCache
from cachelib.simple import SimpleCache
from cachelib.file import FileSystemCache
from cachelib.memcached import MemcachedCache
from cachelib.redis import RedisCache
from cachelib.s3 import S3Cache
from cachelib.uwsgi import UWSGICache

__all__ = [
    "BaseCache",
    "NullCache",
    "SimpleCache",
    "FileSystemCache",
    "MemcachedCache",
    "RedisCache",
    "S3Cache",
    "UWSGICache",
]

__version__ = "0.2"
__author__ = "Pallets Team"
