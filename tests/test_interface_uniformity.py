# type: ignore
import inspect

import pytest

from cachelib import BaseCache
from cachelib import FileSystemCache
from cachelib import MemcachedCache
from cachelib import RedisCache
from cachelib import SimpleCache


@pytest.fixture(autouse=True)
def create_cache_list(request, tmpdir):
    mc = MemcachedCache()
    mc._client.flush_all()
    rc = RedisCache(port=6360)
    rc._client.flushdb()
    request.cls.cache_list = [FileSystemCache(tmpdir), mc, rc, SimpleCache()]


@pytest.mark.usefixtures("redis_server", "memcached_server")
class TestInterfaceUniformity:
    def test_types_have_all_base_methods(self):
        public_api_methods = [
            meth
            for meth in inspect.getmembers(BaseCache, predicate=inspect.isfunction)
            if not meth[0].startswith("_")
        ]
        for cache_type in self.cache_list:
            for meth in public_api_methods:
                assert hasattr(cache_type, meth[0]) and callable(meth[1])
