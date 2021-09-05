# type: ignore
import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import UWSGICache
from cachelib.serializers import UWSGISerializer


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        return eval(bvalue.decode())


@pytest.fixture(autouse=True, params=[UWSGISerializer, SillySerializer])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        uwc = UWSGICache(*args, serializer=request.param(), **kwargs)
        uwc.clear()
        return uwc

    request.cls.cache_factory = _factory


class TestUwsgiCache(CommonTests, ClearTests, HasTests):
    pytest.importorskip(
        "uwsgi",
        reason="could not import 'uwsgi'. Make sure to "
        "run pytest under uwsgi for testing UWSGICache",
    )
