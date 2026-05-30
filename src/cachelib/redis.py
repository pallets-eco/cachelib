import typing as _t
from collections import abc as cabc

from cachelib.redis_base import BaseRedisCache
from cachelib.serializers import RedisSerializer


class RedisCache(BaseRedisCache):
    """Uses the Redis key-value store as a cache backend.

    The first argument can be either a string denoting address of the Redis
    server or an object resembling an instance of a redis.Redis class.

    Note: Python Redis API already takes care of encoding unicode strings on
    the fly.

    :param host: address of the Redis server or an object which API is
                 compatible with the official Python Redis client (redis-py).
    :param port: port number on which Redis server listens for connections.
    :param password: password authentication for the Redis server.
    :param db: db (zero-based numeric index) on Redis Server to connect.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    :param key_prefix: A prefix that should be added to all keys.
    :param secret_key: If given, cache entries are signed with this key so that
                       tampering with values stored in Redis is detected on
                       read. Without it, anyone with write access to the Redis
                       instance could craft malicious cache values that execute
                       arbitrary code when loaded.

        .. versionadded:: 0.15.0

    Any additional keyword arguments will be passed to ``redis.Redis``.
    """

    serializer = RedisSerializer()

    def __init__(
        self,
        host: _t.Any = "localhost",
        port: int = 6379,
        password: _t.Optional[str] = None,
        db: int = 0,
        default_timeout: int = 300,
        key_prefix: _t.Optional[_t.Union[str, _t.Callable[[], str]]] = None,
        *,
        secret_key: _t.Optional[
            "_t.Union[str, bytes, cabc.Iterable[str], cabc.Iterable[bytes]]"
        ] = None,
        **kwargs: _t.Any,
    ):
        if host is None:
            raise ValueError("RedisCache host parameter may not be None")
        if isinstance(host, str):
            try:
                import redis
            except ImportError as err:
                raise RuntimeError("no redis module found") from err
            if kwargs.get("decode_responses", None):
                raise ValueError("decode_responses is not supported by RedisCache.")
            client = redis.Redis(
                host=host, port=port, password=password, db=db, **kwargs
            )
        else:
            client = host
        super().__init__(client, default_timeout, key_prefix, secret_key=secret_key)
