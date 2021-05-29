from time import sleep

import pytest
from conftest import CommonTests
from conftest import HasTests

from cachelib import SimpleCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        return SimpleCache(*args, **kwargs)

    request.cls.cache_factory = _factory


class TestSimpleCache(CommonTests, HasTests):
    def test_threshold(self):
        threshold = len(self.sample_pairs) // 2
        cache = self.cache_factory(threshold=threshold)
        assert cache.set_many(self.sample_pairs)
        assert abs(len(cache._cache) - threshold) <= 1

    def test_prune_old_entries(self):
        threshold = 2 * len(self.sample_pairs) - 1
        cache = self.cache_factory(threshold=threshold)
        for k, v in self.sample_pairs.items():
            assert cache.set(f"{k}-t0.2", v, timeout=0.2)
            assert cache.set(f"{k}-t1.0", v, timeout=1.0)
        sleep(0.3)
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert f"{k}-t1.0" in cache._cache.keys()
            assert f"{k}-t0.2" not in cache._cache.keys()
