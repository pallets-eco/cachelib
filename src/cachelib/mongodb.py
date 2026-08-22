import datetime as dt
import typing as _t

from cachelib.base import BaseCache
from cachelib.serializers import MongoDbSerializer


class MongoDbCache(BaseCache):
    """
    Implementation of :class:`~.BaseCache` that uses mongodb
    collection as the backend.

    Limitations: maximum ``MongoDB`` document size is 16 MB

    :param client: mongodb client or connection string
    :param db: mongodb database name
    :param collection: mongodb collection name
    :param default_timeout: Set the timeout after which cache entries expire,
        either a number of seconds or a :class:`datetime.timedelta`

        .. versionchanged:: 0.17.0
            Accepts a :class:`datetime.timedelta`.
    :param key_prefix: A prefix that should be added to all keys.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.

        .. versionadded:: 0.16.0
    :param check_connection: If True, the constructor will verify the
        connection to the mongodb server and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use.

        .. versionadded:: 0.16.1
    """

    serializer = MongoDbSerializer()

    def __init__(
        self,
        client: _t.Any = None,
        db: str = "cache-db",
        collection: str = "cache-collection",
        default_timeout: int | dt.timedelta = 300,
        key_prefix: str | None = None,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ):
        self.check_connection = check_connection
        super().__init__(
            default_timeout, ignore_delete_many_errors=ignore_delete_many_errors
        )
        try:
            import pymongo
        except ImportError as err:
            raise RuntimeError("no pymongo module found") from err

        if client is None or isinstance(client, str):
            client = pymongo.MongoClient(host=client, **kwargs)
        if self.check_connection:
            try:
                client.admin.command("ping")
            except pymongo.errors.PyMongoError as err:
                raise RuntimeError(
                    f"could not connect to MongoDB server: {err}"
                ) from err
        self.client = client[db][collection]
        index_info = self.client.index_information()
        all_keys = {
            subkey[0] for value in index_info.values() for subkey in value["key"]
        }
        if "id" not in all_keys:
            self.client.create_index("id", unique=True)
        self.key_prefix = key_prefix or ""
        self.collection = collection

    def _utcnow(self) -> dt.datetime:
        """Return a tz-aware UTC datetime representing the current time"""
        return dt.datetime.now(dt.UTC)

    def _expire_records(self) -> _t.Any:
        res = self.client.delete_many({"expiration": {"$lte": self._utcnow()}})
        return res

    def get(self, key: str) -> _t.Any:
        """
        Get a cache item

        :param key: The cache key of the item to fetch
        :return: cache value if not expired, else ``None``
        """
        self._expire_records()
        record = self.client.find_one({"id": self.key_prefix + key})
        value = None
        if record:
            value = self.serializer.loads(record["val"])
        return value

    def delete(self, key: str) -> bool:
        """
        Deletes an item from the cache.  This is a no-op if the item doesn't
        exist

        :param key: Key of the item to delete.
        :return: True if the key existed and was deleted
        """
        res = self.client.delete_one({"id": self.key_prefix + key})
        deleted = bool(res.deleted_count > 0)
        return deleted

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

        if not overwrite:
            # fail if a non-expired item with this key
            # already exists
            if self.has(key):
                return False

        dump = self.serializer.dumps(value)
        record: dict[str, str | bytes | None | dt.datetime] = {
            "id": self.key_prefix + key,
            "val": dump,
        }

        if normalized_timeout > 0:
            record["expiration"] = now + dt.timedelta(seconds=normalized_timeout)
        self.client.update_one({"id": self.key_prefix + key}, {"$set": record}, True)
        return True

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> _t.Any:
        self._expire_records()
        return self._set(key, value, timeout=timeout, overwrite=True)

    def set_many(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        self._expire_records()
        from pymongo import UpdateOne

        operations = []
        now = self._utcnow()
        normalized_timeout = self._normalize_timeout(timeout)
        for key, val in mapping.items():
            dump = self.serializer.dumps(val)

            record: dict[str, str | bytes | None | dt.datetime] = {
                "id": self.key_prefix + key,
                "val": dump,
            }

            if normalized_timeout > 0:
                record["expiration"] = now + dt.timedelta(seconds=normalized_timeout)
            operations.append(
                UpdateOne({"id": self.key_prefix + key}, {"$set": record}, upsert=True),
            )

        result = self.client.bulk_write(operations)
        keys = list(mapping.keys())
        if result.bulk_api_result["nUpserted"] != len(keys):
            query = self.client.find(
                {"id": {"$in": [self.key_prefix + key for key in keys]}}
            )
            keys = []
            for item in query:
                keys.append(item["id"])
        return keys

    def get_many(self, *keys: str) -> list[_t.Any]:
        results = self.get_dict(*keys)
        values = []
        for key in keys:
            values.append(results.get(key, None))
        return values

    def get_dict(self, *keys: str) -> dict[str, _t.Any]:
        self._expire_records()
        query = self.client.find(
            {"id": {"$in": [self.key_prefix + key for key in keys]}}
        )
        results = dict.fromkeys(keys, None)
        for item in query:
            value = self.serializer.loads(item["val"])
            results[item["id"][len(self.key_prefix) :]] = value
        return results

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> _t.Any:
        self._expire_records()
        return self._set(key, value, timeout=timeout, overwrite=False)

    def has(self, key: str) -> bool:
        self._expire_records()
        record = self.get(key)
        return record is not None

    def delete_many(self, *keys: str) -> list[_t.Any]:
        self._expire_records()
        res = list(keys)
        filter = {"id": {"$in": [self.key_prefix + key for key in keys]}}
        result = self.client.delete_many(filter)

        if result.deleted_count != len(keys):
            existing_keys = [
                item["id"][len(self.key_prefix) :] for item in self.client.find(filter)
            ]
            res = [item for item in keys if item not in existing_keys]
            if not self.ignore_delete_many_errors and existing_keys:
                raise RuntimeError(f"Failed to delete keys: {existing_keys}")
        return res

    def clear(self) -> bool:
        self.client.drop()
        return True
