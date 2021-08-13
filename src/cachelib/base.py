import base64
import io
import pickle
import typing as _t

import itsdangerous


class _Base85Pickler:
    """
    Pickles Base85 safe. To allow multiple reads from the same file, encoded output must
    not contain any newlines. Base85 has less overhead than Base64.
    """

    @staticmethod
    def dumps(obj: _t.Any) -> bytes:
        return base64.b85encode(pickle.dumps(obj))

    @staticmethod
    def loads(data: _t.AnyStr) -> bytes:
        return pickle.loads(base64.b85decode(data))


class BaseCache:
    """Baseclass for the cache systems.  All the cache systems implement this
    API or a superset of it.

    :param default_timeout: the default timeout (in seconds) that is used if
                            no timeout is specified on :meth:`set`. A timeout
                            of 0 indicates that the cache never expires.

    :param secret_key:      Key to sign cache entries with.
    """

    def __init__(
        self,
        default_timeout=300,
        *,
        secret_key: _t.Optional[_t.Union[_t.AnyStr, _t.Collection[_t.AnyStr]]] = None
    ):
        self.default_timeout = default_timeout
        if secret_key is not None:
            self.__signed_serializer = itsdangerous.Serializer(
                secret_key, serializer=_Base85Pickler
            )
        else:
            self.__signed_serializer = None

    def _normalize_timeout(self, timeout):
        if timeout is None:
            timeout = self.default_timeout
        return timeout

    def _dumps(self, to_serialize: _t.Any) -> bytes:
        buf = io.BytesIO()
        self._dump(to_serialize, buf)
        return buf.getvalue()

    def _dump(self, to_serialize: _t.Any, file: _t.IO[bytes]) -> None:
        if self.__signed_serializer:
            self.__signed_serializer.dump(to_serialize, file)
            file.write(b"\n")
        else:
            return pickle.dump(to_serialize, file)

    def _loads(self, serialized: bytes) -> _t.Any:
        buf = io.BytesIO(serialized)
        return self._unpack(buf)

    def _load(self, file: _t.IO[bytes]) -> _t.Any:
        if self.__signed_serializer:
            try:
                read = file.readline()[:-1]
                return self.__signed_serializer.loads(read)
            except (itsdangerous.BadSignature, pickle.UnpicklingError):
                return None
        return pickle.load(file)

    def get(self, key):
        """Look up key in the cache and return the value for it.

        :param key: the key to be looked up.
        :returns: The value if it exists and is readable, else ``None``.
        """
        return None

    def delete(self, key):
        """Delete `key` from the cache.

        :param key: the key to delete.
        :returns: Whether the key existed and has been deleted.
        :rtype: boolean
        """
        return True

    def get_many(self, *keys):
        """Returns a list of values for the given keys.
        For each key an item in the list is created::

            foo, bar = cache.get_many("foo", "bar")

        Has the same error handling as :meth:`get`.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        """
        return [self.get(k) for k in keys]

    def get_dict(self, *keys):
        """Like :meth:`get_many` but return a dict::

            d = cache.get_dict("foo", "bar")
            foo = d["foo"]
            bar = d["bar"]

        :param keys: The function accepts multiple keys as positional
                     arguments.
        """
        return dict(zip(keys, self.get_many(*keys)))

    def set(self, key, value, timeout=None):
        """Add a new key/value to the cache (overwrites value, if key already
        exists in the cache).

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: ``True`` if key has been updated, ``False`` for backend
                  errors. Pickling errors, however, will raise a subclass of
                  ``pickle.PickleError``.
        :rtype: boolean
        """
        return True

    def add(self, key, value, timeout=None):
        """Works like :meth:`set` but does not overwrite the values of already
        existing keys.

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: Same as :meth:`set`, but also ``False`` for already
                  existing keys.
        :rtype: boolean
        """
        return True

    def set_many(self, mapping, timeout=None):
        """Sets multiple keys and values from a mapping.

        :param mapping: a mapping with the keys/values to set.
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: Whether all given keys have been set.
        :rtype: boolean
        """
        rv = True
        for key, value in mapping.items():
            if not self.set(key, value, timeout):
                rv = False
        return rv

    def delete_many(self, *keys):
        """Deletes multiple keys at once.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        :returns: Whether all given keys have been deleted.
        :rtype: boolean
        """
        return all(self.delete(key) for key in keys)

    def has(self, key):
        """Checks if a key exists in the cache without returning it. This is a
        cheap operation that bypasses loading the actual data on the backend.

        This method is optional and may not be implemented on all caches.

        :param key: the key to check
        """
        raise NotImplementedError(
            "%s doesn't have an efficient implementation of `has`. That "
            "means it is impossible to check whether a key exists without "
            "fully loading the key's data. Consider using `self.get` "
            "explicitly if you don't care about performance."
        )

    def clear(self):
        """Clears the cache.  Keep in mind that not all caches support
        completely clearing the cache.

        :returns: Whether the cache has been cleared.
        :rtype: boolean
        """
        return True

    def inc(self, key, delta=1):
        """Increments the value of a key by `delta`.  If the key does
        not yet exist it is initialized with `delta`.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to add.
        :returns: The new value or ``None`` for backend errors.
        """
        value = (self.get(key) or 0) + delta
        return value if self.set(key, value) else None

    def dec(self, key, delta=1):
        """Decrements the value of a key by `delta`.  If the key does
        not yet exist it is initialized with `-delta`.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to subtract.
        :returns: The new value or `None` for backend errors.
        """
        value = (self.get(key) or 0) - delta
        return value if self.set(key, value) else None


class NullCache(BaseCache):

    """A cache that doesn't cache.  This can be useful for unit testing.

    :param default_timeout: a dummy parameter that is ignored but exists
                            for API compatibility with other caches.
    """

    def has(self, key):
        return False
