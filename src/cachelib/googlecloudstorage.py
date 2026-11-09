import datetime as dt
import json
import logging
import typing as _t
from collections.abc import Iterable

from cachelib.base import BaseCache

logger = logging.getLogger(__name__)


class GoogleCloudStorageCache(BaseCache):
    """Uses an Google Cloud Storage bucket as a cache backend.
    Note: User-contributed functionality. This project does not guarantee that
    this functionality will be maintained or functional at any given time.

    Note: Cache keys must meet GCS criteria for a valid object name (a sequence
    of Unicode characters whose UTF-8 encoding is at most 1024 bytes long).

    Note: Expired cache objects are not automatically purged. If
    delete_expired_objects_on_read=True, they will be deleted following an
    attempted read (which reduces performance). Otherwise, you have to delete
    stale objects yourself. Consider an GCS bucket life cycle rule or other
    out-of-band process. For example you can use the following rule::

        {
          "rule":
            [
              {"action": {"type": "Delete"}, "condition": {"daysSinceCustomTime": 0}}
            ]
        }

    https://cloud.google.com/storage/docs/lifecycle#dayssincecustomtime

    :param bucket: Required. Name of the bucket to use. It must already exist.
    :param key_prefix: A prefix that should be added to all keys.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~BaseCache.set`. A timeout of
        0 indicates that the cache never expires.
    :param delete_expired_objects_on_read: If True, if a read finds a stale
        object, it will be deleted before
        a response is returned. Will slow
        down responses.
    :param anonymous: If true, use anonymous credentials. Useful for testing.

    Any additional keyword arguments will be passed to ``google.cloud.storage.Client``.
    """

    def __init__(
        self,
        bucket: _t.Any = "mybucket",
        key_prefix: str | None = None,
        default_timeout: int = 300,
        delete_expired_objects_on_read: bool = False,
        ignore_delete_many_errors: bool = True,
        anonymous: bool = False,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ) -> None:
        self.check_connection = check_connection
        super().__init__(
            default_timeout=default_timeout,
            ignore_delete_many_errors=ignore_delete_many_errors,
        )

        try:
            from google.auth.credentials import AnonymousCredentials
            from google.cloud import exceptions
            from google.cloud import storage  # type: ignore[attr-defined]
        except ImportError as err:
            raise RuntimeError("no google-cloud-storage module found") from err

        if bucket is None:
            raise ValueError("bucket parameter must be a string")
        if isinstance(bucket, str):
            if anonymous:
                client = storage.Client(
                    credentials=AnonymousCredentials(),  # type: ignore[no-untyped-call]
                    project="test",
                    **kwargs,
                )
            else:
                client = storage.Client(**kwargs)
        else:
            client = bucket

        if self.check_connection:
            try:
                client.get_bucket(bucket)
            except exceptions.NotFound as err:
                raise RuntimeError(f"GCS bucket {bucket} not found") from err

        self.client = client
        self.bucket = self.client.get_bucket(bucket)
        self.key_prefix = key_prefix or ""
        self.default_timeout = default_timeout
        self.delete_expired_objects_on_read = delete_expired_objects_on_read
        self._not_found_exception = exceptions.NotFound
        self._too_many_requests_exception = exceptions.TooManyRequests

    def get(self, key: str) -> _t.Any:
        result = None
        expired = False
        hit_or_miss = "miss"
        full_key = self.key_prefix + key
        blob = self.bucket.get_blob(full_key)
        if blob is not None:
            expired = blob.custom_time and self._now() > blob.custom_time
            if expired:
                # Object is stale
                if self.delete_expired_objects_on_read:
                    self._delete(full_key)
            else:
                try:
                    result = blob.download_as_bytes()
                    hit_or_miss = "hit"
                    if blob.content_type == "application/json":
                        result = json.loads(result)
                except self._not_found_exception:
                    pass
        expiredstr = "(expired)" if expired else ""
        logger.debug("get key %r -> %s %s", full_key, hit_or_miss, expiredstr)
        return result

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        result = False
        full_key = self.key_prefix + key
        content_type = "application/json"
        try:
            value = json.dumps(value)
        except (UnicodeDecodeError, TypeError):
            content_type = "application/octet-stream"
        blob = self.bucket.blob(full_key)
        seconds = self._normalize_timeout(timeout)
        if seconds != 0:
            # Use 'Custom-Time' for expiry
            # https://cloud.google.com/storage/docs/metadata#custom-time
            blob.custom_time = self._now(delta=seconds)
        try:
            blob.upload_from_string(value, content_type=content_type)
            result = True
        except self._too_many_requests_exception:
            pass
        logger.debug("set key %r -> %s", full_key, result)
        return result

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        full_key = self.key_prefix + key
        if self._has(full_key):
            logger.debug("add key %r -> not added", full_key)
            return False
        else:
            return self.set(key, value, timeout)

    def delete(self, key: str) -> bool:
        full_key = self.key_prefix + key
        return self._delete(full_key)

    def delete_many(self, *keys: str) -> _t.Any:
        return self._delete_many(self.key_prefix + key for key in keys)

    def has(self, key: str) -> bool:
        full_key = self.key_prefix + key
        return self._has(full_key)

    def clear(self) -> bool:
        return self._prune(clear_all=True)

    def _prune(self, clear_all: bool = False) -> bool:
        # Delete in batches of 100 which is much faster than individual deletes
        nremoved = 0
        now = self._now()
        response_iterator = self.client.list_blobs(
            self.bucket,
            prefix=self.key_prefix,
            fields="items(name,customTime),nextPageToken",
        )
        to_delete = []
        for blob in response_iterator:
            if clear_all or blob.custom_time and blob.custom_time < now:
                to_delete.append(blob.name)
                nremoved += 1
                if len(to_delete) == 100:
                    self._delete_many(to_delete)
                    to_delete = []
        # Delete the remainder
        if to_delete:
            self._delete_many(to_delete)
        logger.debug("evicted %d key(s)", nremoved)
        return True

    def _delete(self, key: str) -> bool:
        return self._delete_many([key])

    def _delete_many(self, keys: Iterable[str]) -> bool:
        try:
            with self.client.batch():
                for key in keys:
                    self.bucket.delete_blob(key)
        except (self._not_found_exception, self._too_many_requests_exception):
            pass
        return True

    def _has(self, key: str) -> bool:
        result = False
        expired = False
        blob = self.bucket.get_blob(key)
        if blob is not None:
            expired = blob.custom_time and self._now() > blob.custom_time
            if expired:
                # Exists but is stale
                if self.delete_expired_objects_on_read:
                    self._delete(key)
            else:
                result = True
        expiredstr = "(expired)" if expired else ""
        logger.debug("has key %r -> %s %s", key, result, expiredstr)
        return result

    def _now(self, delta: int = 0) -> dt.datetime:
        return dt.datetime.now(dt.UTC) + dt.timedelta(seconds=delta)
