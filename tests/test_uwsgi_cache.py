import pytest
from conftest import ClearTests
from conftest import CommonTests
from conftest import HasTests

from cachelib import UWSGICache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        uwc = UWSGICache(*args, **kwargs)
        uwc.clear()
        return uwc

    request.cls.cache_factory = _factory


class TestUwsgiCache(CommonTests, ClearTests, HasTests):
    pytest.importorskip("uwsgi")
