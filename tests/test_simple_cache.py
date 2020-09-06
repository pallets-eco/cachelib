from conftest import CommonTests

from cachelib import SimpleCache


class TestSimpleCache(CommonTests):
    def cache_factory(self, *args, **kwargs):
        return SimpleCache(*args, **kwargs)

    def test_has(self, cache):
        cache = self.cache_factory()
        for k, v in super().sample_pairs.items():
            cache.set(k, v)
            assert cache.has(k)
            assert not cache.has(f"{k}-unknown")
