import base64
import logging
import pickle
import typing as _t
from collections import abc as cabc

import itsdangerous


class _Base85Pickler:
    """Pickle, then Base85 encode, so the output is safe to store on a single
    line. itsdangerous separates values with newlines when reading from a
    stream, so the encoded payload must not contain any. Base85 also has less
    overhead than Base64.
    """

    @staticmethod
    def dumps(obj: _t.Any) -> bytes:
        return base64.b85encode(pickle.dumps(obj))

    @staticmethod
    def loads(data: bytes) -> _t.Any:
        return pickle.loads(base64.b85decode(data))


class BaseSerializer:
    """This is the base interface for all default serializers.

    BaseSerializer.load and BaseSerializer.dump will
    default to pickle.load and pickle.dump. This is currently
    used only by FileSystemCache which dumps/loads to/from a file stream.

    :param secret_key: when provided, cache entries are signed with this key
        using ``itsdangerous`` and verified on load. Tampered or unsigned
        entries are rejected.
    """

    def __init__(
        self,
        secret_key: _t.Optional[
            _t.Union[str, bytes, cabc.Iterable[str], cabc.Iterable[bytes]]
        ] = None,
    ) -> None:
        if secret_key is not None:
            self._signer: _t.Optional[itsdangerous.Serializer[bytes]] = (
                itsdangerous.Serializer(secret_key, serializer=_Base85Pickler)
            )
        else:
            self._signer = None

    def _warn(self, e: pickle.PickleError) -> None:
        logging.warning(
            f"An exception has been raised during a pickling operation: {e}"
        )

    def dump(
        self, value: int, f: _t.IO[bytes], protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> None:
        if self._signer is not None:
            f.write(self._signer.dumps(value) + b"\n")
            return
        try:
            pickle.dump(value, f, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            self._warn(e)

    def load(self, f: _t.BinaryIO) -> _t.Any:
        if self._signer is not None:
            try:
                return self._signer.loads(f.readline().rstrip(b"\n"))
            except (itsdangerous.BadSignature, pickle.UnpicklingError):
                return None
        try:
            data = pickle.load(f)
        except pickle.PickleError as e:
            self._warn(e)
            return None
        else:
            return data

    """BaseSerializer.loads and BaseSerializer.dumps
    work on top of pickle.loads and pickle.dumps. Dumping/loading
    strings and byte strings is the default for most cache types.
    """

    def dumps(
        self, value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> _t.Optional[bytes]:
        if self._signer is not None:
            return self._signer.dumps(value)
        try:
            serialized = pickle.dumps(value, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            self._warn(e)
            return None
        return serialized

    def loads(self, bvalue: bytes) -> _t.Any:
        if self._signer is not None:
            if bvalue is None:
                return None
            try:
                return self._signer.loads(bvalue)
            except (itsdangerous.BadSignature, pickle.UnpicklingError):
                return None
        try:
            data = pickle.loads(bvalue)
        except pickle.PickleError as e:
            self._warn(e)
            return None
        else:
            return data


class BaseRedisSerializer(BaseSerializer):
    """Base serializer for Redis compatible caches."""

    def dumps(self, value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL) -> bytes:
        """Dumps an object into a string for redis, using pickle by default."""
        if self._signer is not None:
            return self._signer.dumps(value)
        return b"!" + pickle.dumps(value, protocol)

    def loads(self, value: _t.Optional[bytes]) -> _t.Any:
        """The reversal of :meth:`dump_object`. This might be called with
        None.
        """
        if value is None:
            return None
        if self._signer is not None:
            try:
                return self._signer.loads(value)
            except (itsdangerous.BadSignature, pickle.UnpicklingError):
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


"""Default serializers for each cache type.

The following classes can be used to further customize
serialiation behaviour. Alternatively, any serializer can be
overridden in order to use a custom serializer with a different
strategy altogether.
"""


class UWSGISerializer(BaseSerializer):
    """Default serializer for UWSGICache."""


class SimpleSerializer(BaseSerializer):
    """Default serializer for SimpleCache."""


class FileSystemSerializer(BaseSerializer):
    """Default serializer for FileSystemCache."""


class RedisSerializer(BaseRedisSerializer):
    """Default serializer for RedisCache."""

    pass


class ValkeySerializer(BaseRedisSerializer):
    """Default serializer for ValkeyCache."""

    pass


class DynamoDbSerializer(RedisSerializer):
    """Default serializer for DynamoDbCache."""

    def loads(self, value: _t.Any) -> _t.Any:
        """The reversal of :meth:`dump_object`. This might be called with
        None.
        """
        value = value.value
        return super().loads(value)
