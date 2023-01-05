import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

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
        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory


@pytest.mark.usefixtures("dynamodb_local_server")
class TestDynamoDbCache(CommonTests, ClearTests, HasTests):
    pass

    def test_expiration(self):
        # skip
        issue_reference = (
            "https://github.com/aws/aws-sdk-js/issues/1527#issuecomment-305026722"
        )
        pytest.skip(f"ttl is not supported on dynamodb local {issue_reference}")
