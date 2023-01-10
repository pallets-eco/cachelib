import datetime
import logging
import typing as _t


try:
    import pymongo
except ImportError:
    logging.warning("no pymongo module found")

from cachelib.base import BaseCache
from cachelib.serializers import BaseSerializer


class MongoDbCache(BaseCache):
    """
    Implementation of cachelib.BaseCache that uses mongodb collection
    as the backend.

    Limitations: maximum MongoDB document size is 16mb

    :param host: mongodb connection string
    :param db: mongodb database name
    :param collection: mongodb collection name
    :param default_timeout: Set the timeout in seconds after which cache entries
                            expire
    :param key_prefix: A prefix that should be added to all keys.

    """

    serializer = BaseSerializer()

    def __init__(
        self,
        host: _t.Optional[
            str
        ] = "mongodb://127.0.0.1:27017/python-cache&serverSelectionTimeoutMs=5000",
        db: _t.Optional[str] = "cache-db",
        collection: _t.Optional[str] = "cache-collection",
        default_timeout: int = 300,
        key_prefix: _t.Optional[str] = None,
        **kwargs: _t.Any
    ):
        super().__init__(default_timeout)
        client = pymongo.MongoClient(host=host)  # type: ignore
        self.client = client[db][collection]  # type: ignore
        self.key_prefix = key_prefix or ""
        self.collection = collection

    def _utcnow(self) -> _t.Any:
        """Return a tz-aware UTC datetime representing the current time"""
        return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    def _expire_records(self) -> _t.Any:
        res = self.client.delete_many({"expiration": {"$lte": self._utcnow()}})
        return res

    def get(self, key: str) -> _t.Any:
        """
        Get a cache item

        :param key: The cache key of the item to fetch
        :return: cache value if not expired, else None
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
        return res.deleted_count > 0

    def _set(
        self,
        key: str,
        value: _t.Any,
        timeout: _t.Optional[int] = None,
        overwrite: _t.Optional[bool] = True,
    ) -> _t.Any:
        """
        Store a cache item, with the option to not overwrite existing items

        :param key: Cache key to use
        :param value: a serializable object
        :param timeout: The timeout in seconds for the cached item, to override
                        the default
        :param overwrite: If true, overwrite any existing cache item with key.
                          If false, the new value will only be stored if no
                          non-expired cache item exists with key.
        :return: True if the new item was stored.
        """
        timeout = self._normalize_timeout(timeout)
        now = self._utcnow()

        if not overwrite:
            # fail if a non-expired item with this key
            # already exists
            if self.has(key):
                return False

        dump = self.serializer.dumps(value)
        record = {"id": self.key_prefix + key, "val": dump}

        if timeout > 0:
            record["expiration"] = now + datetime.timedelta(seconds=timeout)
        self.client.update_one({"id": self.key_prefix + key}, {"$set": record}, True)
        return True

    def set(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> _t.Any:
        self._expire_records()
        return self._set(key, value, timeout=timeout, overwrite=True)

    def add(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> _t.Any:
        self._expire_records()
        return self._set(key, value, timeout=timeout, overwrite=False)

    def has(self, key: str) -> bool:
        self._expire_records()
        record = self.get(key)
        return record is not None

    def delete_many(self, *keys: str) -> _t.List[_t.Any]:
        self._expire_records()
        res = list(keys)
        filter = {"id": {"$in": [self.key_prefix + key for key in keys]}}
        result = self.client.delete_many(filter)

        if result.deleted_count != len(keys):

            existing_keys = [
                item["id"][len(self.key_prefix) :] for item in self.client.find(filter)
            ]
            res = [item for item in keys if item not in existing_keys]

        return res

    def clear(self) -> bool:
        self.client.drop()
        return True
