from time import sleep

import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import SimpleCache


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        return eval(bvalue.decode())


class CustomCache(SimpleCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True, params=[SimpleCache, CustomCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        return request.param(*args, **kwargs)

    request.cls.cache_factory = _factory


class TestSimpleCache(CommonTests, HasTests, ClearTests):
    def test_threshold(self):
        threshold = len(self.sample_pairs) // 2
        cache = self.cache_factory(threshold=threshold)
        assert cache.set_many(self.sample_pairs)
        assert abs(len(cache._cache) - threshold) <= 1

    def test_prune_old_entries(self):
        threshold = 2 * len(self.sample_pairs) - 1
        cache = self.cache_factory(threshold=threshold)
        for k, v in self.sample_pairs.items():
            assert cache.set(f"{k}-t0.1", v, timeout=0.1)
            assert cache.set(f"{k}-t5.0", v, timeout=5.0)
        sleep(2)
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert f"{k}-t5.0" in cache._cache.keys()
            assert f"{k}-t0.1" not in cache._cache.keys()
