import platform
import typing as _t

from cachelib.base import BaseCache


class UWSGICache(BaseCache):
    """Implements the cache using uWSGI's caching framework.

    .. note::
        This class cannot be used when running under PyPy, because the uWSGI
        API implementation for PyPy is lacking the needed functionality.

    :param default_timeout: The default timeout in seconds.
    :param cache: The name of the caching instance to connect to, for
        example: mycache@localhost:3031, defaults to an empty string, which
        means uWSGI will cache in the local instance. If the cache is in the
        same instance as the werkzeug app, you only have to provide the name of
        the cache.
    :param secret_key: Key to sign cache entries with.

        .. warning::
            Without a secret key or in case the secret key is not secret anymore,
            anyone with write access to the uWSGI cache can trick your program
            into executing arbitrary code.

        .. versionadded:: 0.4.0
    """

    def __init__(
        self,
        default_timeout=300,
        cache="",
        *,
        secret_key: _t.Optional[_t.Union[_t.AnyStr, _t.Collection[_t.AnyStr]]] = None,
    ):
        BaseCache.__init__(self, default_timeout, secret_key=secret_key)

        if platform.python_implementation() == "PyPy":
            raise RuntimeError(
                "uWSGI caching does not work under PyPy, see "
                "the docs for more details."
            )

        try:
            import uwsgi

            self._uwsgi = uwsgi
        except ImportError:
            raise RuntimeError(
                "uWSGI could not be imported, are you running under uWSGI?"
            )

        self.cache = cache

    def get(self, key):
        rv = self._uwsgi.cache_get(key, self.cache)
        if rv is None:
            return
        return self._loads(rv)

    def delete(self, key):
        return self._uwsgi.cache_del(key, self.cache)

    def set(self, key, value, timeout=None):
        return self._uwsgi.cache_update(
            key, self._dumps(value), self._normalize_timeout(timeout), self.cache
        )

    def add(self, key, value, timeout=None):
        return self._uwsgi.cache_set(
            key, self._dumps(value), self._normalize_timeout(timeout), self.cache
        )

    def clear(self):
        return self._uwsgi.cache_clear(self.cache)

    def has(self, key):
        return self._uwsgi.cache_exists(key, self.cache) is not None
