import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests
from serializer import SerializerTests

from cachelib import DynamoDbCache


@pytest.fixture(autouse=True, params=[DynamoDbCache])
def cache_factory(request, key_prefix):
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
        kwargs.setdefault("key_prefix", key_prefix)
        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc

    if request.cls:
        request.cls.cache_factory = _factory


@pytest.mark.network
class TestDynamoDbCache(
    CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests, SerializerTests
):
    pass


def _fast_fail_config():
    import os

    from botocore.config import Config

    os.environ.setdefault("AWS_ACCESS_KEY_ID", "RANDOM")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "RANDOM")
    return Config(connect_timeout=0.5, read_timeout=0.5, retries={"max_attempts": 0})


class TestDynamoDbCacheCheckConnection:
    # nothing listens on port 1, so load() fails with a BotoCoreError
    def test_unreachable_server_raises_when_enabled(self):
        with pytest.raises(RuntimeError, match="could not connect to DynamoDB"):
            DynamoDbCache(
                endpoint_url="http://127.0.0.1:1",
                region_name="us-west-2",
                check_connection=True,
                config=_fast_fail_config(),
            )

    def test_unreachable_server_is_lazy_by_default(self):
        cache = DynamoDbCache(
            endpoint_url="http://127.0.0.1:1",
            region_name="us-west-2",
            config=_fast_fail_config(),
        )
        assert isinstance(cache, DynamoDbCache)


@pytest.mark.network
class TestDynamoDbCacheCheckConnectionLive:
    @pytest.mark.parametrize("check_connection", [True, False])
    def test_missing_table_is_created_regardless_of_flag(self, check_connection):
        import uuid

        table_name = f"check-connection-{uuid.uuid4().hex}"
        cache = DynamoDbCache(
            table_name=table_name,
            endpoint_url="http://localhost:8000",
            region_name="us-west-2",
            check_connection=check_connection,
            config=_fast_fail_config(),
        )
        try:
            assert cache.set("check-connection-key", "value")
            assert cache.get("check-connection-key") == "value"
        finally:
            cache._table.delete()
