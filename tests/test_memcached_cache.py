import pytest
from conftest import ClearTests
from conftest import CommonTests
from conftest import HasTests

from cachelib import MemcachedCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        mc = MemcachedCache(*args, **kwargs)
        mc._client.flush_all()
        return mc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("memcached_server")
class TestMemcachedCache(CommonTests, ClearTests, HasTests):
    pass
