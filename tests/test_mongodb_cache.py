import pytest

from cachelib.mongodb import MongoDbCache
from clear import ClearTests
from common import CommonTests
from has import HasTests

@pytest.fixture(autouse=True, params=[MongoDbCache])
def cache_factory(request):
    import warnings

    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )

    def _factory(self, *args, **kwargs):
        url = "mongodb+srv://datalake_test_user:xas7rPIDozTvEdDg@development.ewxgy.mongodb.net/datalake_test?retryWrites=true&w=majority&serverSelectionTimeoutMs=5000"

        kwargs["host"] = url
        kwargs["collection"] = "flask-session-test"
        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory


class TestMongoDbCache(CommonTests, ClearTests, HasTests):
    pass
