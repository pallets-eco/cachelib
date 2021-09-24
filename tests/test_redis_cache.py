import pickle

import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import RedisCache


@pytest.fixture(autouse=True)
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        rc = RedisCache(*args, port=6360, **kwargs)
        rc._client.flushdb()
        return rc

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("redis_server")
class TestRedisCache(CommonTests, ClearTests, HasTests):
    def test_dump_object(self):
        cache = self.cache_factory()

        expected = {
            4: {
                "128": b"!\x80\x04\x89.",
                "beef": b"!\x80\x04\x88.",
                "crevettes": b"!\x80\x04}\x94.",
                "1024": b"!\x80\x04"
                b"\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04spam\x94.",
                "bacon": b"!\x80\x04"
                b"\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04eggs\x94.",
                "sausage": b"2048",
                "3072": b"!\x80\x04]\x94.",
                "brandy": b"!\x80\x04\x95\x14\x00\x00\x00\x00\x00\x00\x00]"
                b"\x94(}\x94\x8c\nfried eggs\x94e.",
                "lobster": b"!\x80\x04\x95\x19\x00\x00\x00\x00\x00\x00\x00]"
                b"\x94(\x8c\x0bbaked beans\x94]\x94M\x00\x02ae.",
                "4096": b"!\x80\x04\x95\x1c\x00\x00\x00\x00\x00\x00\x00}"
                b"\x94(\x8c\x05sauce\x94]\x94M\x00\x01\x8c\x07truffle\x94u.",
            },
            5: {
                "128": b"!\x80\x05\x89.",
                "beef": b"!\x80\x05\x88.",
                "crevettes": b"!\x80\x05}\x94.",
                "1024": b"!\x80\x05"
                b"\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04spam\x94.",
                "bacon": b"!\x80\x05"
                b"\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04eggs\x94.",
                "sausage": b"2048",
                "3072": b"!\x80\x05]\x94.",
                "brandy": b"!\x80\x05\x95\x14\x00\x00\x00\x00\x00\x00\x00]"
                b"\x94(}\x94\x8c\nfried eggs\x94e.",
                "lobster": b"!\x80\x05\x95\x19\x00\x00\x00\x00\x00\x00\x00]"
                b"\x94(\x8c\x0bbaked beans\x94]\x94M\x00\x02ae.",
                "4096": b"!\x80\x05\x95\x1c\x00\x00\x00\x00\x00\x00\x00}"
                b"\x94(\x8c\x05sauce\x94]\x94M\x00\x01\x8c\x07truffle\x94u.",
            },
        }[pickle.DEFAULT_PROTOCOL]

        for k, v in self.sample_pairs.items():
            dumped = cache.dump_object(v)
            exp = expected.get(k)
            assert dumped == exp
