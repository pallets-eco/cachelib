import hashlib
import os
from time import sleep
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import FileSystemCache


class SillySerializer:
    """A pointless serializer only for testing"""

    def dump(self, value, fs):
        fs.write(f"{repr(value)}{os.linesep}".encode())

    def load(self, fs):
        try:
            loaded = eval(fs.readline().decode())
        # When all file content has been read eval will
        # turn the EOFError into SyntaxError wich is not
        # handled by cachelib
        except SyntaxError as e:
            raise EOFError from e
        return loaded


class CustomSerializerCache(FileSystemCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CustomHashingMethodCache(FileSystemCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, hash_method=hashlib.sha256, **kwargs)


class CustomDefaultHashingMethodCache(FileSystemCache):
    _default_hash_method = hashlib.sha256

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(
    autouse=True,
    params=[
        FileSystemCache,
        CustomSerializerCache,
        CustomHashingMethodCache,
        CustomDefaultHashingMethodCache,
    ],
)
def cache_factory(request, tmpdir):
    def _factory(self, *args, **kwargs):
        client = request.param(tmpdir, *args, **kwargs)
        return client

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

    def test_run_safely_succeeds_on_first_try(self):
        """_run_safely returns the function's result when no error is raised."""
        cache = self.cache_factory()
        result = cache._run_safely(lambda: 42)
        assert result == 42

    def test_run_safely_retries_on_permission_error(self):
        """
        _run_safely retries when PermissionError is raised
        (e.g. Windows NTFS race).
        """
        cache = self.cache_factory()
        flaky = Mock(
            side_effect=[PermissionError("locked"), PermissionError("locked"), "ok"]
        )

        with patch("cachelib.file.sleep") as mock_sleep:
            result = cache._run_safely(flaky)

        assert result == "ok"
        assert flaky.call_count == 3
        assert mock_sleep.call_count == 2

    def test_run_safely_exhausts_retries_and_returns_none(self):
        """
        _run_safely returns None when PermissionError persists
        beyond max_sleep_time.
        """
        cache = self.cache_factory()

        def always_fails():
            raise PermissionError("locked")

        with patch("cachelib.file.sleep"):
            result = cache._run_safely(always_fails)

        assert result is None

    def test_run_safely_does_not_retry_other_errors(self):
        """_run_safely does not catch non-PermissionError exceptions."""
        cache = self.cache_factory()

        def raises_file_not_found():
            raise FileNotFoundError("missing")

        with pytest.raises(FileNotFoundError):
            cache._run_safely(raises_file_not_found)

    def test_run_safely_exponential_backoff(self):
        """_run_safely doubles the wait_step on each retry."""
        cache = self.cache_factory()
        flaky = Mock(
            side_effect=[
                PermissionError("locked"),
                PermissionError("locked"),
                PermissionError("locked"),
                "ok",
            ]
        )

        with patch("cachelib.file.sleep") as mock_sleep:
            cache._run_safely(flaky)

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        # Each wait should double the previous
        assert sleep_calls[1] == sleep_calls[0] * 2
        assert sleep_calls[2] == sleep_calls[1] * 2
