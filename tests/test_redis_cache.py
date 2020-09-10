from conftest import CommonTests

from cachelib import RedisCache


class TestRedisCache(CommonTests):
    def cache_factory(self, *args, **kwargs):
        rc = RedisCache(*args, **kwargs)
        rc._client.flushdb()
        return rc

    def test_has(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert cache.has(k)
        assert not cache.has("unknown")

    def test_clear(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache.clear()
        assert not any(cache.get_many(*self.sample_pairs))
