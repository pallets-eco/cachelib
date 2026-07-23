from conftest import TestData


class DeleteManyWithPrefixTests(TestData):
    """Tests for the 'delete_many' method when a key prefix is used"""

    def test_delete_many_with_prefix(self):
        cache = self.cache_factory(key_prefix="test_prefix:")
        cache.set_many({"foo": 1, "bar": 2, "baz": 3})
        result = cache.delete_many("foo", "bar", "baz")
        assert result == ["foo", "bar", "baz"]
        assert not any(cache.get_many("foo", "bar", "baz"))
