import logging
import pickle
import typing as _t
from io import BufferedWriter


class FileSystemSerializer:
    @staticmethod
    def dump(
        timeout: int, f: BufferedWriter, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> None:
        try:
            pickle.dump(timeout, f, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            logging.warning(
                f"An exception has been raised during a pickling operation: {e}"
            )

    @staticmethod
    def load(f: _t.BinaryIO) -> _t.Any:
        try:
            data = pickle.load(f)
        except pickle.PickleError as e:
            logging.warning(
                f"An exception has been raised during an unplicking operation: {e}"
            )
            return None
        else:
            return data


class RedisSerializer:
    @staticmethod
    def dump(value: _t.Any) -> bytes:
        """Dumps an object into a string for redis.  By default it serializes
        integers as regular string and pickle dumps everything else.
        """
        if isinstance(type(value), int):
            return str(value).encode("ascii")
        return b"!" + pickle.dumps(value)

    @staticmethod
    def load(value: _t.Optional[bytes]) -> _t.Any:
        """The reversal of :meth:`dump_object`.  This might be called with
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


class SimpleSerializer:
    @staticmethod
    def dump(
        value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> _t.Optional[bytes]:
        try:
            serialized = pickle.dumps(value, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            logging.warning(
                f"An exception has been raised during a pickling operation: {e}"
            )
            return None
        else:
            return serialized

    @staticmethod
    def load(bvalue: bytes) -> _t.Any:
        try:
            data = pickle.loads(bvalue)
        except pickle.PickleError as e:
            logging.warning(
                f"An exception has been raised during an unplicking operation: {e}"
            )
            return None
        else:
            return data


class UWSGISerializer:
    @staticmethod
    def dump(
        value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> _t.Optional[bytes]:
        try:
            serialized = pickle.dumps(value, protocol)
        except (pickle.PickleError, pickle.PicklingError) as e:
            logging.warning(
                f"An exception has been raised during a pickling operation: {e}"
            )
            return None
        else:
            return serialized

    @staticmethod
    def load(bvalue: bytes) -> _t.Any:
        try:
            data = pickle.loads(bvalue)
        except pickle.PickleError as e:
            logging.warning(
                f"An exception has been raised during an unplicking operation: {e}"
            )
            return None
        else:
            return data
