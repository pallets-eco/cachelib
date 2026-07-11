import pymongo
import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib.mongodb import MongoDbCache


@pytest.fixture(autouse=True, params=[MongoDbCache])
def cache_factory(request):
    client = pymongo.MongoClient()

    def _factory(self, *args, **kwargs):
        kwargs["client"] = client
        kwargs["db"] = "test-db"
        kwargs["collection"] = "test-collection"
        kwargs["key_prefix"] = "prefix"

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
class TestMongoDbCache(CommonTests, ClearTests, HasTests):
    pass
