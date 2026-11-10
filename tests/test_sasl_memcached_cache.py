import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib import SASLMemcachedCache
from cachelib import SpreadSASLMemcachedCache


@pytest.fixture(
    params=["pylibmc", "memcache"],
    ids=["pylibmc", "python-memcached"],
)
def memcache_client_lib(request):
    pytest.importorskip(request.param, reason=f"{request.param} not installed")
    return request.param


@pytest.fixture
def cache_factory(request, key_prefix, memcache_client_lib):
    caches = []

    def _factory(self, *args, **kwargs):
        kwargs.setdefault("servers", ["127.0.0.1:11212"])
        kwargs.setdefault("key_prefix", key_prefix)
        kwargs.setdefault("memcache_client_lib", memcache_client_lib)
        cache = self.cache_class(*args, **kwargs)
        cache.clear()
        caches.append(cache)
        return cache

    request.cls.cache_factory = _factory
    yield
    for cache in caches:
        # close python-memcached sockets to avoid ResourceWarning noise
        disconnect = getattr(cache._client, "disconnect_all", None)
        if disconnect is not None:
            disconnect()


@pytest.mark.network
@pytest.mark.usefixtures("memcached_server", "cache_factory")
class TestSASLMemcachedCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests
):
    cache_class = SASLMemcachedCache

    def test_bool_roundtrip(self):
        # pylibmc flags bool as int on the wire so bools round-trip as 1/0;
        # python-memcached pickles them, preserving bool.
        cache = self.cache_factory()
        assert cache.set("true-key", True)
        assert cache.get("true-key") == 1
        assert cache.set("false-key", False)
        assert cache.get("false-key") == 0


@pytest.mark.network
@pytest.mark.usefixtures("memcached_server", "cache_factory")
class TestSpreadSASLMemcachedCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    cache_class = SpreadSASLMemcachedCache

    def test_value_is_spread_across_chunks(self):
        cache = self.cache_factory(chunksize=16)
        value = "x" * 100
        assert cache.set("key", value)
        assert cache.get("key.0", chunk=False) is not None
        assert cache.get("key.1", chunk=False) is not None
        assert cache.get("key") == value

    def test_smaller_value_replaces_bigger_value(self):
        cache = self.cache_factory(chunksize=32)
        assert cache.set("key", "x" * 100)
        assert cache.set("key", "y")
        assert cache.get("key.1", chunk=False) is None
        assert cache.get("key") == "y"

    def test_value_bigger_than_maxchunk_raises(self):
        cache = self.cache_factory(chunksize=16, maxchunk=2)
        with pytest.raises(ValueError, match="Cannot store value"):
            cache.set("key", "x" * 100)

    def test_unchunked_roundtrip(self):
        cache = self.cache_factory()
        assert cache.set("key", "value", chunk=False)
        assert cache.get("key", chunk=False) == "value"
        assert cache.get("key") is None

    def test_add_does_not_replace_spread_value(self):
        cache = self.cache_factory(chunksize=16)
        assert cache.add("key", "x" * 100)
        assert not cache.add("key", "y")
        assert cache.get("key") == "x" * 100

    def test_has_and_delete_spread_value(self):
        cache = self.cache_factory(chunksize=16)
        assert cache.set("key", "x" * 100)
        assert cache.has("key")
        assert cache.delete("key")
        assert not cache.has("key")
        assert cache.get("key.1", chunk=False) is None
        assert not cache.delete("key")

    def test_inc_dec_spread_value(self):
        cache = self.cache_factory(chunksize=4)
        assert cache.inc("count", 10) == 10
        assert cache.inc("count", 5) == 15
        assert cache.dec("count", 3) == 12
        assert cache.get("count") == 12


class TestSASLMemcachedCacheClientLib:
    def test_credentials_select_pylibmc(self):
        pylibmc = pytest.importorskip("pylibmc")
        cache = SASLMemcachedCache(
            servers=["127.0.0.1:1"], username="cachelib", password="cachelib"
        )
        assert isinstance(cache._client, pylibmc.ClientPool)

    def test_credentials_with_other_client_lib_raise(self):
        with pytest.raises(ValueError, match="only supported by pylibmc"):
            SASLMemcachedCache(
                servers=["127.0.0.1:1"],
                username="cachelib",
                password="cachelib",
                memcache_client_lib="memcache",
            )

    def test_kwargs_are_passed_to_pylibmc(self):
        pytest.importorskip("pylibmc")
        cache = SASLMemcachedCache(
            servers=["127.0.0.1:1"],
            memcache_client_lib="pylibmc",
            behaviors={"tcp_nodelay": True},
        )
        with cache._client_context() as client:
            assert client.behaviors["tcp_nodelay"]


@pytest.mark.network
@pytest.mark.usefixtures("memcached_sasl_server")
class TestSASLMemcachedCacheAuthentication:
    servers = ["127.0.0.1:11213"]

    def test_valid_credentials(self):
        cache = SASLMemcachedCache(
            servers=self.servers, username="cachelib", password="cachelib"
        )
        assert cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_invalid_credentials(self):
        import pylibmc

        cache = SASLMemcachedCache(
            servers=self.servers, username="cachelib", password="wrong"
        )
        with pytest.raises(pylibmc.Error, match="AUTHENTICATION"):
            cache.set("key", "value")

    def test_spread_with_valid_credentials(self):
        cache = SpreadSASLMemcachedCache(
            servers=self.servers,
            username="cachelib",
            password="cachelib",
            chunksize=16,
        )
        value = "x" * 100
        assert cache.set("key", value)
        assert cache.get("key") == value
