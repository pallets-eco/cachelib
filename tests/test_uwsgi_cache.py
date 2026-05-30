import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import UWSGICache


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        return eval(bvalue.decode())


class CustomCache(UWSGICache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True, params=[UWSGICache, CustomCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        uwc = request.param(*args, **kwargs)
        uwc.clear()
        return uwc

    request.cls.cache_factory = _factory


class TestUwsgiCache(CommonTests, ClearTests, HasTests):
    pytest.importorskip(
        "uwsgi",
        reason="could not import 'uwsgi'. Make sure to "
        "run pytest under uwsgi for testing UWSGICache",
    )
