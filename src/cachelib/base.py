import datetime as dt
import math
import typing as _t
import warnings


class BaseCache:
    """Base class for the cache systems.  All the cache systems implement this
    API or a superset of it.

    :param default_timeout: the default timeout that is used if
        no timeout is specified on :meth:`set`. Either a number of seconds
        or a :class:`datetime.timedelta`. A timeout
        of 0 indicates that the cache never expires.

        .. versionchanged:: 0.17.0
            Accepts a :class:`datetime.timedelta`.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.

        .. versionadded:: 0.16.0
    """

    def __init__(
        self,
        default_timeout: int | dt.timedelta = 300,
        ignore_delete_many_errors: bool = True,
    ) -> None:
        self.default_timeout = self._to_seconds(default_timeout)
        self.ignore_delete_many_errors = ignore_delete_many_errors

    @staticmethod
    def _to_seconds(timeout: int | float | dt.timedelta) -> int:
        """Convert a timeout to a whole number of seconds.

        :param timeout: the timeout to convert. In case a
            :class:`datetime.timedelta` is passed it will round up
            subseconds to whole seconds (i.e. 200 milliseconds
            will be rounded to 1 second)

        .. versionadded:: 0.17.0

        .. deprecated:: 0.17.0
            Float timeouts are deprecated and rounded up to whole
            seconds. They will raise a ``TypeError`` in a future release.
        """
        if isinstance(timeout, dt.timedelta):
            return math.ceil(timeout.total_seconds())
        if isinstance(timeout, float):
            warnings.warn(
                "Float timeouts are deprecated and will raise a TypeError"
                " in a future release. Use a whole number of seconds or a"
                " datetime.timedelta instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return math.ceil(timeout)
        if isinstance(timeout, int):
            return timeout
        raise TypeError(
            "timeout must be an int or datetime.timedelta, "
            f"got {type(timeout).__name__!r}"
        )

    def _normalize_timeout(self, timeout: int | dt.timedelta | None) -> int:
        if timeout is None:
            return self.default_timeout
        return self._to_seconds(timeout)

    def get(self, key: str) -> _t.Any:
        """Look up key in the cache and return the value for it.

        :param key: the key to be looked up.
        :returns: The value if it exists and is readable, else ``None``.
        """
        return None

    def delete(self, key: str) -> bool:
        """Delete ``key`` from the cache.

        :param key: the key to delete.
        :returns: Whether the key existed and has been deleted.
        """
        return True

    def get_many(self, *keys: str) -> list[_t.Any]:
        """Returns a list of values for the given keys.
        For each key an item in the list is created::

            foo, bar = cache.get_many("foo", "bar")

        Has the same error handling as :meth:`get`.

        :param keys: The function accepts multiple keys as positional
            arguments.
        """
        return [self.get(k) for k in keys]

    def get_dict(self, *keys: str) -> dict[str, _t.Any]:
        """Like :meth:`get_many` but return a dict::

            d = cache.get_dict("foo", "bar")
            foo = d["foo"]
            bar = d["bar"]

        :param keys: The function accepts multiple keys as positional
            arguments.
        """
        return dict(zip(keys, self.get_many(*keys), strict=True))

    def set(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool | None:
        """Add a new key/value to the cache (overwrites value, if key already
        exists in the cache).

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key, either a number of
            seconds or a :class:`datetime.timedelta` (if not
            specified, it uses the default timeout). A timeout of
            0 indicates that the cache never expires.
        :returns: ``True`` if key has been updated, ``False`` for backend
            errors. Pickling errors, however, will raise a subclass of
            ``pickle.PickleError``.
        """
        return True

    def add(
        self, key: str, value: _t.Any, timeout: int | dt.timedelta | None = None
    ) -> bool:
        """Works like :meth:`set` but does not overwrite the values of already
        existing keys.

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key, either a number of
            seconds or a :class:`datetime.timedelta` (if not
            specified, it uses the default timeout). A timeout of
            0 indicates that the cache never expires.
        :returns: Same as :meth:`set`, but also ``False`` for already
            existing keys.
        """
        return True

    def set_many(
        self, mapping: dict[str, _t.Any], timeout: int | dt.timedelta | None = None
    ) -> list[_t.Any]:
        """Sets multiple keys and values from a mapping.

        :param mapping: a mapping with the keys/values to set.
        :param timeout: the cache timeout for the key, either a number of
            seconds or a :class:`datetime.timedelta` (if not
            specified, it uses the default timeout). A timeout of
            0 indicates that the cache never expires.
        :returns: A list containing all keys successfully set
        """
        set_keys = []
        for key, value in mapping.items():
            if self.set(key, value, timeout):
                set_keys.append(key)
        return set_keys

    def delete_many(self, *keys: str) -> list[_t.Any]:
        """Deletes multiple keys at once.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        :returns: A list containing all successfully deleted keys
        :raises RuntimeError: If ``ignore_delete_many_errors`` is False and
            a key still exists after the delete attempt.
        """
        deleted_keys = []
        failed_keys = []
        for key in keys:
            # a key that is absent after the attempt counts as deleted
            if self.delete(key) or not self.has(key):
                deleted_keys.append(key)
            else:
                failed_keys.append(key)
        if not self.ignore_delete_many_errors and failed_keys:
            raise RuntimeError(f"Failed to delete keys: {failed_keys}")
        return deleted_keys

    def has(self, key: str) -> bool:
        """Checks if a key exists in the cache without returning it. This is a
        cheap operation that bypasses loading the actual data on the backend.

        :param key: the key to check
        """
        raise NotImplementedError(
            "%s doesn't have an efficient implementation of `has`. That "
            "means it is impossible to check whether a key exists without "
            "fully loading the key's data. Consider using `self.get` "
            "explicitly if you don't care about performance."
        )

    def clear(self) -> bool:
        """Clears the cache.  Keep in mind that not all caches support
        completely clearing the cache.

        :returns: Whether the cache has been cleared.
        """
        return True

    def inc(self, key: str, delta: int = 1) -> int | None:
        """Increments the value of a key by ``delta``.  If the key does
        not yet exist it is initialized with ``delta``.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to add.
        :returns: The new value or ``None`` for backend errors.
        """
        value = (self.get(key) or 0) + delta
        return value if self.set(key, value) else None

    def dec(self, key: str, delta: int = 1) -> int | None:
        """Decrements the value of a key by ``delta``.  If the key does
        not yet exist it is initialized with ``-delta``.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to subtract.
        :returns: The new value or ``None`` for backend errors.
        """
        value = (self.get(key) or 0) - delta
        return value if self.set(key, value) else None


class NullCache(BaseCache):
    """A cache that doesn't cache.  This can be useful for unit testing.

    :param default_timeout: a dummy parameter that is ignored but exists
                            for API compatibility with other caches.
    """

    def has(self, key: str) -> bool:
        return False
