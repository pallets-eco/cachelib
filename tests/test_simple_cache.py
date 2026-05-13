import threading
from time import sleep

import pytest
from clear import ClearTests
from common import CommonTests
from has import HasTests

from cachelib import SimpleCache
from cachelib import ThreadedSimpleCache


class SillySerializer:
    """A pointless serializer only for testing"""

    def dumps(self, value):
        return repr(value).encode()

    def loads(self, bvalue):
        return eval(bvalue.decode())


class CustomCache(SimpleCache):
    """Our custom cache client with non-default serializer"""

    # overwrite serializer
    serializer = SillySerializer()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.fixture(params=[SimpleCache, CustomCache])
def cache_factory(request):
    def _factory(self, *args, **kwargs):
        return request.param(*args, **kwargs)

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("cache_factory")
class TestSimpleCache(CommonTests, HasTests, ClearTests):
    def test_threshold(self):
        threshold = len(self.sample_pairs) // 2
        cache = self.cache_factory(threshold=threshold)
        assert cache.set_many(self.sample_pairs)
        assert abs(len(cache._cache) - threshold) <= 1

    def test_prune_old_entries(self):
        threshold = 2 * len(self.sample_pairs) - 1
        cache = self.cache_factory(threshold=threshold)
        for k, v in self.sample_pairs.items():
            assert cache.set(f"{k}-t0.1", v, timeout=0.1)
            assert cache.set(f"{k}-t5.0", v, timeout=5.0)
        sleep(2)
        for k, v in self.sample_pairs.items():
            assert cache.set(k, v)
            assert f"{k}-t5.0" in cache._cache.keys()
            assert f"{k}-t0.1" not in cache._cache.keys()

    def test_threshold_zero_defaults_to_500(self):
        """SimpleCache(threshold=0) should silently use 500, not 0."""
        cache = self.cache_factory(threshold=0)
        assert cache._threshold == 500

    def test_add_on_expired_key_succeeds(self):
        """add() on a key whose TTL has elapsed should succeed."""
        cache = self.cache_factory()
        cache.set("key", "original", timeout=0.1)
        sleep(0.5)
        assert cache.add("key", "new") is True
        assert cache.get("key") == "new"

    def test_has_on_expired_key_returns_false(self):
        cache = self.cache_factory()
        cache.set("key", "value", timeout=0.1)
        sleep(0.5)
        assert cache.has("key") is False

    def test_delete_nonexistent_returns_false(self):
        cache = self.cache_factory()
        assert cache.delete("does_not_exist") is False


@pytest.fixture(params=[ThreadedSimpleCache])
def threaded_cache_factory(request):
    def _factory(self, *args, **kwargs):
        return request.param(*args, **kwargs)

    request.cls.cache_factory = _factory


@pytest.mark.usefixtures("threaded_cache_factory")
class TestThreadedSimpleCache(CommonTests, HasTests, ClearTests):
    """Run the full common test suite against ThreadedSimpleCache."""

    def test_concurrent_set_no_data_corruption(self):
        """Multiple threads writing distinct keys must all succeed."""
        cache = self.cache_factory()
        errors = []

        def writer(thread_id: int) -> None:
            for i in range(50):
                key = f"thread-{thread_id}-key-{i}"
                try:
                    cache.set(key, thread_id * 1000 + i)
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Exceptions raised during concurrent set: {errors}"

    def test_concurrent_inc_is_consistent(self):
        """Concurrent increments on a single key must not lose updates.

        A small sleep is injected into ``serializer.dumps`` to widen the
        read-modify-write window inside ``inc``. Without the cache's lock,
        threads would interleave between ``get`` and ``set`` and lose
        updates, making this test reliably fail on a non-thread-safe
        backend.
        """
        cache = self.cache_factory()

        class _SlowSerializer:
            def __init__(self, inner):
                self._inner = inner

            def dumps(self, value):
                sleep(0.0001)
                return self._inner.dumps(value)

            def loads(self, bvalue):
                return self._inner.loads(bvalue)

        cache.serializer = _SlowSerializer(type(cache).serializer)
        cache.set("counter", 0)
        num_threads = 20
        increments_each = 50
        barrier = threading.Barrier(num_threads)

        def incrementer() -> None:
            barrier.wait()
            for _ in range(increments_each):
                cache.inc("counter", 1)

        threads = [threading.Thread(target=incrementer) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cache.get("counter") == num_threads * increments_each

    def test_concurrent_add_only_one_winner(self):
        """Only one thread must win the race on add() for a fresh key."""
        cache = self.cache_factory()
        results = []
        lock = threading.Lock()

        def adder() -> None:
            result = cache.add("race-key", 1)
            with lock:
                results.append(result)

        threads = [threading.Thread(target=adder) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        winners = [r for r in results if r is True]
        assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}"

    def test_concurrent_get_set_no_exception(self):
        """Simultaneous reads and writes must not raise exceptions."""
        cache = self.cache_factory()
        cache.set("shared", "initial")
        errors = []

        def reader() -> None:
            for _ in range(100):
                try:
                    cache.get("shared")
                except Exception as exc:
                    errors.append(exc)

        def writer() -> None:
            for i in range(100):
                try:
                    cache.set("shared", i)
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        threads += [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Exceptions during concurrent get/set: {errors}"

    def test_is_subclass_of_simple_cache(self):
        """ThreadedSimpleCache must be a drop-in subclass of SimpleCache."""
        cache = self.cache_factory()
        assert isinstance(cache, ThreadedSimpleCache)
        assert isinstance(cache, SimpleCache)
