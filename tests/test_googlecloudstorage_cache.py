from time import sleep

import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib import GoogleCloudStorageCache
from cachelib.serializers import JSONSerializer


class SillySerializer(JSONSerializer):
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        if bvalue is None:
            return None
        return eval(bvalue.decode())


class CustomCache(GoogleCloudStorageCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()


@pytest.fixture(autouse=True, params=[GoogleCloudStorageCache, CustomCache])
def cache_factory(request, key_prefix):
    def _factory(self, *args, **kwargs):
        kwargs.setdefault("bucket", "cachelib-test")
        kwargs.setdefault("key_prefix", key_prefix)
        kwargs.setdefault("anonymous", True)
        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory


@pytest.mark.network
@pytest.mark.usefixtures("gcs_server")
class TestGoogleCloudStorageCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    def expected_value(self, cache, value):
        return cache.serializer.loads(cache.serializer.dumps(value))

    def test_content_types(self):
        cache = self.cache_factory()
        assert cache.set("raw", b"\x00raw bytes")
        assert cache.set("serialized", {"a": 1})
        raw = cache.bucket.get_blob(cache.key_prefix + "raw")
        serialized = cache.bucket.get_blob(cache.key_prefix + "serialized")
        assert raw.content_type == "application/octet-stream"
        assert serialized.content_type == "application/json"
        assert cache.get("raw") == b"\x00raw bytes"
        assert cache.get("serialized") == {"a": 1}

    def test_set_unserializable_value(self):
        cache = self.cache_factory()
        cache.serializer = JSONSerializer()
        assert not cache.set("key", object())
        assert cache.get("key") is None

    def test_delete_missing_key(self):
        cache = self.cache_factory()
        assert not cache.delete("missing")

    def test_expired_objects_are_kept_by_default(self):
        cache = self.cache_factory()
        assert cache.set("key", "value", timeout=1)
        sleep(2)
        assert cache.get("key") is None
        assert not cache.has("key")
        assert cache.bucket.get_blob(cache.key_prefix + "key") is not None

    def test_delete_expired_objects_on_read(self):
        cache = self.cache_factory(delete_expired_objects_on_read=True)
        assert cache.set("key", "value", timeout=1)
        sleep(2)
        assert cache.get("key") is None
        assert cache.bucket.get_blob(cache.key_prefix + "key") is None

    def test_add_replaces_expired_object(self):
        cache = self.cache_factory()
        assert cache.set("key", "old", timeout=1)
        sleep(2)
        assert cache.add("key", "new")
        assert cache.get("key") == "new"


@pytest.mark.network
@pytest.mark.usefixtures("gcs_server")
class TestGoogleCloudStorageCacheCheckConnectionLive:
    def test_existing_bucket_constructs_and_works(self):
        cache = GoogleCloudStorageCache(
            "cachelib-test", anonymous=True, check_connection=True
        )
        assert cache.set("check-connection-key", "value")
        assert cache.get("check-connection-key") == "value"

    def test_missing_bucket_raises_when_enabled(self):
        with pytest.raises(RuntimeError, match="not found"):
            GoogleCloudStorageCache(
                "cachelib-missing-bucket", anonymous=True, check_connection=True
            )


class TestGoogleCloudStorageCacheCheckConnection:
    def test_unreachable_server_is_lazy_by_default(self, monkeypatch):
        # nothing listens on port 1, but no request is made at construction
        monkeypatch.setenv("STORAGE_EMULATOR_HOST", "http://127.0.0.1:1")
        cache = GoogleCloudStorageCache("cachelib-test", anonymous=True)
        assert isinstance(cache, GoogleCloudStorageCache)
