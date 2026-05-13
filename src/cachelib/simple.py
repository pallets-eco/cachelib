import threading
import typing as _t
from time import time

from cachelib.base import BaseCache
from cachelib.serializers import SimpleSerializer


class SimpleCache(BaseCache):
    """Simple memory cache for single process environments.  This class exists
    mainly for the development server and is not 100% thread safe.  It tries
    to use as many atomic operations as possible and no locks for simplicity
    but it could happen under heavy load that keys are added multiple times.

    :param threshold: the maximum number of items the cache stores before
                      it starts deleting some.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    """

    serializer = SimpleSerializer()

    def __init__(
        self,
        threshold: int = 500,
        default_timeout: int = 300,
    ):
        BaseCache.__init__(self, default_timeout)
        self._cache: _t.Dict[str, _t.Any] = {}
        self._threshold = threshold or 500  # threshold = 0

    def _over_threshold(self) -> bool:
        return len(self._cache) > self._threshold

    def _remove_expired(self, now: float) -> None:
        toremove = [k for k, (expires, _) in self._cache.items() if expires < now]
        for k in toremove:
            self._cache.pop(k, None)

    def _remove_older(self) -> None:
        k_ordered = (
            k for k, v in sorted(self._cache.items(), key=lambda item: item[1][0])
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
        # key exists and is not expired, do not add
        if self.has(key):
            return False
        # key does not exist or is expired, add it
        self._cache[key] = item
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


class ThreadedSimpleCache(SimpleCache):
    """A thread-safe variant of :class:`SimpleCache`.

    All single-key operations (``get``, ``set``, ``add``, ``delete``, ``has``,
    ``inc``, ``dec``, ``clear``) are protected by a reentrant lock
    (``threading.RLock``), making this backend safe to share between
    threads. A reentrant lock is required because ``inc`` and ``dec`` call
    ``get`` and ``set`` internally, which would otherwise deadlock.

    The batch helpers inherited from :class:`BaseCache` (``get_many``,
    ``set_many``, ``delete_many``, ``get_dict``) acquire the lock for each
    underlying single-key call but are **not** atomic across the whole
    batch. Use single-key operations if you need an all-or-nothing
    guarantee across multiple keys.

    The API is otherwise identical to :class:`SimpleCache`. Use this
    backend whenever your application serves requests from multiple
    threads concurrently.

    :param threshold: the maximum number of items the cache stores before
                      it starts deleting some.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    """

    def __init__(
        self,
        threshold: int = 500,
        default_timeout: int = 300,
    ):
        super().__init__(threshold=threshold, default_timeout=default_timeout)
        self._lock = threading.RLock()

    def get(self, key: str) -> _t.Any:
        with self._lock:
            return super().get(key)

    def set(
        self, key: str, value: _t.Any, timeout: _t.Optional[int] = None
    ) -> _t.Optional[bool]:
        with self._lock:
            return super().set(key, value, timeout)

    def add(self, key: str, value: _t.Any, timeout: _t.Optional[int] = None) -> bool:
        with self._lock:
            return super().add(key, value, timeout)

    def delete(self, key: str) -> bool:
        with self._lock:
            return super().delete(key)

    def has(self, key: str) -> bool:
        with self._lock:
            return super().has(key)

    def clear(self) -> bool:
        with self._lock:
            return super().clear()

    def inc(self, key: str, delta: int = 1) -> _t.Optional[int]:
        with self._lock:
            return super().inc(key, delta)

    def dec(self, key: str, delta: int = 1) -> _t.Optional[int]:
        with self._lock:
            return super().dec(key, delta)
