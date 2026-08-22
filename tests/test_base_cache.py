from datetime import timedelta

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

    def test_delete_many_raise_errors(self):
        class FailingDeleteCache(BaseCache):
            """Simulates a backend where deletes fail and keys remain"""

            def delete(self, key):
                return False

            def has(self, key):
                return True

        cache = FailingDeleteCache(ignore_delete_many_errors=False)
        with pytest.raises(RuntimeError, match="Failed to delete keys"):
            cache.delete_many("bacon", "spam")

        cache = FailingDeleteCache(ignore_delete_many_errors=True)
        assert cache.delete_many("bacon", "spam") == []

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

    @pytest.mark.parametrize(
        "default_timeout,input_timeout,expected",
        [
            (42, None, 42),  # None falls back to default
            (300, 0, 0),  # explicit zero stays zero (permanent)
            (300, 60, 60),  # explicit value is returned as-is
            (0, None, 0),  # default_timeout=0 means permanently cached by default
            (300, timedelta(seconds=60), 60),  # timedelta is converted to seconds
            (300, timedelta(minutes=2), 120),
            (300, timedelta(days=1), 86400),
            (300, timedelta(), 0),  # a zero timedelta is permanent, like 0
            (300, timedelta(milliseconds=500), 1),  # sub-second timeouts round up
            (300, timedelta(seconds=1, milliseconds=200), 2),
            (timedelta(minutes=1), None, 60),  # timedelta default
            (timedelta(minutes=1), 30, 30),  # explicit value beats timedelta default
        ],
    )
    def test_normalize_timeout(self, default_timeout, input_timeout, expected):
        cache = BaseCache(default_timeout=default_timeout)
        assert cache._normalize_timeout(input_timeout) == expected

    def test_default_timeout_timedelta_is_stored_as_seconds(self):
        cache = BaseCache(default_timeout=timedelta(minutes=5))
        assert cache.default_timeout == 300

    @pytest.mark.parametrize(
        "input_timeout,expected",
        [
            (0.1, 1),  # subsecond floats round up, not down to "never expires"
            (5.0, 5),
            (5.5, 6),
        ],
    )
    def test_float_timeout_is_deprecated_and_rounded_up(self, input_timeout, expected):
        cache = self.cache_factory()
        with pytest.warns(DeprecationWarning, match="Float timeouts are deprecated"):
            assert cache._normalize_timeout(input_timeout) == expected

    def test_float_default_timeout_is_deprecated(self):
        with pytest.warns(DeprecationWarning, match="Float timeouts are deprecated"):
            cache = BaseCache(default_timeout=1.5)
        assert cache.default_timeout == 2

    def test_invalid_timeout_type_raises(self):
        cache = self.cache_factory()
        with pytest.raises(TypeError, match="timeout must be an int"):
            cache._normalize_timeout("60")
