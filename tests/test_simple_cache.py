from time import sleep

from conftest import CommonTests

from cachelib import SimpleCache


class TestSimpleCache(CommonTests):
    def cache_factory(self, *args, **kwargs):
        return SimpleCache(*args, **kwargs)

    def test_has(self):
        cache = self.cache_factory()
        for k, v in super().sample_pairs.items():
            assert cache.set(k, v)
            assert cache.has(k)
            assert not cache.has(f"{k}-unknown")

    def test_threshold(self):
        threshold = len(super().sample_pairs) // 2
        cache = self.cache_factory(threshold=threshold)
        assert cache.set_many(super().sample_pairs)
        assert abs(len(cache._cache) - threshold) <= 1

    def test_prune_old_entries(self):
        threshold = 2 * len(super().sample_pairs) - 1
        cache = self.cache_factory(threshold=threshold)
        for k, v in super().sample_pairs.items():
            assert cache.set(f"{k}-t0.2", v, timeout=0.2)
            assert cache.set(f"{k}-t1.0", v, timeout=1.0)
        sleep(0.3)
        for k, v in super().sample_pairs.items():
            assert cache.set(k, v)
            assert f"{k}-t1.0" in cache._cache.keys()
            assert f"{k}-t0.2" not in cache._cache.keys()
