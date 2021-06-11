import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import RedisCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = RedisCache(*args, port=6360, **kwargs)
        rc._client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("redis_server")
class TestRedisCache(CommonTests, ClearTests, HasTests):
    pass
