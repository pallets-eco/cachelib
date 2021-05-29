import pickle
from time import time

from cachelib.base import BaseCache


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

    def __init__(self, threshold=500, default_timeout=300):
        BaseCache.__init__(self, default_timeout)
        self._cache = {}
        self.clear = self._cache.clear
        self._threshold = threshold or 500  # threshold = 0

    def _over_threshold(self):
        return len(self._cache) > self._threshold

    def _remove_expired(self, now):
        toremove = [k for k, (expires, _) in self._cache.items() if expires < now]
        for k in toremove:
            self._cache.pop(k, None)

    def _remove_older(self):
        k_ordered = (
            k for k, v in sorted(self._cache.items(), key=lambda item: item[1][0])
        )
        for k in k_ordered:
            self._cache.pop(k, None)
            if not self._over_threshold():
                break

    def _prune(self):
        if self._over_threshold():
            now = time()
            self._remove_expired(now)
        # remove older items if still over threshold
        if self._over_threshold():
            self._remove_older()

    def _normalize_timeout(self, timeout):
        timeout = BaseCache._normalize_timeout(self, timeout)
        if timeout > 0:
            timeout = time() + timeout
        return timeout

    def get(self, key):
        try:
            expires, value = self._cache[key]
            if expires == 0 or expires > time():
                return pickle.loads(value)
        except (KeyError, pickle.PickleError):
            return None

    def set(self, key, value, timeout=None):
        expires = self._normalize_timeout(timeout)
        self._prune()
        self._cache[key] = (expires, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
        return True

    def add(self, key, value, timeout=None):
        expires = self._normalize_timeout(timeout)
        self._prune()
        item = (expires, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
        if key in self._cache:
            return False
        self._cache.setdefault(key, item)
        return True

    def delete(self, key):
        return self._cache.pop(key, None) is not None

    def has(self, key):
        try:
            expires, value = self._cache[key]
            return expires == 0 or expires > time()
        except KeyError:
            return False
