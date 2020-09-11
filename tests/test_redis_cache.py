import pytest
from conftest import CommonTests

from cachelib import RedisCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = RedisCache(*args, **kwargs)
        rc._client.flushdb()
        return rc

    request.cls._cache_factory = _factory


@pytest.mark.usefixtures("redis_server")
class TestRedisCache(CommonTests):
    def test_has(self):
        cache = self._cache_factory()
        assert cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert cache.has(k)
        assert not cache.has("unknown")

    def test_clear(self):
        cache = self._cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache.clear()
        assert not any(cache.get_many(*self.sample_pairs))
