import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib.redis import RedisSentinelCache


class StandaloneSentinel:
    """Sentinel stand-in backed by the standalone test redis server."""

    def _client(self):
        import redis

        return redis.Redis(port=6360)

    def master_for(self, master):
        return self._client()

    def slave_for(self, master):
        return self._client()


@pytest.fixture(autouse=True)
def cache_factory(request, key_prefix):
    def _factory(self, *args, **kwargs):
        kwargs.setdefault("key_prefix", key_prefix)
        rc = RedisSentinelCache(StandaloneSentinel(), *args, **kwargs)
        rc._write_client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.network
@pytest.mark.usefixtures("redis_server")
class TestRedisSentinelCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    def test_reads_go_through_read_client(self):
        cache = self.cache_factory()
        assert cache._read_client is not cache._write_client
        assert cache.set("bacon", "eggs")
        assert cache.get("bacon") == "eggs"


class FakeRedisClient:
    """Stands in for a redis.Redis client; only tracks pings."""

    def __init__(self, ping_error=None):
        self.pinged = False
        self._ping_error = ping_error

    def ping(self):
        if self._ping_error is not None:
            raise self._ping_error
        self.pinged = True


class FakeSentinel:
    """Stands in for redis.sentinel.Sentinel with distinct r/w clients."""

    def __init__(self, ping_error=None):
        self.write_client = FakeRedisClient(ping_error=ping_error)
        self.read_client = FakeRedisClient(ping_error=ping_error)

    def master_for(self, master):
        return self.write_client

    def slave_for(self, master):
        return self.read_client


class TestRedisSentinelCacheInit:
    def test_sentinels_is_required(self):
        with pytest.raises(ValueError, match="sentinels is required"):
            RedisSentinelCache(None)
        with pytest.raises(ValueError, match="sentinels is required"):
            RedisSentinelCache([])

    def test_accepts_instantiated_sentinel(self):
        sentinel = FakeSentinel()
        cache = RedisSentinelCache(sentinel)
        assert cache._write_client is sentinel.write_client
        assert cache._read_client is sentinel.read_client

    def test_check_connection_pings_both_clients(self):
        sentinel = FakeSentinel()
        RedisSentinelCache(sentinel, check_connection=True)
        assert sentinel.write_client.pinged
        assert sentinel.read_client.pinged

    def test_check_connection_failure_raises(self):
        sentinel = FakeSentinel(ping_error=ConnectionError("boom"))
        with pytest.raises(RuntimeError, match="could not connect to Redis"):
            RedisSentinelCache(sentinel, check_connection=True)

    def test_check_connection_is_lazy_by_default(self):
        sentinel = FakeSentinel(ping_error=ConnectionError("boom"))
        RedisSentinelCache(sentinel)
        assert not sentinel.write_client.pinged

    def test_decode_responses_rejected(self):
        with pytest.raises(ValueError, match="decode_responses"):
            RedisSentinelCache([("127.0.0.1", 26379)], decode_responses=True)
