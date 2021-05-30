import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import UWSGICache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        uwc = UWSGICache(*args, **kwargs)
        uwc.clear()
        return uwc

    request.cls.cache_factory = _factory


class TestUwsgiCache(CommonTests, ClearTests, HasTests):
    pytest.importorskip(
        "uwsgi",
        reason="could not import 'uwsgi'. Make sure to "
        "run pytest under uwsgi for testing UWSGICache",
    )
