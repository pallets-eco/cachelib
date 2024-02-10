import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import MemcachedCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        mc = MemcachedCache(*args, **kwargs)
        if mc.pylibmc_used:
            with mc._client.reserve(block=mc.blocking) as client:
                client.flush_all()
        else:
            mc._client.flush_all()
        return mc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("memcached_server")
class TestMemcachedCache(CommonTests, ClearTests, HasTests):
    pass
