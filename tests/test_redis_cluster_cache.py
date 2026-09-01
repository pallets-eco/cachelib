import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib.redis import RedisClusterCache


@pytest.fixture(autouse=True)
def cache_factory(request, key_prefix):
    def _factory(self, *args, **kwargs):
        import redis

        kwargs.setdefault("key_prefix", key_prefix)
        # standalone client via the pre-instantiated-client path: a real
        # multi-node cluster is not available locally nor in CI services
        rc = RedisClusterCache(redis.Redis(port=6360), *args, **kwargs)
        rc._write_client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.network
@pytest.mark.usefixtures("redis_server")
class TestRedisClusterCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    pass


class FakeRedisClient:
    """Stands in for a redis.Redis client; only tracks pings."""

    def __init__(self, ping_error=None):
        self.pinged = False
        self._ping_error = ping_error

    def ping(self):
        if self._ping_error is not None:
            raise self._ping_error
        self.pinged = True


class TestRedisClusterCacheInit:
    def test_cluster_or_redis_url_is_required(self):
        with pytest.raises(ValueError, match="cluster is required"):
            RedisClusterCache()

    def test_invalid_cluster_string_raises(self):
        with pytest.raises(ValueError, match="correct cluster argument"):
            RedisClusterCache("host-without-port")

    def test_accepts_instantiated_client(self):
        client = FakeRedisClient()
        cache = RedisClusterCache(client)
        assert cache._write_client is client
        assert cache._read_client is client

    def test_check_connection_pings_client(self):
        client = FakeRedisClient()
        RedisClusterCache(client, check_connection=True)
        assert client.pinged

    def test_check_connection_failure_raises(self):
        client = FakeRedisClient(ping_error=ConnectionError("boom"))
        with pytest.raises(RuntimeError, match="could not connect to Redis"):
            RedisClusterCache(client, check_connection=True)

    def test_decode_responses_rejected(self):
        with pytest.raises(ValueError, match="decode_responses"):
            RedisClusterCache("localhost:7000", decode_responses=True)
