import collections.abc as cabc
import datetime as dt
import logging
import typing as _t

from cachelib.base import BaseCache
from cachelib.serializers import GoogleCloudStorageSerializer

logger = logging.getLogger(__name__)

# The GCS JSON API accepts at most 100 calls per batch request.
_BATCH_SIZE = 100

# The content type tells get() whether to deserialize.
_SERIALIZED_CONTENT_TYPE = "application/json"
_RAW_CONTENT_TYPE = "application/octet-stream"


class GoogleCloudStorageCache(BaseCache):
    """Uses a Google Cloud Storage bucket as a cache backend.

    .. note::
        User-contributed functionality. This project does not guarantee that
        this functionality will be maintained or functional at any given time.

    .. note::
        Cache keys must meet GCS criteria for a valid object name (a sequence
        of Unicode characters whose UTF-8 encoding is at most 1024 bytes long).

    .. note::
        Expired cache objects are not automatically purged. If
        ``delete_expired_objects_on_read=True``, they will be deleted following
        an attempted read (which reduces performance). Otherwise, you have to
        delete stale objects yourself. Consider a GCS bucket life cycle rule or
        other out-of-band process. For example you can use the following rule::

            {
              "rule": [
                {
                  "action": {"type": "Delete"},
                  "condition": {"daysSinceCustomTime": 0}
                }
              ]
            }

        https://cloud.google.com/storage/docs/lifecycle#dayssincecustomtime

    .. note::
        ``bytes`` values are stored as is with the ``application/octet-stream``
        content type. Other values are stored using :attr:`serializer` with the
        ``application/json`` content type.

    .. note::
        :meth:`inc` and :meth:`dec` are not atomic and reset the timeout of
        the key to the default. :meth:`get_many` and :meth:`set_many` make one
        request per key.

    :param bucket: Name of the bucket to use. It must already exist.
    :param client: A ``google.cloud.storage.Client`` to use. If not given, one
        is created using ``anonymous`` and any additional keyword arguments.
    :param key_prefix: A prefix that should be added to all keys.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~BaseCache.set`. Either a number of seconds or a
        :class:`datetime.timedelta`. A timeout of 0 indicates that the cache
        never expires.
    :param delete_expired_objects_on_read: If True, if a read finds a stale
        object, it will be deleted before a response is returned. Will slow
        down responses.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.
    :param anonymous: If True, create the client with anonymous credentials.
        Useful for testing against an emulator. The project defaults to
        ``"test"`` unless a ``project`` keyword argument is given.
    :param check_connection: If True, the constructor will verify that the
        bucket exists and raise a RuntimeError if it does not or cannot be
        reached. If False (default), no request is made at construction and
        errors surface on first use.

    Any additional keyword arguments will be passed to
    ``google.cloud.storage.Client`` when ``client`` is not given.
    """

    serializer = GoogleCloudStorageSerializer()

    def __init__(
        self,
        bucket: str = "mybucket",
        client: _t.Any = None,
        key_prefix: str | None = None,
        default_timeout: int | dt.timedelta = 300,
        delete_expired_objects_on_read: bool = False,
        ignore_delete_many_errors: bool = True,
        anonymous: bool = False,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ) -> None:
        super().__init__(
            default_timeout, ignore_delete_many_errors=ignore_delete_many_errors
        )

        try:
            from google.auth.credentials import AnonymousCredentials
            from google.cloud import exceptions
            from google.cloud import storage  # type: ignore[attr-defined]
        except ImportError as err:
            raise RuntimeError("no google-cloud-storage module found") from err

        if not isinstance(bucket, str):
            raise ValueError("bucket parameter must be a string")

        if client is None:
            if anonymous:
                kwargs.setdefault("project", "test")
                client = storage.Client(
                    credentials=AnonymousCredentials(),  # type: ignore[no-untyped-call]
                    **kwargs,
                )
            else:
                client = storage.Client(**kwargs)

        self.client = client
        self.key_prefix = key_prefix or ""
        self.delete_expired_objects_on_read = delete_expired_objects_on_read
        self.check_connection = check_connection
        self._not_found_exception = exceptions.NotFound
        self._precondition_failed_exception = exceptions.PreconditionFailed
        self._too_many_requests_exception = exceptions.TooManyRequests
        self._google_cloud_error = exceptions.GoogleCloudError

        if self.check_connection:
            try:
                self.bucket = client.get_bucket(bucket)
            except exceptions.NotFound as err:
                raise RuntimeError(f"GCS bucket {bucket!r} not found") from err
            except exceptions.GoogleCloudError as err:
                raise RuntimeError(
                    f"could not connect to Google Cloud Storage: {err}"
                ) from err
        else:
            self.bucket = client.bucket(bucket)

    def _now(self, delta: int = 0) -> dt.datetime:
        return dt.datetime.now(dt.UTC) + dt.timedelta(seconds=delta)

    def _is_expired(self, blob: _t.Any) -> bool:
        return blob.custom_time is not None and bool(self._now() > blob.custom_time)

    def _evict_expired(self, blob: _t.Any) -> None:
        if not self.delete_expired_objects_on_read:
            return
        try:
            # Don't delete a newer value written after the expiry check
            self.bucket.delete_blob(blob.name, if_generation_match=blob.generation)
        except (
            self._not_found_exception,
            self._precondition_failed_exception,
            self._too_many_requests_exception,
        ):
            pass

    def get(self, key: str) -> _t.Any:
        full_key = self.key_prefix + key
        blob = self.bucket.get_blob(full_key)
        if blob is None:
            logger.debug("get key %r -> miss", full_key)
            return None
        if self._is_expired(blob):
            self._evict_expired(blob)
            logger.debug("get key %r -> miss (expired)", full_key)
            return None
        try:
            # Don't return content from a different version than was checked
            data = blob.download_as_bytes(if_generation_match=blob.generation)
        except (self._not_found_exception, self._precondition_failed_exception):
            logger.debug("get key %r -> miss", full_key)
            return None
        logger.debug("get key %r -> hit", full_key)
        if blob.content_type == _RAW_CONTENT_TYPE:
            return data
        return self.serializer.loads(data)

    def _set(
        self,
        full_key: str,
        value: _t.Any,
        timeout: int | dt.timedelta | None = None,
        if_generation_match: int | None = None,
    ) -> bool:
        data: bytes | None
        if isinstance(value, bytes):
            data, content_type = value, _RAW_CONTENT_TYPE
        else:
            data = self.serializer.dumps(value)
            if data is None:
                logger.debug("set key %r -> False (not serializable)", full_key)
                return False
            content_type = _SERIALIZED_CONTENT_TYPE
        blob = self.bucket.blob(full_key)
        seconds = self._normalize_timeout(timeout)
        if seconds != 0:
            # Use 'Custom-Time' for expiry
            # https://cloud.google.com/storage/docs/metadata#custom-time
            blob.custom_time = self._now(delta=seconds)
        try:
            blob.upload_from_string(
                data,
                content_type=content_type,
                if_generation_match=if_generation_match,
            )
        except (
            self._precondition_failed_exception,
            self._too_many_requests_exception,
        ):
            logger.debug("set key %r -> False", full_key)
            return False
        logger.debug("set key %r -> True", full_key)
        return True

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        return self._set(self.key_prefix + key, value, timeout)

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        full_key = self.key_prefix + key
        blob = self.bucket.get_blob(full_key)
        if blob is not None and not self._is_expired(blob):
            logger.debug("add key %r -> not added", full_key)
            return False
        # Only write if the object is still missing (generation 0) or still the
        # expired generation, so concurrent adds can't both succeed
        generation = 0 if blob is None else blob.generation
        return self._set(full_key, value, timeout, if_generation_match=generation)

    def delete(self, key: str) -> bool:
        try:
            self.bucket.delete_blob(self.key_prefix + key)
        except (self._not_found_exception, self._too_many_requests_exception):
            return False
        return True

    def _delete_blobs(self, names: cabc.Iterable[str]) -> cabc.Set[str]:
        """Delete objects by their full name in batches. Returns the names that
        could not be deleted. Objects that don't exist count as deleted.
        """
        failed: set[str] = set()
        chunk: list[str] = []
        for name in names:
            chunk.append(name)
            if len(chunk) == _BATCH_SIZE:
                failed |= self._delete_batch(chunk)
                chunk = []
        if chunk:
            failed |= self._delete_batch(chunk)
        return failed

    def _delete_batch(self, names: list[str]) -> cabc.Set[str]:
        try:
            with self.client.batch():
                for name in names:
                    self.bucket.delete_blob(name)
        except (self._google_cloud_error, ValueError):
            # A failed batch only reports its last error, and a malformed batch
            # response raises ValueError, so retry one by one to find out which
            # objects could not be deleted
            return {name for name in names if not self._delete_blob(name)}
        return set()

    def _delete_blob(self, name: str) -> bool:
        try:
            self.bucket.delete_blob(name)
        except self._not_found_exception:
            return True
        except self._google_cloud_error:
            return False
        return True

    def delete_many(self, *keys: str) -> list[str]:
        failed = self._delete_blobs(self.key_prefix + key for key in keys)
        failed_keys = [key for key in keys if self.key_prefix + key in failed]
        if not self.ignore_delete_many_errors and failed_keys:
            raise RuntimeError(f"Failed to delete keys: {failed_keys}")
        return [key for key in keys if self.key_prefix + key not in failed]

    def has(self, key: str) -> bool:
        full_key = self.key_prefix + key
        blob = self.bucket.get_blob(full_key)
        if blob is None:
            logger.debug("has key %r -> False", full_key)
            return False
        if self._is_expired(blob):
            self._evict_expired(blob)
            logger.debug("has key %r -> False (expired)", full_key)
            return False
        logger.debug("has key %r -> True", full_key)
        return True

    def _prune(self, clear_all: bool = False) -> bool:
        blobs = self.client.list_blobs(
            self.bucket,
            prefix=self.key_prefix,
            fields="items(name,customTime),nextPageToken",
        )
        names = [blob.name for blob in blobs if clear_all or self._is_expired(blob)]
        failed = self._delete_blobs(names)
        logger.debug("evicted %d key(s)", len(names) - len(failed))
        return not failed

    def clear(self) -> bool:
        return self._prune(clear_all=True)
