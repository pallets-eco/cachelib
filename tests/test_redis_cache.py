import pytest
from conftest import ClearTests
from conftest import CommonTests
from conftest import HasTests

from cachelib import RedisCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = RedisCache(*args, **kwargs)
        rc._client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("redis_server")
class TestRedisCache(CommonTests, ClearTests, HasTests):
    pass
