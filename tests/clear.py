from conftest import TestData


class ClearTests(TestData):
    """Tests for the optional 'clear' method specified by BaseCache"""

    def test_clear(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache.clear()
        assert not any(cache.get_many(*self.sample_pairs))
