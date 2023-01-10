import datetime
import logging
import typing as _t



try:
    from mongoengine import Document, StringField, BinaryField, DateTimeField # type: ignore
    from mongoengine.context_managers import switch_collection # type: ignore
except ImportError:
    logging.warning("no mongoengine module found")

from cachelib.base import BaseCache
from cachelib.serializers import BaseSerializer


class MongoCacheDocument(Document): # type: ignore
    key = StringField(required=True, unique=True)
    val = BinaryField(required=True)
    expiration = DateTimeField()


class MongoDbCache(BaseCache):
    """
    Implementation of cachelib.BaseCache that uses mongodb collection
    as the backend.

    Limitations: maximum MongoDB document size is 16mb

    :param host: mongodb connection string including database name
    :param collection: mongodb collection name
    :param default_timeout: Set the timeout in seconds after which cache entries
                            expire
    :param key_prefix: A prefix that should be added to all keys.

    """

    serializer = BaseSerializer()

    def __init__(
        self,
        host: _t.Optional[str] = "mongodb://127.0.0.1:27017/python-cache",
        collection: _t.Optional[str] = "python-cache",
        default_timeout: int = 300,
        key_prefix: _t.Optional[str] = None,
        **kwargs: _t.Any
    ):
        super().__init__(default_timeout)
        from mongoengine import connect
        self.client = connect(host=host, uuidrepresentation='standard')
        self.key_prefix = key_prefix or ""
        self.collection = collection

    def _utcnow(self) -> _t.Any:
        """Return a tz-aware UTC datetime representing the current time"""
        return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    def _expire_records(self) -> _t.Any:
        with switch_collection(MongoCacheDocument, self.collection) as Cache:
            Cache.objects(expiration__lte=self._utcnow()).delete()

    def get(self, key: str) -> _t.Any:
        """
        Get a cache item

        :param key: The cache key of the item to fetch
        :return: cache value if not expired, else None
        """
        self._expire_records()
        with switch_collection(MongoCacheDocument, self.collection) as Cache:

            cache_item = Cache.objects(key=self.key_prefix + key).first()
            if cache_item:
                response = cache_item.val
                value = self.serializer.loads(response)
                return value
            return None

    def delete(self, key: str) -> bool:
        """
        Deletes an item from the cache.  This is a no-op if the item doesn't
        exist

        :param key: Key of the item to delete.
        :return: True if the key existed and was deleted
        """
        res = 0
        with switch_collection(MongoCacheDocument, self.collection) as Cache:
            res = Cache.objects(key=self.key_prefix + key).delete()
        return res > 0

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

        with switch_collection(MongoCacheDocument, self.collection) as Cache:
            record = Cache.objects(key=self.key_prefix + key).first()

            if (not overwrite) and record:
                # fail if a non-expired item with this key
                # already exists
                return False

            if not record:
                record = Cache(key=self.key_prefix+key)
            dump = self.serializer.dumps(value)
            record.val = dump
            if timeout > 0:
                expiration_time = now + datetime.timedelta(seconds=timeout)
                record.expiration = expiration_time
            record.save()
            return True

    def set(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> _t.Any:
        self._expire_records()
        return self._set(self.key_prefix + key, value, timeout=timeout, overwrite=True)

    def add(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> _t.Any:
        self._expire_records()
        return self._set(self.key_prefix + key, value, timeout=timeout, overwrite=False)

    def has(self, key: str) -> bool:
        self._expire_records()
        with switch_collection(MongoCacheDocument, self.collection) as Cache:
            record = Cache.objects(key=self.key_prefix + key).first()
            return record is not None

    def delete_many(self, *keys: str) -> _t.List[_t.Any]:
        self._expire_records()
        res = list(keys)
        with switch_collection(MongoCacheDocument, self.collection) as Cache:
            count = Cache.objects(key__in=[self.key_prefix+key for key in keys]).delete()
            if count != len(keys):

                existing_keys = Cache.objects(key__in=[self.key_prefix+key for key in keys]).distinct('key')
                existing_keys = [item[len(self.key_prefix):] for item in existing_keys]
                res = [item for item in keys if item not in existing_keys]

        return res

    def clear(self) -> bool:
        with switch_collection(MongoCacheDocument, self.collection) as Cache:
            Cache.objects.delete()

        return True
