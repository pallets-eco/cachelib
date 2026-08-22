import datetime as dt
import typing as _t

from cachelib.base import BaseCache
from cachelib.serializers import DynamoDbSerializer

CREATED_AT_FIELD = "created_at"
RESPONSE_FIELD = "response"

if _t.TYPE_CHECKING:
    from mypy_boto3_dynamodb.type_defs import GetItemInputTableGetItemTypeDef
    from mypy_boto3_dynamodb.type_defs import PutItemInputTablePutItemTypeDef


class DynamoDbCache(BaseCache):
    """
    Implementation of :class:`~.BaseCache` that uses an AWS DynamoDb table
    as the backend.

    Your server process will require ``dynamodb:GetItem`` and
    ``dynamodb:PutItem`` IAM permissions on the cache table.

    Limitations: DynamoDB table items are limited to 400 KB in size.  Since
    this class stores cached items in a table, the max size of a cache entry
    will be slightly less than 400 KB, since the cache key and expiration
    time fields are also part of the item.

    :param table_name: The name of the DynamoDB table to use
    :param default_timeout: Set the timeout after which cache entries expire,
        either a number of seconds or a :class:`datetime.timedelta`

        .. versionchanged:: 0.17.0
            Accepts a :class:`datetime.timedelta`.
    :param key_field: The name of the hash_key attribute in the DynamoDb
        table. This must be a string attribute.
    :param expiration_time_field: The name of the table attribute to store the
        expiration time in.  This will be an int
        attribute. The timestamp will be stored as
        seconds past the epoch.  If you configure
        this as the TTL field, then DynamoDB will
        automatically delete expired entries.
    :param key_prefix: A prefix that should be added to all keys.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.

        .. versionadded:: 0.16.0
    :param check_connection: If True, the constructor will verify the
        connection to DynamoDB and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use. A missing table is created either way.

        .. versionadded:: 0.16.1
    """

    serializer = DynamoDbSerializer()

    def __init__(
        self,
        table_name: str = "python-cache",
        default_timeout: int | dt.timedelta = 300,
        key_field: str = "cache_key",
        expiration_time_field: str = "expiration_time",
        key_prefix: str | None = None,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ):
        super().__init__(
            default_timeout, ignore_delete_many_errors=ignore_delete_many_errors
        )

        try:
            import boto3
            from boto3.dynamodb.conditions import Attr
            from botocore.exceptions import BotoCoreError
            from botocore.exceptions import ClientError
        except ImportError as err:
            raise RuntimeError("no boto3 module found") from err

        self._table_name = table_name
        self._key_field = key_field
        self._expiration_time_field = expiration_time_field
        self.key_prefix = key_prefix or ""
        self._dynamo = boto3.resource("dynamodb", **kwargs)
        self._attr = Attr
        self._client_error = ClientError
        self._boto_core_error = BotoCoreError
        self.check_connection = check_connection

        try:
            self._table = self._dynamo.Table(table_name)
            self._table.load()
        except BotoCoreError as err:
            if self.check_connection:
                raise RuntimeError(f"could not connect to DynamoDB: {err}") from err
        except ClientError as err:
            # only create the table if it's missing; anything else
            # (bad credentials, denied access) is a real error
            if err.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
                if self.check_connection:
                    raise RuntimeError(f"could not connect to DynamoDB: {err}") from err
                return  # fail silently if check_connection is False
            table = self._dynamo.create_table(
                AttributeDefinitions=[
                    {"AttributeName": key_field, "AttributeType": "S"}
                ],
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": key_field, "KeyType": "HASH"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            dynamo = boto3.client("dynamodb", **kwargs)
            dynamo.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    "Enabled": True,
                    "AttributeName": expiration_time_field,
                },
            )
            self._table = self._dynamo.Table(table_name)
            self._table.load()

    def _utcnow(self) -> dt.datetime:
        """Return a tz-aware UTC datetime representing the current time"""
        return dt.datetime.now(dt.UTC)

    def _get_item(self, key: str, attributes: list[_t.Any] | None = None) -> _t.Any:
        """
        Get an item from the cache table, optionally limiting the returned
        attributes.

        :param key: The cache key of the item to fetch

        :param attributes: An optional list of attributes to fetch.  If not
            given, all attributes are fetched. The
            ``expiration_time`` field will always be added to the
            list of fetched attributes.
        :return: The table item for key if it exists and is not expired, else
            ``None``.
        """
        kwargs: GetItemInputTableGetItemTypeDef = {"Key": {self._key_field: key}}
        if attributes:
            if self._expiration_time_field not in attributes:
                attributes = list(attributes) + [self._expiration_time_field]
            kwargs["ProjectionExpression"] = ",".join(attributes)

        response = self._table.get_item(**kwargs)
        cache_item = response.get("Item")

        if cache_item:
            now = int(self._utcnow().timestamp())
            if (
                _t.cast(int, cache_item.get(self._expiration_time_field, now + 100))
                > now
            ):
                return cache_item

        return None

    def get(self, key: str) -> _t.Any:
        """
        Get a cache item

        :param key: The cache key of the item to fetch
        :return: cache value if not expired, else None
        """
        cache_item = self._get_item(self.key_prefix + key)
        if cache_item:
            response = cache_item[RESPONSE_FIELD]
            value = self.serializer.loads(response.value)
            return value
        return None

    def delete(self, key: str) -> bool:
        """
        Deletes an item from the cache. This is a no-op if the item doesn't
        exist

        :param key: Key of the item to delete.
        :return: True if the key was deleted
        """
        try:
            self._table.delete_item(Key={self._key_field: self.key_prefix + key})
            return True
        except (self._client_error, self._boto_core_error):
            return False

    def _set(
        self,
        key: str,
        value: _t.Any,
        timeout: int | dt.timedelta | None = None,
        overwrite: bool | None = True,
    ) -> _t.Any:
        """
        Store a cache item, with the option to not overwrite existing items

        :param key: Cache key to use
        :param value: a serializable object
        :param timeout: The timeout for the cached item, to override
            the default. Either a number of seconds or a
            :class:`datetime.timedelta`.
        :param overwrite: If true, overwrite any existing cache item with key.
            If false, the new value will only be stored if no
            non-expired cache item exists with key.
        :return: True if the new item was stored.
        """
        normalized_timeout = self._normalize_timeout(timeout)
        now = self._utcnow()

        try:
            dump = self.serializer.dumps(value)
            item: dict[str, str | bytes | None | int] = {
                self._key_field: key,
                CREATED_AT_FIELD: now.isoformat(),
                RESPONSE_FIELD: dump,
            }
            if normalized_timeout > 0:
                expiration_time = now + dt.timedelta(seconds=normalized_timeout)
                item[self._expiration_time_field] = int(expiration_time.timestamp())

            kwargs: PutItemInputTablePutItemTypeDef = {"Item": item}
            if not overwrite:
                # Cause the put to fail if a non-expired item with this key
                # already exists

                cond = self._attr(self._key_field).not_exists() | self._attr(
                    self._expiration_time_field
                ).lte(int(now.timestamp()))
                kwargs["ConditionExpression"] = cond

            self._table.put_item(**kwargs)
            return True
        except Exception:
            return False

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> _t.Any:
        return self._set(self.key_prefix + key, value, timeout=timeout, overwrite=True)

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> _t.Any:
        return self._set(self.key_prefix + key, value, timeout=timeout, overwrite=False)

    def has(self, key: str) -> bool:
        return (
            self._get_item(self.key_prefix + key, [self._expiration_time_field])
            is not None
        )

    def clear(self) -> bool:
        paginator = self._dynamo.meta.client.get_paginator("scan")
        pages = paginator.paginate(
            TableName=self._table_name, ProjectionExpression=self._key_field
        )

        with self._table.batch_writer() as batch:
            for page in pages:
                for item in page["Items"]:
                    batch.delete_item(Key=item)

        return True
