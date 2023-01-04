import pytest
from moto import mock_dynamodb

from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import DynamoDbCache


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        if bvalue is None:
            return None
        return eval(bvalue.decode())


class CustomCache(DynamoDbCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True, params=[DynamoDbCache, CustomCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = request.param(*args, **kwargs)
        rc.clear()
        return rc
    if request.cls:
        request.cls.cache_factory = _factory


@mock_dynamodb
def test_dynamodb_behaviour():
    import boto3
    import time
    from datetime import datetime
    dynamo = boto3.client("dynamodb")
    table_name = 'test-table'
    table = dynamo.create_table(
                AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "id", "KeyType": "HASH"},
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            )
    # table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

    # table.wait_until_exists()
    dynamo.update_time_to_live(
        TableName=table_name,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
    )
    cache_key = "foobar"
    item = {
        'id': {"S": cache_key},
        'ttl': {"N": str(int(time.time() + 600))},
        'created_at': {"S": datetime.utcnow().isoformat()},
        'value': {"S": "asdf"}

    }
    res = dynamo.put_item(TableName=table_name,Item=item)
    value = dynamo.get_item(TableName=table_name, Key={"id": {"S": cache_key}})
    table = boto3.resource("dynamodb").Table(table_name)
    item = {
        'id': cache_key,
        'ttl': int(time.time() + 600),
        'created_at': datetime.utcnow().isoformat(),
        'value': "asdf2"
    }
    res2 = table.put_item(Item=item)
    res3 = table.delete()
    pass


class TestDynamoDbCache(CommonTests):#, ClearTests, HasTests):
    pass


