from conftest import TestData


class HasTests(TestData):
    """Tests for the optional 'has' method specified by BaseCache"""

    def test_has(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        for k in self.sample_pairs:
            assert cache.has(k)
        assert not cache.has("unknown")
