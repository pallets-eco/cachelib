import datetime as dt
import re
import typing as _t
from contextlib import contextmanager
from contextlib import nullcontext
from functools import partial
from time import time

from cachelib.base import BaseCache

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
        library to use. Valid values are 'pylibmc', 'google', 'memcache', and 'libmc'.
        If not provided, the library will be auto-detected based on availability.

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
        new_keys = []
        normalized_keys = []
        for key in keys:
            normalized = self._normalize_key(key)
            if _test_memcached_key(normalized):
                new_keys.append(key)
                normalized_keys.append(normalized)
        with self._client_context() as client:
            client.delete_multi(normalized_keys)
        deleted_keys = [k for k in new_keys if not self.has(k)]
        if not self.ignore_delete_many_errors and len(deleted_keys) != len(new_keys):
            failed_keys = [k for k in new_keys if k not in deleted_keys]
            if failed_keys:
                raise RuntimeError(f"Failed to delete keys: {failed_keys}")
        return deleted_keys

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

    def inc(self, key: str, delta: int = 1) -> int | None:
        normalized_key = self._normalize_key(key)
        with self._client_context() as client:
            value = (client.get(normalized_key) or 0) + delta
        return value if self.set(key, value) else None

    def dec(self, key: str, delta: int = 1) -> int | None:
        normalized_key = self._normalize_key(key)
        with self._client_context() as client:
            value = (client.get(normalized_key) or 0) - delta
        return value if self.set(key, value) else None

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
