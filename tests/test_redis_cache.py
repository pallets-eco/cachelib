import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import RedisCache


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        if bvalue is None:
            return None
        return eval(bvalue.decode())


class CustomCache(RedisCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True, params=[RedisCache, CustomCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = request.param(*args, port=6360, **kwargs)
        rc._write_client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("redis_server")
class TestRedisCache(CommonTests, ClearTests, HasTests):
    pass
