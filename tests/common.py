from time import sleep

import pytest
from conftest import TestData
from conftest import under_uwsgi

from cachelib import MemcachedCache
from cachelib import SimpleCache


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
        if under_uwsgi():
            pytest.skip(
                "uwsgi uses a separate sweeper thread to clean"
                " expired chache entries, thus the testing"
                " of such feature must be handled differently"
                " from other cache types."
            )
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(f"{k}-t0", v, timeout=0)
            cache.set(f"{k}-t1", v, timeout=1)
        sleep(4)
        for k, v in self.sample_pairs.items():
            assert cache.get(f"{k}-t0") == v
            assert not cache.get(f"{k}-t1")

    def test_signed_set_get(self):
        cache = self.cache_factory(secret_key="not very secret")
        if isinstance(cache, (MemcachedCache, SimpleCache)):
            pytest.skip("Simple and MemcachedCache do not support signing.")

        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert cache.get(k) == v

    def test_signed_does_not_get_unsigned(self):
        unsigned_cache = self.cache_factory()
        if isinstance(unsigned_cache, (MemcachedCache, SimpleCache)):
            pytest.skip("Simple and MemcachedCache do not support signing.")

        signed_cache = self.cache_factory(secret_key="not very secret")

        for k, v in self.sample_pairs.items():
            assert unsigned_cache.set(k, v)
            assert signed_cache.get(k) is None

    def test_signed_does_not_get_wrong_key(self):
        if isinstance(self.cache_factory(), (MemcachedCache, SimpleCache)):
            pytest.skip("Simple and MemcachedCache do not support signing.")

        signed_cache1 = self.cache_factory(secret_key="not very secret")
        signed_cache2 = self.cache_factory(secret_key="another not secret value")

        for k, v in self.sample_pairs.items():
            assert signed_cache1.set(k, v)
            assert signed_cache2.get(k) is None
            assert signed_cache2.set(k, v)
            assert signed_cache1.get(k) is None
