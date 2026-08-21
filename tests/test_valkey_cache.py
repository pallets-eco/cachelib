import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib import ValkeyCache
from cachelib.serializers import BaseRedisSerializer


class SillySerializer(BaseRedisSerializer):
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
def cache_factory(request, key_prefix):
    def _factory(self, *args, **kwargs):
        kwargs.setdefault("key_prefix", key_prefix)
        rc = request.param(*args, port=6370, **kwargs)
        rc._write_client.flushdb()
        return rc

    request.cls.cache_factory = _factory


def my_callable_key() -> str:
    return "bacon"


@pytest.mark.network
@pytest.mark.usefixtures("valkey_server")
class TestValkeyCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    def test_callable_key(self):
        cache = self.cache_factory()
        assert cache.set(my_callable_key, "sausages")
        assert cache.get(my_callable_key) == "sausages"
        spam_key = lambda: "spam"  # noqa: E731
        assert cache.set(spam_key, "sausages")
        assert cache.get(spam_key) == "sausages"


class TestValkeyCacheCheckConnection:
    # nothing listens on port 1, so connections are refused immediately
    def test_unreachable_server_raises_when_enabled(self):
        with pytest.raises(RuntimeError, match="could not connect to Valkey"):
            ValkeyCache(port=1, check_connection=True, socket_connect_timeout=0.1)

    def test_unreachable_server_is_lazy_by_default(self):
        cache = ValkeyCache(port=1, socket_connect_timeout=0.1)
        assert isinstance(cache, ValkeyCache)


@pytest.mark.network
@pytest.mark.usefixtures("valkey_server")
class TestValkeyCacheCheckConnectionLive:
    def test_reachable_server_constructs_and_works(self):
        cache = ValkeyCache(port=6370, check_connection=True)
        assert cache.set("check-connection-key", "value")
        assert cache.get("check-connection-key") == "value"
