import pymongo
import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests
from serializer import SerializerTests

from cachelib.mongodb import MongoDbCache


@pytest.fixture(autouse=True, params=[MongoDbCache])
def cache_factory(request, key_prefix):
    client = pymongo.MongoClient()

    def _factory(self, *args, **kwargs):
        kwargs["client"] = client
        kwargs["db"] = "test-db"
        kwargs["collection"] = "test-collection"
        kwargs.setdefault("key_prefix", key_prefix)

        rc = request.param(*args, **kwargs)
        index_info = rc.client.index_information()
        all_keys = {
            subkey[0] for value in index_info.values() for subkey in value["key"]
        }
        assert "id" in all_keys, "Failed to create index on 'id' field"
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory

    yield

    client.close()


@pytest.mark.network
class TestMongoDbCache(CommonTests, ClearTests, HasTests, SerializerTests):
    pass


class TestMongoDbCacheCheckConnection:
    # nothing listens on port 1; short timeouts keep the ping failure fast
    def test_unreachable_server_raises_when_enabled(self):
        client = pymongo.MongoClient(
            "mongodb://127.0.0.1:1/",
            serverSelectionTimeoutMS=100,
            connectTimeoutMS=100,
        )
        try:
            with pytest.raises(RuntimeError, match="could not connect to MongoDB"):
                MongoDbCache(client=client, check_connection=True)
        finally:
            client.close()


@pytest.mark.network
class TestMongoDbCacheCheckConnectionLive:
    def test_reachable_server_constructs_and_works(self):
        client = pymongo.MongoClient()
        try:
            cache = MongoDbCache(
                client=client,
                db="test-db",
                collection="test-collection",
                check_connection=True,
            )
            assert cache.set("check-connection-key", "value")
            assert cache.get("check-connection-key") == "value"
        finally:
            client.close()
