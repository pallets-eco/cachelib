import datetime as dt
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
        compatible with the official Python Valkey client (``valkey-py``).
    :param port: port number on which Valkey server listens for connections.
    :param password: password authentication for the Valkey server.
    :param db: db (zero-based numeric index) on Valkey Server to connect.
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
        connection to the Valkey server and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use.

        .. versionadded:: 0.16.1

    Any additional keyword arguments will be passed to ``valkey.Valkey``.
    """

    serializer = ValkeySerializer()

    def __init__(
        self,
        host: _t.Any = "localhost",
        port: int = 6379,
        password: str | None = None,
        db: int = 0,
        default_timeout: int | dt.timedelta = 300,
        key_prefix: str | _t.Callable[[], str] | None = None,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
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
        if check_connection:
            try:
                client.ping()
            except Exception as err:
                raise RuntimeError(
                    f"could not connect to Valkey server: {err}"
                ) from err
        super().__init__(
            client,
            default_timeout,
            key_prefix,
            ignore_delete_many_errors,
            check_connection,
        )

    def set_many(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        normalized_timeout = self._normalize_timeout(timeout)
        # Use transaction=False to batch without calling MULTI
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
