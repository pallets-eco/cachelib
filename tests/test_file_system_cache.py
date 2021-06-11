from time import sleep

import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import FileSystemCache


@pytest.fixture(autouse=True)
def cache_factory(request, tmpdir):
    def _factory(self, *args, **kwargs):
        return FileSystemCache(tmpdir, *args, **kwargs)

    request.cls.cache_factory = _factory


class TestFileSystemCache(CommonTests, ClearTests, HasTests):
    # override parent sample since these must implement buffer interface
    sample_pairs = {
        "bacon": "eggs",
        "sausage": "spam",
        "brandy": "lobster",
        "truffle": "wine",
        "sauce": "truffle pate",
        "cravettes": "mournay sauce",
    }

    def test_threshold(self):
        threshold = len(self.sample_pairs) // 2
        cache = self.cache_factory(threshold=threshold)
        assert cache.set_many(self.sample_pairs)
        assert abs(cache._file_count - threshold) <= 1
        # due to autouse=True a single tmpdir is used
        # for each test so we need to clear it
        assert cache.clear()
        cache = self.cache_factory(threshold=0)
        assert cache.set_many(self.sample_pairs)
        assert not cache._file_count

    def test_file_counting(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache._file_count == len(self.sample_pairs)
        assert cache.clear()
        assert cache._file_count == 0

    def test_prune_old_entries(self):
        threshold = 2 * len(self.sample_pairs) - 1
        cache = self.cache_factory(threshold=threshold)
        for k, v in self.sample_pairs.items():
            assert cache.set(f"{k}-t0.1", v, timeout=0.1)
            assert cache.set(f"{k}-t5.0", v, timeout=5.0)
        sleep(2)
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert cache.has(f"{k}-t5.0")
            assert not cache.has(f"{k}-t0.1")
