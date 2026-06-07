from conftest import TestData

from cachelib.serializers import JSONSerializer


class SerializerTests(TestData):
    """A set of tests to run on serializers used by caches"""

    def test_serializer_injection_roundtrip(self):
        cache = self.cache_factory(serializer=JSONSerializer())
        assert cache.set("key", {"a": 1, "b": [1, 2, 3]})
        assert cache.get("key") == {"a": 1, "b": [1, 2, 3]}

    def test_serializer_injection_set_many(self):
        cache = self.cache_factory(serializer=JSONSerializer())
        pairs = {"k1": "hello", "k2": 42, "k3": [True, None]}
        assert cache.set_many(pairs)
        assert cache.get_many(*pairs) == list(pairs.values())

    def test_serializer_is_stored_on_instance(self):
        serializer = JSONSerializer()
        cache = self.cache_factory(serializer=serializer)
        assert isinstance(cache.serializer, JSONSerializer)

    def test_serializer_injection_add(self):
        cache = self.cache_factory(serializer=JSONSerializer())
        assert cache.add("key", {"a": 1})
        assert cache.get("key") == {"a": 1}
        assert not cache.add("key", {"b": 2})

    def test_serializer_injection_get_dict(self):
        cache = self.cache_factory(serializer=JSONSerializer())
        pairs = {"k1": "hello", "k2": 42}
        cache.set_many(pairs)
        assert cache.get_dict(*pairs) == pairs

    def test_no_serializer_uses_default(self):
        cache = self.cache_factory()
        assert cache.set("key", b"raw bytes")
        assert cache.get("key") == b"raw bytes"
