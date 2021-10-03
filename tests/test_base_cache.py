import pytest

from cachelib import BaseCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        return BaseCache(*args, **kwargs)

    request.cls.cache_factory = _factory


class TestBaseCache:
    def test_get(self):
        cache = self.cache_factory()
        assert cache.get("bacon") is None

    def test_delete(self):
        cache = self.cache_factory()
        assert cache.delete("eggs")

    def test_get_many(self):
        cache = self.cache_factory()
        keys = ["bacon", "spam", "eggs"]
        expected = [None] * 3
        assert cache.get_many(*keys) == expected

    def test_get_dict(self):
        cache = self.cache_factory()
        keys = ["bacon", "spam", "eggs"]
        expected = dict.fromkeys(keys, None)
        assert cache.get_dict(*keys) == expected

    def test_set(self):
        cache = self.cache_factory()
        assert cache.set("sausage", "tomato")

    def test_add(self):
        cache = self.cache_factory()
        assert cache.add("baked", "beans")

    def test_set_many(self):
        cache = self.cache_factory()
        keys = ["bacon", "spam", "eggs"]
        mapping = dict.fromkeys(keys, None)
        assert cache.set_many(mapping) == keys

    def test_delete_many(self):
        cache = self.cache_factory()
        keys = ["bacon", "spam", "eggs"]
        assert cache.delete_many(*keys) == keys

    def test_has(self):
        cache = self.cache_factory()
        with pytest.raises(NotImplementedError):
            cache.has("lobster")

    def test_clear(self):
        cache = self.cache_factory()
        assert cache.clear()

    def test_inc(self):
        cache = self.cache_factory()
        assert cache.inc("crevettes", delta=10) == 10

    def test_dec(self):
        cache = self.cache_factory()
        assert cache.dec("truffle", delta=10) == -10
