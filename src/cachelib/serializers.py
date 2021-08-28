import logging
import pickle
import typing as _t


class BaseSerializer:
    """This is the base interface for all default serializers.

    BaseSerializer.load and BaseSerializer.dump
    will default to pickle.loads and pickle.dumps
    as do default serializers for most of the cache types.
    """

    def _warn(self, e: pickle.PickleError) -> None:
        logging.warning(
            f"An exception has been raised during a pickling operation: {e}"
        )

    def dump(
        self, serialized: int, f: _t.IO, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> None:
        try:
            pickle.dump(serialized, f, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            self._warn(e)

    def load(self, f: _t.BinaryIO) -> _t.Any:
        try:
            data = pickle.load(f)
        except pickle.PickleError as e:
            self._warn(e)
            return None
        else:
            return data

    """BaseSerializer.loads and BaseSerializer.dumps
    work on top of pickle.loads and pickle.dumps. For now,
    these two methods are only used in FileSystemCache.
    """

    def dumps(
        self, value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> _t.Optional[bytes]:
        try:
            serialized = pickle.dumps(value, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            self._warn(e)
            return None
        else:
            return serialized

    def loads(self, bvalue: bytes) -> _t.Any:
        try:
            data = pickle.loads(bvalue)
        except pickle.PickleError as e:
            self._warn(e)
            return None
        else:
            return data


class UWSGISerializer(BaseSerializer):
    """Default serializer for UWSGICache.

    This class can be used to further customize the
    behaviour specific to UWSGICache serialization.
    Alternatively, UWSGISerializer.serializer can be
    overriden in order to use a custom serializer with
    a different strategy altogether.
    """


class SimpleSerializer(BaseSerializer):
    """Default serializer for SimpleCache.

    This class can be used to further customize the
    behaviour specific to SimpleCache serialization.
    Alternatively, SimpleSerializer.serializer can be
    overriden in order to use a custom serializer with
    a different strategy altogether.
    """


class FileSystemSerializer(BaseSerializer):
    """Default serializer for FileSystemCache.

    This class can be used to further customize the
    behaviour specific to FileSystemCache serialization.
    Alternatively, FileSystemCache.serializer can be
    overriden in order to use a custom serializer with
    a different strategy altogether.
    """


class RedisSerializer(BaseSerializer):
    """Default serializer for RedisCache.

    This class can be used to further customize the
    behaviour specific to RedisCache serialization.
    Alternatively, RedisCache.serializer can be
    overriden in order to use a custom serializer with
    a different strategy altogether.
    """

    def dumps(self, value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL) -> bytes:
        """Dumps an object into a string for redis. By default it serializes
        integers as regular string and pickle dumps everything else.
        """
        if isinstance(type(value), int):
            return str(value).encode("ascii")
        return b"!" + pickle.dumps(value, protocol)

    def loads(self, value: _t.Optional[bytes]) -> _t.Any:
        """The reversal of :meth:`dump_object`. This might be called with
        None.
        """
        if value is None:
            return None
        if value.startswith(b"!"):
            try:
                return pickle.loads(value[1:])
            except pickle.PickleError:
                return None
        try:
            return int(value)
        except ValueError:
            # before 0.8 we did not have serialization. Still support that.
            return value
