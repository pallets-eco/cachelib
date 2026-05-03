import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import ValkeyCache


class SillySerializer:
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
class TestValkeyCache(CommonTests, ClearTests, HasTests):
    def test_callable_key(self):
        cache = self.cache_factory()
        assert cache.set(my_callable_key, "sausages")
        assert cache.get(my_callable_key) == "sausages"
        assert cache.set(lambda: "spam", "sausages")
        assert cache.get(lambda: "spam") == "sausages"

    def test_delete_many_with_prefix(self):
        cache = self.cache_factory(key_prefix="test_prefix:")
        cache.set_many({"foo": 1, "bar": 2, "baz": 3})
        result = cache.delete_many("foo", "bar", "baz")
        assert result == ["foo", "bar", "baz"]
        assert not any(cache.get_many("foo", "bar", "baz"))
