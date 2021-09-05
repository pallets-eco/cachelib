import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import RedisCache
from cachelib.serializers import RedisSerializer


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        if bvalue is None:
            return None
        return eval(bvalue.decode())


@pytest.fixture(autouse=True, params=[RedisSerializer, SillySerializer])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = RedisCache(*args, port=6360, serializer=request.param(), **kwargs)
        rc._client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("redis_server")
class TestRedisCache(CommonTests, ClearTests, HasTests):
    pass
