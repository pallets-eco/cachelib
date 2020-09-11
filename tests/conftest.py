import importlib.util
import os
import signal
import sys
from time import sleep

import pytest
from xprocess import ProcessStarter


def _cleanup(proc_name):
    """make sure process started by xprocess does not hang"""
    with open(f".xprocess/{proc_name}/xprocess.PID") as f:
        pid = int(f.readline().strip())
        os.kill(pid, signal.SIGKILL)


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
    _package_name = "redis"
    if not _safe_import(_package_name):
        pytest.skip("could not find python package 'redis'")

    class Starter(ProcessStarter):
        pattern = "[Rr]eady to accept connections"
        args = ["redis-server"]

    xprocess.ensure(_package_name, Starter)
    yield
    _cleanup(_package_name)


class CommonTests:
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

    def test_set_get(self):
        cache = self._cache_factory()
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert cache.get(k) == v

    def test_set_get_many(self):
        cache = self._cache_factory()
        assert cache.set_many(self.sample_pairs)
        values = cache.get_many(*self.sample_pairs)
        assert values == list(self.sample_pairs.values())

    def test_get_dict(self):
        cache = self._cache_factory()
        cache.set_many(self.sample_pairs)
        d = cache.get_dict(*self.sample_pairs)
        assert d == self.sample_pairs

    def test_delete(self):
        cache = self._cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
            assert cache.delete(k)
            assert not cache.get(k)

    def test_delete_many(self):
        cache = self._cache_factory()
        cache.set_many(self.sample_pairs)
        assert cache.delete_many(*self.sample_pairs)
        assert not any(cache.get_many(*self.sample_pairs))

    def test_add(self):
        cache = self._cache_factory()
        cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert not cache.add(k, "updated")
        assert cache.get_many(*self.sample_pairs) == list(self.sample_pairs.values())
        for k, v in self.sample_pairs.items():
            assert cache.add(f"{k}-new", v)
            assert cache.get(f"{k}-new") == v

    def test_inc_dec(self):
        cache = self._cache_factory()
        for n in self.sample_numbers:
            assert not cache.get(f"{n}-key-inc")
            assert cache.inc(f"{n}-key-inc", n) == n
            assert cache.get(f"{n}-key-inc") == n
            assert cache.dec(f"{n}-key-dec", n) == -n
            assert cache.get(f"{n}-key-dec") == -n
            assert cache.dec(f"{n}-key-inc", 5) == n - 5

    def test_expiration(self):
        cache = self._cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(f"{k}-t0", v, timeout=0)
            cache.set(f"{k}-t1", v, timeout=1)
            cache.set(f"{k}-t5", v, timeout=5)
        sleep(2)
        for k, v in self.sample_pairs.items():
            assert cache.get(f"{k}-t0") == v
            assert cache.get(f"{k}-t5") == v
            assert not cache.get(f"{k}-t1")
