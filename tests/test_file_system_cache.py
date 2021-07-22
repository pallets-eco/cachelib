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

    def test_EOFError(self, caplog):
        cache = self.cache_factory(threshold=1)
        assert cache.set_many(self.sample_pairs)
        file_names = [cache._get_filename(k) for k in self.sample_pairs.keys()]
        # truncate files to erase content
        for fpath in file_names:
            open(fpath, "w").close()
        assert cache.set("test", "EOFError")
        assert "Exception raised" in caplog.text

    def test_threshold(self):
        threshold = len(self.sample_pairs) // 2
        cache = self.cache_factory(threshold=threshold)
        assert cache.set_many(self.sample_pairs)
        assert cache._file_count == 4
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

    def test_file_counting_on_override(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache._file_count == len(self.sample_pairs)
        assert cache.set_many(self.sample_pairs)
        # count should remain the same
        assert cache._file_count == len(self.sample_pairs)

    def test_prune_old_entries(self):
        threshold = 2 * len(self.sample_pairs) - 1
        cache = self.cache_factory(threshold=threshold)
        for k, v in self.sample_pairs.items():
            assert cache.set(f"{k}-t1", v, timeout=1)
            assert cache.set(f"{k}-t10", v, timeout=10)
        sleep(3)
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert cache.has(f"{k}-t10")
            assert not cache.has(f"{k}-t1")
