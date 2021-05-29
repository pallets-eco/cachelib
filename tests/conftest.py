import importlib.util
import os
import sys
import warnings
from pathlib import Path
from time import sleep

import pytest
from xprocess import ProcessStarter


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    try:
        script_path = Path(os.environ["TMPDIR"], "return_pytest_exit_code.py")
    except KeyError:
        warnings.warn(
            "Pytest could not find tox 'TMPDIR' in the environment,"
            " make sure the variable is set in the project tox.ini"
            " file if you are running under tox."
        )
    else:
        with open(script_path, mode="w") as f:
            f.write(f"import sys; sys.exit({exitstatus})")
    yield


def _safe_import(name):
    if name in sys.modules:
        return True
    spec = importlib.util.find_spec(name)
    if spec is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return True
    return False


@pytest.fixture(scope="class")
def redis_server(xprocess):
    package_name = "redis"
    if not _safe_import(package_name):
        pytest.skip(f"could not find python package '{package_name}'")

    class Starter(ProcessStarter):
        pattern = "[Rr]eady to accept connections"
        args = ["redis-server"]

    xprocess.ensure(package_name, Starter)
    yield
    xprocess.getinfo(package_name).terminate()


@pytest.fixture(scope="class")
def memcached_server(xprocess):
    package_name = "pylibmc"
    if not _safe_import(package_name):
        pytest.skip(f"could not find python package '{package_name}'")

    class Starter(ProcessStarter):
        pattern = "server listening"
        args = ["memcached", "-vv"]

    xprocess.ensure(package_name, Starter)
    yield
    xprocess.getinfo(package_name).terminate()


class TestData:
    """This class centralizes all data samples used in tests"""

    sample_numbers = [0, 10, 1024000, 9, 5000000000000, 99, 738, 2000000]

    sample_pairs = {
        "128": False,
        "beef": True,
        "crevettes": {},
        "1024": "spam",
        "bacon": "eggs",
        "sausage": 2048,
        "3072": [],
        "brandy": [{}, "fried eggs"],
        "lobster": ["baked beans", [512]],
        "4096": {"sauce": [], 256: "truffle"},
    }


class ClearTests(TestData):
    """Tests for the optional 'clear' method specified by BaseCache"""

    def test_clear(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache.clear()
        assert not any(cache.get_many(*self.sample_pairs))


class HasTests(TestData):
    """Tests for the optional 'has' method specified by BaseCache"""

    def test_has(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert cache.has(k)
        assert not cache.has("unknown")


class CommonTests(TestData):
    """A base set of tests to be run for all cache types"""

    def test_set_get(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert cache.get(k) == v

    def test_set_get_many(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        values = cache.get_many(*self.sample_pairs)
        assert values == list(self.sample_pairs.values())

    def test_get_dict(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs)
        d = cache.get_dict(*self.sample_pairs)
        assert d == self.sample_pairs

    def test_delete(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
            assert cache.delete(k)
            assert not cache.get(k)

    def test_delete_many(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs)
        assert cache.delete_many(*self.sample_pairs)
        assert not any(cache.get_many(*self.sample_pairs))

    def test_add(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert not cache.add(k, "updated")
        assert cache.get_many(*self.sample_pairs) == list(self.sample_pairs.values())
        for k, v in self.sample_pairs.items():
            assert cache.add(f"{k}-new", v)
            assert cache.get(f"{k}-new") == v

    def test_inc_dec(self):
        cache = self.cache_factory()
        for n in self.sample_numbers:
            assert not cache.get(f"{n}-key-inc")
            assert cache.inc(f"{n}-key-inc", n) == n
            assert cache.get(f"{n}-key-inc") == n
            assert cache.dec(f"{n}-key-dec", n) == -n
            assert cache.get(f"{n}-key-dec") == -n
            assert cache.dec(f"{n}-key-inc", 5) == n - 5

    def test_expiration(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(f"{k}-t0", v, timeout=0)
            cache.set(f"{k}-t1", v, timeout=1)
            cache.set(f"{k}-t5", v, timeout=5)
        sleep(4)
        for k, v in self.sample_pairs.items():
            assert cache.get(f"{k}-t0") == v
            assert cache.get(f"{k}-t5") == v
            assert not cache.get(f"{k}-t1")
