import io
import pickle

import pytest

from cachelib.serializers import BaseRedisSerializer
from cachelib.serializers import BaseSerializer
from cachelib.serializers import JSONSerializer
from cachelib.serializers import RedisSerializer
from cachelib.serializers import ValkeySerializer

PICKLE_VALUES = [
    None,
    True,
    False,
    0,
    42,
    -1,
    3.14,
    "",
    "hello",
    b"raw bytes",
    [],
    [1, 2, 3],
    (1, 2),
    {},
    {"a": 1, "b": [True, None]},
]

JSON_VALUES = [v for v in PICKLE_VALUES if not isinstance(v, (bytes, tuple))]


class _Unpicklable:
    """Helper that always raises PicklingError"""

    def __reduce__(self):
        raise pickle.PicklingError("cannot pickle")


class TestBaseSerializer:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.s = BaseSerializer()

    @pytest.mark.parametrize("value", PICKLE_VALUES)
    def test_dumps_loads_roundtrip(self, value):
        assert self.s.loads(self.s.dumps(value)) == value

    @pytest.mark.parametrize("value", PICKLE_VALUES)
    def test_dump_load_roundtrip(self, value):
        buf = io.BytesIO()
        self.s.dump(value, buf)
        buf.seek(0)
        assert self.s.load(buf) == value

    def test_dumps_returns_none_on_pickle_error(self):
        assert self.s.dumps(_Unpicklable()) is None

    def test_loads_returns_none_on_corrupt_data(self):
        assert self.s.loads(b"not valid pickle data") is None

    def test_load_returns_none_on_corrupt_stream(self):
        assert self.s.load(io.BytesIO(b"not valid pickle data")) is None


class TestBaseRedisSerializer:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.s = BaseRedisSerializer()

    @pytest.mark.parametrize("value", PICKLE_VALUES)
    def test_dumps_loads_roundtrip(self, value):
        assert self.s.loads(self.s.dumps(value)) == value

    def test_dumps_adds_bang_prefix(self):
        assert self.s.dumps("hello").startswith(b"!")

    def test_loads_none_returns_none(self):
        assert self.s.loads(None) is None

    @pytest.mark.parametrize("n", [0, 1, 42, -5])
    def test_loads_integer_string_returns_int(self, n):
        # Redis stores counters as plain integers without prefix
        assert self.s.loads(str(n).encode()) == n

    def test_loads_legacy_bytes_returns_raw(self):
        # Before 0.8, values were stored without the "!" prefix
        raw = b"legacy data without prefix"
        assert self.s.loads(raw) == raw

    def test_loads_corrupt_prefixed_data_returns_none(self):
        assert self.s.loads(b"!" + b"corrupt pickle") is None


@pytest.mark.parametrize("cls", [RedisSerializer, ValkeySerializer])
class TestRedisCompatibleSerializers:
    @pytest.mark.parametrize("value", PICKLE_VALUES)
    def test_roundtrip(self, cls, value):
        s = cls()
        assert s.loads(s.dumps(value)) == value


class TestJSONSerializer:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.s = JSONSerializer()

    @pytest.mark.parametrize("value", JSON_VALUES)
    def test_dumps_loads_roundtrip(self, value):
        assert self.s.loads(self.s.dumps(value)) == value

    @pytest.mark.parametrize("value", JSON_VALUES)
    def test_dump_load_roundtrip(self, value):
        buf = io.BytesIO()
        self.s.dump(value, buf)
        buf.seek(0)
        assert self.s.load(buf) == value

    def test_dumps_returns_bytes(self):
        assert isinstance(self.s.dumps({"key": "value"}), bytes)

    def test_dump_writes_bytes_to_stream(self):
        buf = io.BytesIO()
        self.s.dump({"key": "value"}, buf)
        assert isinstance(buf.getvalue(), bytes)
        assert buf.getvalue()

    @pytest.mark.parametrize("value", [b"raw bytes", _Unpicklable()])
    def test_dumps_non_serializable_returns_none(self, value):
        assert self.s.dumps(value) is None

    @pytest.mark.parametrize(
        "raw",
        [b'"hello"', '"hello"', bytearray(b'"hello"')],
        ids=["bytes", "str", "bytearray"],
    )
    def test_loads_accepts_bytes_str_bytearray(self, raw):
        assert self.s.loads(raw) == "hello"

    def test_loads_invalid_json_returns_none(self):
        assert self.s.loads(b"not valid json {{{{") is None

    def test_load_invalid_stream_returns_none(self):
        assert self.s.load(io.BytesIO(b"not valid json {{{{")) is None
