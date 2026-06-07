import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib import DynamoDbCache


@pytest.fixture(autouse=True, params=[DynamoDbCache])
def cache_factory(request):
    import warnings

    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )

    def _factory(self, *args, **kwargs):
        import os

        os.environ.setdefault("AWS_ACCESS_KEY_ID", "RANDOM")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "RANDOM")
        kwargs["endpoint_url"] = "http://localhost:8000"
        kwargs["region_name"] = "us-west-2"
        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory


class TestDynamoDbCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    pass
