from multiprocessing import shared_memory
shm_a = shared_memory.SharedMemory(create=True, size=1 * 1024 * 1024 * 1024)
shm_a.buf[:4] = bytearray(b'1234')
print(bytes(shm_a.buf[:4]))





import multiprocessing
import cachelib
import bitstruct.c as bitstruct

# Use bitstruct to serialize as predefined pattern that can handle pickle or primatives
# TODO: Add bitstruct as cachelib serializer

CACHE_ITEM = bitstruct.compile('u8p24u32')

class SharedMemoryCache(cachelib.simple.SimpleCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = multiprocessing.shared_memory.SharedMemory(
            create=False, size=self._threshold, name='psm_21467_46073',
        )

    def _over_threshold(self) -> bool:
        return len(self._cache) > self._threshold

    def _remove_expired(self, now: float) -> None:
        toremove = [k for k, (expires, _) in self._cache.items() if expires < now]
        for k in toremove:
            self._cache.pop(k, None)

    def _remove_older(self) -> None:
        k_ordered = (
            k
            for k, v in sorted(
                self._cache.items(), key=lambda item: item[1][0]  # type: ignore
            )
        )
        for k in k_ordered:
            self._cache.pop(k, None)
            if not self._over_threshold():
                break

    def _prune(self) -> None:
        if self._over_threshold():
            now = time()
            self._remove_expired(now)
        # remove older items if still over threshold
        if self._over_threshold():
            self._remove_older()

    def _normalize_timeout(self, timeout: _t.Optional[int]) -> int:
        timeout = BaseCache._normalize_timeout(self, timeout)
        if timeout > 0:
            timeout = int(time()) + timeout
        return timeout

    def get(self, key: str) -> _t.Any:
        try:
            expires, value = self._cache[key]
            if expires == 0 or expires > time():
                return self.serializer.loads(value)
        except KeyError:
            return None

    def set(
        self, key: str, value: _t.Any, timeout: _t.Optional[int] = None
    ) -> _t.Optional[bool]:
        expires = self._normalize_timeout(timeout)
        self._prune()
        self._cache[key] = (expires, self.serializer.dumps(value))
        return True

    def add(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> bool:
        expires = self._normalize_timeout(timeout)
        self._prune()
        item = (expires, self.serializer.dumps(value))
        if key in self._cache:
            return False
        self._cache.setdefault(key, item)
        return True

    def delete(self, key: str) -> bool:
        return self._cache.pop(key, None) is not None

    def has(self, key: str) -> bool:
        try:
            expires, value = self._cache[key]
            return bool(expires == 0 or expires > time())
        except KeyError:
            return False

    def clear(self) -> bool:
        self._cache.clear()
        return not bool(self._cache)
    

import platform
import typing as _t

from cachelib.base import BaseCache
from cachelib.serializers import UWSGISerializer


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
    """

    serializer = UWSGISerializer()

    def __init__(
        self,
        default_timeout: int = 300,
        cache: str = "",
    ):
        BaseCache.__init__(self, default_timeout)

        if platform.python_implementation() == "PyPy":
            raise RuntimeError(
                "uWSGI caching does not work under PyPy, see "
                "the docs for more details."
            )

        try:
            import uwsgi  # type: ignore

            self._uwsgi = uwsgi
        except ImportError as err:
            raise RuntimeError(
                "uWSGI could not be imported, are you running under uWSGI?"
            ) from err

        self.cache = cache

    def get(self, key: str) -> _t.Any:
        rv = self._uwsgi.cache_get(key, self.cache)
        if rv is None:
            return
        return self.serializer.loads(rv)

    def delete(self, key: str) -> bool:
        return bool(self._uwsgi.cache_del(key, self.cache))

    def set(
        self, key: str, value: _t.Any, timeout: _t.Optional[int] = None
    ) -> _t.Optional[bool]:
        result = self._uwsgi.cache_update(
            key,
            self.serializer.dumps(value),
            self._normalize_timeout(timeout),
            self.cache,
        )  # type: bool
        return result

    def add(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> bool:
        return bool(
            self._uwsgi.cache_set(
                key,
                self.serializer.dumps(value),
                self._normalize_timeout(timeout),
                self.cache,
            )
        )

    def clear(self) -> bool:
        return bool(self._uwsgi.cache_clear(self.cache))

    def has(self, key: str) -> bool:
        return self._uwsgi.cache_exists(key, self.cache) is not None
