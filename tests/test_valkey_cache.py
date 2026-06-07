import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib import ValkeyCache
from cachelib.serializers import BaseSerializer


class SillySerializer(BaseSerializer):
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        if bvalue is None:
            return None
        return eval(bvalue.decode())


class CustomCache(ValkeyCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True, params=[ValkeyCache, CustomCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = request.param(*args, port=6370, **kwargs)
        rc._write_client.flushdb()
        return rc

    request.cls.cache_factory = _factory


def my_callable_key() -> str:
    return "bacon"


@pytest.mark.usefixtures("valkey_server")
class TestValkeyCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    def test_callable_key(self):
        cache = self.cache_factory()
        assert cache.set(my_callable_key, "sausages")
        assert cache.get(my_callable_key) == "sausages"
        assert cache.set(lambda: "spam", "sausages")
        assert cache.get(lambda: "spam") == "sausages"
