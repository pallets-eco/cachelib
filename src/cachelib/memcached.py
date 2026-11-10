import datetime as dt
import re
import typing as _t
from contextlib import contextmanager
from contextlib import nullcontext
from functools import partial
from time import time

from cachelib.base import BaseCache
from cachelib.serializers import SpreadSASLMemcachedSerializer

_test_memcached_key = re.compile(r"[^\x00-\x21\xff]{1,250}$").match
_MemcacheClientLib = _t.Literal["pylibmc", "google", "memcache", "libmc"]


class MemcachedCache(BaseCache):
    """A cache that uses memcached as backend.

    The first argument can either be an object that resembles the API of a
    ``memcache.Client`` or a tuple/list of server addresses. In the
    event that a tuple/list is passed, CacheLib tries to import the best
    available memcache library.

    This cache looks into the following packages/modules to find bindings for
    memcached:

        - ``pylibmc``
        - ``google.appengine.api.memcached``
        - ``memcache``
        - ``libmc``

    Implementation notes:
    This cache backend works around some limitations in memcached to
    simplify the interface. For example unicode keys are encoded to
    UTF-8 on the fly. Methods such as :meth:`~.BaseCache.get_dict` return
    the keys in the same format as passed.  Furthermore all get methods
    silently ignore key errors to not cause problems when untrusted user data
    is passed to the get methods which is often the case in web applications.
    This cache doesn't have a serializer since the underlying memcached client
    libraries handle serialization internally."

    :param servers: a list or tuple of server addresses or alternatively
        a ``memcache.Client`` or a compatible client.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~.BaseCache.set`. Either a number of seconds or a
        :class:`datetime.timedelta`. A timeout of
        0 indicates that the cache never expires.

        .. versionchanged:: 0.17.0
            Accepts a :class:`datetime.timedelta`.
    :param key_prefix: a prefix that is added before all keys.  This makes it
        possible to use the same memcached server for different
        applications.  Keep in mind that
        :meth:`~.BaseCache.clear` will also clear keys with a
        different prefix.
    :param pool_size: the size of the connection pool.  This is only used if
        the memcached client library supports connection pooling.

        .. versionadded:: 0.15.0
    :param pool_blocking: if the connection pool is exhausted, should the
        client block until a connection is available or raise
        an exception.  This is only used if the memcached
        client library supports connection pooling.

        .. versionadded:: 0.15.0
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.

        .. versionadded:: 0.16.0
    :param check_connection: If True, the constructor will verify the
        connection to the memcached server and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use.

        .. versionadded:: 0.16.1
    :param memcache_client_lib: Optional. A string indicating which memcache client
        library to use. Valid values are ``pylibmc``, ``google``, ``memcache``,
        and ``libmc``. If not provided, the library will be auto-detected based on
        availability.

        .. versionadded:: 0.17.0
    """

    def __init__(
        self,
        servers: _t.Any = None,
        default_timeout: int | dt.timedelta = 300,
        key_prefix: str | None = None,
        pool_size: int = 1,
        pool_blocking: bool = True,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
        memcache_client_lib: _MemcacheClientLib | None = None,
    ):
        self.check_connection = check_connection
        BaseCache.__init__(
            self, default_timeout, ignore_delete_many_errors=ignore_delete_many_errors
        )

        if servers is None or isinstance(servers, (list, tuple)):
            if servers is None:
                servers = ["127.0.0.1:11211"]
            self._client, self._client_context = self.import_preferred_memcache_lib(
                servers, pool_size, pool_blocking, memcache_client_lib
            )
        else:
            # NOTE: servers is actually an already initialized memcache
            # client.
            self._client = servers
            self._client_context = partial(nullcontext, self._client)

        self.key_prefix = key_prefix

    def _normalize_key(self, key: str) -> str:
        if self.key_prefix:
            key = self.key_prefix + key
        return key

    def _normalize_timeout(self, timeout: int | dt.timedelta | None) -> int:
        normalized_timeout = BaseCache._normalize_timeout(self, timeout)
        if normalized_timeout > 0:
            normalized_timeout = int(time()) + normalized_timeout
        return normalized_timeout

    def get(self, key: str) -> _t.Any:
        key = self._normalize_key(key)
        # memcached doesn't support keys longer than that.  Because often
        # checks for so long keys can occur because it's tested from user
        # submitted data etc we fail silently for getting.
        if _test_memcached_key(key):
            with self._client_context() as client:
                return client.get(key)

    def get_dict(self, *keys: str) -> dict[str, _t.Any]:
        return self._get_multi(*keys)

    def _get_multi(self, *keys: str) -> dict[str, _t.Any]:
        """Read keys exactly as stored. Missing keys map to ``None``."""
        key_mapping = {}
        for key in keys:
            encoded_key = self._normalize_key(key)
            if _test_memcached_key(key):
                key_mapping[encoded_key] = key
        _keys = list(key_mapping)
        with self._client_context() as client:
            d: dict[str, _t.Any] = client.get_multi(_keys)
            rv = d
        if self.key_prefix:
            rv = {}
            for key, value in d.items():
                rv[key_mapping[key]] = value
        if len(rv) < len(keys):
            for key in keys:
                if key not in rv:
                    rv[key] = None
        return rv

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        normalized_key = self._normalize_key(key)
        normalized_timeout = self._normalize_timeout(timeout)
        with self._client_context() as client:
            return bool(client.add(normalized_key, value, normalized_timeout))

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool | None:
        normalized_key = self._normalize_key(key)
        normalized_timeout = self._normalize_timeout(timeout)
        with self._client_context() as client:
            return bool(client.set(normalized_key, value, normalized_timeout))

    def get_many(self, *keys: str) -> list[_t.Any]:
        d = self.get_dict(*keys)
        return [d[key] for key in keys]

    def set_many(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        return self._set_multi(mapping, timeout)

    def _set_multi(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        """Store values exactly as given. Returns the keys that were set."""
        new_mapping = {}
        for key, value in mapping.items():
            key = self._normalize_key(key)
            new_mapping[key] = value

        normalized_timeout = self._normalize_timeout(timeout)
        with self._client_context() as client:
            failed_keys: list[_t.Any] = client.set_multi(
                new_mapping, normalized_timeout
            )
        k_normkey = zip(mapping.keys(), new_mapping.keys(), strict=True)
        return [k for k, nkey in k_normkey if nkey not in failed_keys]

    def delete(self, key: str) -> bool:
        normalized_key = self._normalize_key(key)
        if _test_memcached_key(normalized_key):
            with self._client_context() as client:
                return bool(client.delete(normalized_key))
        return False

    def delete_many(self, *keys: str) -> list[_t.Any]:
        new_keys = self._delete_multi(*keys)
        deleted_keys = [k for k in new_keys if not self.has(k)]
        if not self.ignore_delete_many_errors and len(deleted_keys) != len(new_keys):
            failed_keys = [k for k in new_keys if k not in deleted_keys]
            if failed_keys:
                raise RuntimeError(f"Failed to delete keys: {failed_keys}")
        return deleted_keys

    def _delete_multi(self, *keys: str) -> list[str]:
        """Delete keys exactly as stored. Returns the valid keys that were
        sent to memcached.
        """
        new_keys = []
        normalized_keys = []
        for key in keys:
            normalized = self._normalize_key(key)
            if _test_memcached_key(normalized):
                new_keys.append(key)
                normalized_keys.append(normalized)
        if normalized_keys:
            with self._client_context() as client:
                client.delete_multi(normalized_keys)
        return new_keys

    def has(self, key: str) -> bool:
        normalized_key = self._normalize_key(key)
        if _test_memcached_key(normalized_key):
            with self._client_context() as client:
                return bool(client.append(normalized_key, ""))
        return False

    def clear(self) -> bool:
        with self._client_context() as client:
            # python-memcached's flush_all returns None on success
            result = client.flush_all()
            return True if result is None else bool(result)

    def _create_pylibmc(
        self, servers: _t.Any, pool_size: int, pool_blocking: bool = True
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        import pylibmc  # type: ignore

        client = pylibmc.Client(servers)
        if self.check_connection:
            try:
                client.get_stats()
            except pylibmc.Error as err:
                raise RuntimeError(
                    f"could not connect to memcached server(s): {err}"
                ) from err
        pool = pylibmc.ClientPool(client, pool_size)
        reserve = partial(pool.reserve, block=pool_blocking)
        return pool, reserve

    def _create_google(
        self, servers: _t.Any, pool_size: int, pool_blocking: bool = True
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        from google.appengine.api import memcache  # type: ignore

        client = memcache.Client()
        return client, partial(nullcontext, client)

    def _create_memcache(
        self, servers: _t.Any, pool_size: int, pool_blocking: bool = True
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        import memcache  # type: ignore

        client = memcache.Client(servers)
        return client, partial(nullcontext, client)

    def _create_libmc(
        self, servers: _t.Any, pool_size: int, pool_blocking: bool = True
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        import libmc  # type: ignore

        # libmc.ClientPool doesn't take pool_size as a positional arg,
        # and its .client() always blocks/auto-grows, no non-blocking mode.
        pool = libmc.ClientPool(servers)
        pool.config(libmc.MC_INITIAL_CLIENTS, pool_size)
        pool.config(libmc.MC_MAX_CLIENTS, pool_size)

        @contextmanager
        def get_client() -> _t.Generator[_t.Any, None, None]:
            # flush_all is disabled by default in libmc; enable per connection.
            with pool.client() as client:
                client.toggle_flush_all_feature(True)
                yield client

        return pool, get_client

    def import_preferred_memcache_lib(
        self,
        servers: _t.Any,
        pool_size: int,
        pool_blocking: bool = True,
        memcache_client_lib: _MemcacheClientLib | None = None,
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        """Returns an initialized memcache client.  Used by the constructor."""
        factories = {
            "pylibmc": self._create_pylibmc,
            "google": self._create_google,
            "memcache": self._create_memcache,
            "libmc": self._create_libmc,
        }
        if memcache_client_lib is not None:
            factory = factories.get(memcache_client_lib)
            if factory is None:
                raise ValueError(f"Invalid memcache_client_lib: {memcache_client_lib}")
            return factory(servers, pool_size, pool_blocking)
        for factory in factories.values():
            try:
                return factory(servers, pool_size, pool_blocking)
            except ImportError:
                continue
        raise RuntimeError("no memcache module found")


class SASLMemcachedCache(MemcachedCache):
    """A :class:`MemcachedCache` that can authenticate with SASL.

    Of the supported memcached client libraries only ``pylibmc`` supports SASL.
    If ``username`` or ``password`` is given, ``pylibmc`` is used with the
    memcached binary protocol, which SASL requires. Without credentials this
    cache works like :class:`MemcachedCache` with any supported library.

    :param servers: a list or tuple of server addresses or alternatively
        a ``memcache.Client`` or a compatible client.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~.BaseCache.set`. Either a number of seconds or a
        :class:`datetime.timedelta`. A timeout of
        0 indicates that the cache never expires.
    :param key_prefix: a prefix that is added before all keys.
    :param username: the SASL username.
    :param password: the SASL password.
    :param pool_size: the size of the connection pool.  This is only used if
        the memcached client library supports connection pooling.
    :param pool_blocking: if the connection pool is exhausted, should the
        client block until a connection is available or raise
        an exception.  This is only used if the memcached
        client library supports connection pooling.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.
    :param check_connection: If True, the constructor will verify the
        connection to the memcached server and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use.
    :param memcache_client_lib: Optional. A string indicating which memcache client
        library to use. Valid values are ``pylibmc``, ``google``, ``memcache``,
        and ``libmc``. If not provided, the library will be auto-detected based on
        availability, or ``pylibmc`` is used if credentials are given. A
        :exc:`ValueError` is raised if credentials are given with another library.

    Any additional keyword arguments are passed to ``pylibmc.Client``.
    """

    def __init__(
        self,
        servers: _t.Any = None,
        default_timeout: int | dt.timedelta = 300,
        key_prefix: str | None = None,
        username: str | None = None,
        password: str | None = None,
        pool_size: int = 1,
        pool_blocking: bool = True,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
        memcache_client_lib: _MemcacheClientLib | None = None,
        **kwargs: _t.Any,
    ) -> None:
        self._username = username
        self._password = password
        self._pylibmc_kwargs = kwargs
        super().__init__(
            servers=servers,
            default_timeout=default_timeout,
            key_prefix=key_prefix,
            pool_size=pool_size,
            pool_blocking=pool_blocking,
            ignore_delete_many_errors=ignore_delete_many_errors,
            check_connection=check_connection,
            memcache_client_lib=memcache_client_lib,
        )

    @property
    def _has_credentials(self) -> bool:
        return self._username is not None or self._password is not None

    def import_preferred_memcache_lib(
        self,
        servers: _t.Any,
        pool_size: int,
        pool_blocking: bool = True,
        memcache_client_lib: _MemcacheClientLib | None = None,
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        if self._has_credentials:
            if memcache_client_lib not in (None, "pylibmc"):
                raise ValueError(
                    "SASL authentication is only supported by pylibmc, not"
                    f" {memcache_client_lib}"
                )
            memcache_client_lib = "pylibmc"
        return super().import_preferred_memcache_lib(
            servers, pool_size, pool_blocking, memcache_client_lib
        )

    def _create_pylibmc(
        self, servers: _t.Any, pool_size: int, pool_blocking: bool = True
    ) -> tuple[_t.Any, _t.Callable[[], _t.ContextManager[_t.Any]]]:
        import pylibmc

        client_kwargs = dict(self._pylibmc_kwargs)
        if self._has_credentials:
            client_kwargs.update(
                username=self._username, password=self._password, binary=True
            )
        client = pylibmc.Client(servers, **client_kwargs)
        if self.check_connection:
            try:
                client.get_stats()
            except pylibmc.Error as err:
                raise RuntimeError(
                    f"could not connect to memcached server(s): {err}"
                ) from err
        pool = pylibmc.ClientPool(client, pool_size)
        reserve = partial(pool.reserve, block=pool_blocking)
        return pool, reserve


class SpreadSASLMemcachedCache(SASLMemcachedCache):
    """A :class:`SASLMemcachedCache` that spreads values across multiple keys
    so values bigger than memcached's item size limit can be stored.

    .. note::
        Spreading requires serializing the value with :attr:`serializer`,
        which uses pickle by default and can significantly impact performance.

    :param chunksize: the maximum size in bytes of each chunk of the serialized
        value. memcached limits items to 1MB by default.
    :param maxchunk: the maximum number of chunks a value can be spread across.
        :meth:`set` raises a :exc:`ValueError` for bigger values.

    All other arguments are passed to :class:`SASLMemcachedCache`.
    """

    serializer = SpreadSASLMemcachedSerializer()

    def __init__(
        self,
        *args: _t.Any,
        chunksize: int = 1048448,
        maxchunk: int = 32,
        **kwargs: _t.Any,
    ) -> None:
        self.chunksize = chunksize
        self.maxchunk = maxchunk
        super().__init__(*args, **kwargs)

    def _genkeys(self, key: str) -> list[str]:
        return [f"{key}.{i}" for i in range(self.maxchunk)]

    def _chunks(self, key: str, value: _t.Any) -> dict[str, bytes] | None:
        serialized = self.serializer.dumps(value)
        if serialized is None:
            return None
        chunks = {
            f"{key}.{n}": serialized[i : i + self.chunksize]
            for n, i in enumerate(range(0, len(serialized), self.chunksize))
        }
        if len(chunks) > self.maxchunk:
            raise ValueError(f"Cannot store value in less than {self.maxchunk} keys")
        return chunks

    def _delete_chunks_from(self, key: str, start: int) -> None:
        # Leftover chunks of a previous, bigger value would corrupt the new one
        self._delete_multi(*self._genkeys(key)[start:])

    def get(self, key: str, chunk: bool = True) -> _t.Any:
        """Get a cached value.

        :param key: the key to be looked up.
        :param chunk: If set to ``False``, get a value that was stored with
            ``chunk=False`` instead of spread across multiple keys.
        """
        if not chunk:
            return super().get(key)
        keys = self._genkeys(key)
        values = self._get_multi(*keys)
        parts = []
        for k in keys:
            part = values[k]
            if part is None:
                break
            parts.append(part)
        if not parts:
            return None
        return self.serializer.loads(b"".join(parts))

    def set(
        self,
        key: str,
        value: _t.Any,
        timeout: int | dt.timedelta | None = None,
        chunk: bool = True,
    ) -> bool | None:
        """Set a value in the cache, spreading it across multiple keys.

        :param key: the key to set.
        :param value: the value for the key.
        :param timeout: the cache timeout for the key, either a number of
            seconds or a :class:`datetime.timedelta`.
        :param chunk: If set to ``False``, store the value in a single key
            without the serializer. This is faster, but fails for values bigger
            than memcached's item size limit, and the value must be read back
            with ``get(key, chunk=False)``.
        """
        if not chunk:
            return super().set(key, value, timeout)
        chunks = self._chunks(key, value)
        if chunks is None:
            return False
        stored = self._set_multi(chunks, timeout)
        self._delete_chunks_from(key, len(chunks))
        return len(stored) == len(chunks)

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        chunks = self._chunks(key, value)
        if chunks is None:
            return False
        first_key, *rest_keys = chunks
        # Adding the first chunk is what makes this fail for existing keys
        if not super().add(first_key, chunks[first_key], timeout):
            return False
        rest = {k: chunks[k] for k in rest_keys}
        stored = self._set_multi(rest, timeout) if rest else []
        self._delete_chunks_from(key, len(chunks))
        return len(stored) == len(rest)

    def delete(self, key: str) -> bool:
        existed = self.has(key)
        self._delete_multi(*self._genkeys(key))
        return existed

    def has(self, key: str) -> bool:
        return super().has(f"{key}.0")

    def get_dict(self, *keys: str) -> dict[str, _t.Any]:
        return {key: self.get(key) for key in keys}

    def set_many(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        return BaseCache.set_many(self, mapping, timeout)

    def delete_many(self, *keys: str) -> list[_t.Any]:
        return BaseCache.delete_many(self, *keys)
