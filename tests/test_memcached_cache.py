import pytest

from conftest import CommonTests
from cachelib import MemcachedCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        mc = MemcachedCache(*args, **kwargs)
        mc._client.flush_all()
        return mc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("memcached_server")
class TestMemcachedCache(CommonTests):
    def test_has(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert cache.has(k)
        assert not cache.has("unknown")

    def test_clear(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache.clear()
        assert not any(cache.get_many(*self.sample_pairs))
