import typing as _t

from cachelib.redis_base import BaseRedisCache
from cachelib.serializers import ValkeySerializer


class ValkeyCache(BaseRedisCache):
    """Uses the Valkey key-value store as a cache backend.

    The first argument can be either a string denoting address of the Valkey
    server or an object resembling an instance of a valkey.Valkey class.

    Note: Python Valkey API already takes care of encoding unicode strings on
    the fly.

    :param host: address of the Valkey server or an object which API is
                 compatible with the official Python Valkey client (valkey-py).
    :param port: port number on which Valkey server listens for connections.
    :param password: password authentication for the Valkey server.
    :param db: db (zero-based numeric index) on Valkey Server to connect.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    :param key_prefix: A prefix that should be added to all keys.

    Any additional keyword arguments will be passed to ``valkey.Valkey``.
    """

    serializer = ValkeySerializer()

    def __init__(
        self,
        host: _t.Any = "localhost",
        port: int = 6379,
        password: _t.Optional[str] = None,
        db: int = 0,
        default_timeout: int = 300,
        key_prefix: _t.Optional[_t.Union[str, _t.Callable[[], str]]] = None,
        **kwargs: _t.Any,
    ):
        if host is None:
            raise ValueError("ValkeyCache host parameter may not be None")
        if isinstance(host, str):
            try:
                import valkey
            except ImportError as err:
                raise RuntimeError("no valkey module found") from err
            if kwargs.get("decode_responses", None):
                raise ValueError("decode_responses is not supported by ValkeyCache.")
            client = valkey.Valkey(
                host=host, port=port, password=password, db=db, **kwargs
            )
        else:
            client = host
        super().__init__(client, default_timeout, key_prefix)

    def set_many(
        self, mapping: _t.Dict[str, _t.Any], timeout: _t.Optional[int] = None
    ) -> _t.List[_t.Any]:
        timeout = self._normalize_timeout(timeout)
        # Use transaction=False to batch without calling MULTI
        pipe = self._write_client.pipeline(transaction=False)

        for key, value in mapping.items():
            dump = self.serializer.dumps(value)
            if timeout == -1:
                pipe.set(name=f"{self._get_prefix()}{key}", value=dump)
            else:
                pipe.setex(name=f"{self._get_prefix()}{key}", value=dump, time=timeout)
        results = pipe.execute()
        return [k for k, was_set in zip(mapping.keys(), results) if was_set]
