import datetime as dt
import typing as _t

from cachelib.base import BaseCache
from cachelib.serializers import BaseRedisSerializer


class BaseRedisCache(BaseCache):
    """Base class for Redis compatible cache backends.

    Sub classes are responsible for constructing the client and passing it
    to this base via ``super().__init__``.

    :param client: a connected client instance compatible with the Redis API.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~.BaseCache.set`. Either a number of seconds or a
        :class:`datetime.timedelta`. A timeout of
        0 indicates that the cache never expires.

        .. versionchanged:: 0.17.0
            Accepts a :class:`datetime.timedelta`.
    :param key_prefix: A prefix that should be added to all keys.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.

        .. versionadded:: 0.16.0
    :param check_connection: If True, the constructor will verify the
        connection to the Redis server and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use.

        .. versionadded:: 0.16.1
    """

    _read_client: _t.Any = None
    _write_client: _t.Any = None
    serializer = BaseRedisSerializer()

    def __init__(
        self,
        client: _t.Any,
        default_timeout: int | dt.timedelta = 300,
        key_prefix: str | _t.Callable[[], str] | None = None,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
    ):
        BaseCache.__init__(
            self, default_timeout, ignore_delete_many_errors=ignore_delete_many_errors
        )
        self._read_client = self._write_client = client
        self.key_prefix = key_prefix or ""
        self.check_connection = check_connection

    def _get_prefix(self) -> str:
        return (
            self.key_prefix if isinstance(self.key_prefix, str) else self.key_prefix()
        )

    def _normalize_timeout(self, timeout: int | dt.timedelta | None) -> int:
        """Normalize timeout by setting it to default of 300 if
        not defined (None) or -1 if explicitly set to zero.

        :param timeout: timeout to normalize, either a number of seconds
            or a :class:`datetime.timedelta`.
        """
        normalized_timeout = BaseCache._normalize_timeout(self, timeout)
        if normalized_timeout == 0:
            normalized_timeout = -1
        return normalized_timeout

    def get(self, key: str) -> _t.Any:
        return self.serializer.loads(
            self._read_client.get(f"{self._get_prefix()}{key}")
        )

    def get_many(self, *keys: str) -> list[_t.Any]:
        if self.key_prefix:
            prefixed_keys = [f"{self._get_prefix()}{key}" for key in keys]
        else:
            prefixed_keys = list(keys)
        return [self.serializer.loads(x) for x in self._read_client.mget(prefixed_keys)]

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> _t.Any:
        normalized_timeout = self._normalize_timeout(timeout)
        dump = self.serializer.dumps(value)
        result = self._write_client.set(
            name=f"{self._get_prefix()}{key}",
            value=dump,
            ex=normalized_timeout if normalized_timeout != -1 else None,
        )
        return result

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> _t.Any:
        normalized_timeout = self._normalize_timeout(timeout)
        dump = self.serializer.dumps(value)
        created = self._write_client.setnx(
            name=f"{self._get_prefix()}{key}", value=dump
        )
        # handle case where timeout is explicitly set to zero
        if created and normalized_timeout != -1:
            self._write_client.expire(
                name=f"{self._get_prefix()}{key}", time=normalized_timeout
            )
        return created

    def set_many(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        normalized_timeout = self._normalize_timeout(timeout)
        # Use transaction=False to batch without calling redis MULTI
        # which is not supported by twemproxy
        pipe = self._write_client.pipeline(transaction=False)

        for key, value in mapping.items():
            dump = self.serializer.dumps(value)
            pipe.set(
                name=f"{self._get_prefix()}{key}",
                value=dump,
                ex=normalized_timeout if normalized_timeout != -1 else None,
            )
        results = pipe.execute()
        return [
            k for k, was_set in zip(mapping.keys(), results, strict=True) if was_set
        ]

    def delete(self, key: str) -> bool:
        return bool(self._write_client.delete(f"{self._get_prefix()}{key}"))

    def delete_many(self, *keys: str) -> list[_t.Any]:
        if not keys:
            return []
        if self.key_prefix:
            prefixed_keys = [f"{self._get_prefix()}{key}" for key in keys]
        else:
            prefixed_keys = [k for k in keys]
        self._write_client.delete(*prefixed_keys)
        deleted_keys = [k for k in keys if not self.has(k)]
        if not self.ignore_delete_many_errors and len(deleted_keys) != len(keys):
            failed_keys = [k for k in keys if k not in deleted_keys]
            if failed_keys:
                raise RuntimeError(f"Failed to delete keys: {failed_keys}")
        return deleted_keys

    def has(self, key: str) -> bool:
        return bool(self._read_client.exists(f"{self._get_prefix()}{key}"))

    def clear(self) -> bool:
        status = 0
        if self.key_prefix:
            keys = self._read_client.keys(self._get_prefix() + "*")
            if keys:
                status = self._write_client.delete(*keys)
        else:
            status = self._write_client.flushdb()
        return bool(status)

    def inc(self, key: str, delta: int = 1) -> _t.Any:
        return self._write_client.incr(name=f"{self._get_prefix()}{key}", amount=delta)

    def dec(self, key: str, delta: int = 1) -> _t.Any:
        return self._write_client.incr(name=f"{self._get_prefix()}{key}", amount=-delta)
