import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib.mongodb import MongoDbCache


@pytest.fixture(autouse=True, params=[MongoDbCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        kwargs["db"] = "test-db"
        kwargs["collection"] = "test-collection"
        kwargs["key_prefix"] = "prefix"

        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory


class TestMongoDbCache(CommonTests, ClearTests, HasTests):
    pass
