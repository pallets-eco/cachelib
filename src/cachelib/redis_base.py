import typing as _t

from cachelib.base import BaseCache
from cachelib.serializers import BaseRedisSerializer


class BaseRedisCache(BaseCache):
    """Base class for Redis compatible cache backends.

    Subclasses are responsible for constructing the client and passing it
    to this base via ``super().__init__``.

    :param client: a connected client instance compatible with the Redis API.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    :param key_prefix: A prefix that should be added to all keys.
    """

    _read_client: _t.Any = None
    _write_client: _t.Any = None
    serializer = BaseRedisSerializer()

    def __init__(
        self,
        client: _t.Any,
        default_timeout: int = 300,
        key_prefix: _t.Optional[_t.Union[str, _t.Callable[[], str]]] = None,
    ):
        BaseCache.__init__(self, default_timeout)
        self._read_client = self._write_client = client
        self.key_prefix = key_prefix or ""

    def _get_prefix(self) -> str:
        return (
            self.key_prefix if isinstance(self.key_prefix, str) else self.key_prefix()
        )

    def _normalize_timeout(self, timeout: _t.Optional[int]) -> int:
        """Normalize timeout by setting it to default of 300 if
        not defined (None) or -1 if explicitly set to zero.

        :param timeout: timeout to normalize.
        """
        timeout = BaseCache._normalize_timeout(self, timeout)
        if timeout == 0:
            timeout = -1
        return timeout

    def get(self, key: str) -> _t.Any:
        return self.serializer.loads(
            self._read_client.get(f"{self._get_prefix()}{key}")
        )

    def get_many(self, *keys: str) -> _t.List[_t.Any]:
        if self.key_prefix:
            prefixed_keys = [f"{self._get_prefix()}{key}" for key in keys]
        else:
            prefixed_keys = list(keys)
        return [self.serializer.loads(x) for x in self._read_client.mget(prefixed_keys)]

    def set(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> _t.Any:
        timeout = self._normalize_timeout(timeout)
        dump = self.serializer.dumps(value)
        if timeout == -1:
            result = self._write_client.set(
                name=f"{self._get_prefix()}{key}", value=dump
            )
        else:
            result = self._write_client.setex(
                name=f"{self._get_prefix()}{key}", value=dump, time=timeout
            )
        return result

    def add(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> _t.Any:
        timeout = self._normalize_timeout(timeout)
        dump = self.serializer.dumps(value)
        created = self._write_client.setnx(
            name=f"{self._get_prefix()}{key}", value=dump
        )
        # handle case where timeout is explicitly set to zero
        if created and timeout != -1:
            self._write_client.expire(name=f"{self._get_prefix()}{key}", time=timeout)
        return created

    def set_many(
        self, mapping: _t.Dict[str, _t.Any], timeout: _t.Optional[int] = None
    ) -> _t.List[_t.Any]:
        timeout = self._normalize_timeout(timeout)
        # Use transaction=False to batch without calling redis MULTI
        # which is not supported by twemproxy
        pipe = self._write_client.pipeline(transaction=False)

        for key, value in mapping.items():
            dump = self.serializer.dumps(value)
            if timeout == -1:
                pipe.set(name=f"{self._get_prefix()}{key}", value=dump)
            else:
                pipe.setex(name=f"{self._get_prefix()}{key}", value=dump, time=timeout)
        results = pipe.execute()
        return [k for k, was_set in zip(mapping.keys(), results) if was_set]

    def delete(self, key: str) -> bool:
        return bool(self._write_client.delete(f"{self._get_prefix()}{key}"))

    def delete_many(self, *keys: str) -> _t.List[_t.Any]:
        if not keys:
            return []
        if self.key_prefix:
            prefixed_keys = [f"{self._get_prefix()}{key}" for key in keys]
        else:
            prefixed_keys = [k for k in keys]
        self._write_client.delete(*prefixed_keys)
        return [k for k in keys if not self.has(k)]

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
