import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import MemcachedCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        kwargs.setdefault("servers", ["127.0.0.1:11212"])
        mc = MemcachedCache(*args, **kwargs)
        mc._client.flush_all()
        return mc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("memcached_server")
class TestMemcachedCache(CommonTests, ClearTests, HasTests):
    def test_delete_many_with_prefix(self):
        cache = self.cache_factory(key_prefix="test_prefix:")
        cache.set_many({"foo": 1, "bar": 2, "baz": 3})
        result = cache.delete_many("foo", "bar", "baz")
        assert result == ["foo", "bar", "baz"]
        assert not any(cache.get_many("foo", "bar", "baz"))
