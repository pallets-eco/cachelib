import queue
import threading

import pytest
from clear import ClearTests
from common import CommonTests
from delete_many_with_prefix import DeleteManyWithPrefixTests
from has import HasTests

from cachelib import MemcachedCache


@pytest.fixture(autouse=True)
def cache_factory(request, key_prefix):
    def _factory(self, *args, **kwargs):
        kwargs.setdefault("servers", ["127.0.0.1:11212"])
        kwargs.setdefault("key_prefix", key_prefix)
        mc = MemcachedCache(*args, **kwargs)
        mc.clear()
        return mc

    request.cls.cache_factory = _factory


@pytest.mark.network
@pytest.mark.usefixtures("memcached_server")
class TestMemcachedCache(CommonTests, ClearTests, HasTests, DeleteManyWithPrefixTests):
    def test_bool_roundtrip(self):
        # memcached client libs flag bool as int on the wire,
        # so bools round-trip as 1/0 instead of True/False
        cache = self.cache_factory()
        assert cache.set("true-key", True)
        value = cache.get("true-key")
        assert value == 1
        assert type(value) is int
        assert cache.set("false-key", False)
        value = cache.get("false-key")
        assert value == 0
        assert type(value) is int

    def test_pool_enforces_capacity_and_blocking_waits_for_release(self):
        cache = self.cache_factory(pool_size=2, pool_blocking=True)

        acquired = [threading.Event(), threading.Event()]
        release = threading.Event()
        held_clients = [None, None]

        def hold_a_slot(index):
            with cache._client_context() as client:
                held_clients[index] = client
                acquired[index].set()
                release.wait(timeout=5)

        holders = [threading.Thread(target=hold_a_slot, args=(i,)) for i in range(2)]
        for holder in holders:
            holder.start()
        for event in acquired:
            # wait until both holders have acquired their slots
            assert event.wait(timeout=5), "holder never acquired its slot"

        # Two reservations are different from each other,
        # not the same client shared.
        assert held_clients[0] is not held_clients[1]

        # pool_size=2 is now fully exhausted, a non-blocking reservation must
        # fail immediately with queue.Empty.
        with pytest.raises(queue.Empty):
            with cache._client.reserve(block=False):
                pass

        # With block=True reservation should wait rather than raise or return
        waiter_acquired = threading.Event()

        def wait_for_a_slot():
            with cache._client_context():
                waiter_acquired.set()

        waiter = threading.Thread(target=wait_for_a_slot)
        waiter.start()

        # check waiter can't acquire a client before it is released.
        assert not waiter_acquired.wait(timeout=0.2), (
            "waiter acquired a client before any slot was released"
        )

        release.set()  # free both held slots
        # wait until the waiter has acquired a slot after the release
        assert waiter_acquired.wait(timeout=5), "waiter never acquired after release"

        for holder in holders:
            holder.join()
        waiter.join()

    def test_non_blocking_pool_raises_when_exhausted(self):
        cache = self.cache_factory(pool_size=1, pool_blocking=False)

        holder_acquired = threading.Event()
        released = threading.Event()

        def hold_the_only_client():
            with cache._client_context():
                holder_acquired.set()
                released.wait(timeout=5)  # keep the single slot busy

        holder = threading.Thread(target=hold_the_only_client)
        holder.start()
        holder_acquired.wait(
            timeout=5
        )  # wait until the holder has acquired the only slot

        try:
            with pytest.raises(queue.Empty):
                with cache._client_context():
                    pass  # 0 free slots left, will raise queue.Empty immediately
        finally:
            released.set()
            holder.join()

        # After the holder releases the only slot, this should work
        with cache._client_context() as client:
            assert client is not None
