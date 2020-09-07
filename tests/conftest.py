from time import sleep


class CommonTests:
    def cache_factory(self, *args, **kwargs):
        raise NotImplementedError()

    sample_numbers = [0, 10, 1024000, 9, 5000000000000, 99, 738, 2000000]

    sample_pairs = {
        128: False,
        "beef": True,
        "crevettes": {},
        1024: "spam",
        "bacon": "eggs",
        "sausage": 2048,
        3072: [],
        "brandy": [{}, "fried eggs"],
        "lobster": ["baked beans", [512]],
        4096: {"sauce": [], 256: "truffle"},
    }

    def test_set_get(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v, timeout=0)
            assert cache.get(k) == v

    def test_set_get_many(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs, timeout=0)
        values = cache.get_many(*self.sample_pairs)
        assert values == list(self.sample_pairs.values())

    def test_get_dict(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs, timeout=0)
        d = cache.get_dict(*self.sample_pairs)
        assert d == self.sample_pairs

    def test_delete(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v, timeout=0)
            assert cache.delete(k)
            assert not cache.get(k)

    def test_delete_many(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs, timeout=0)
        assert cache.delete_many(*self.sample_pairs)
        assert not any(cache.get_many(*self.sample_pairs))

    def test_add(self):
        cache = self.cache_factory()
        cache.set_many(self.sample_pairs, timeout=0)
        for k in self.sample_pairs:
            cache.add(k, "updated", timeout=0)
        assert cache.get_many(*self.sample_pairs) == list(self.sample_pairs.values())
        for k, v in self.sample_pairs.items():
            cache.add(f"{k}-new", v, timeout=0)
            assert cache.get(f"{k}-new") == v

    def test_inc_dec(self):
        cache = self.cache_factory()
        for n in self.sample_numbers:
            assert cache.inc(f"{n}-key-inc", n) == n
            assert cache.get(f"{n}-key-inc") == n
            assert cache.dec(f"{n}-key-dec", n) == -n
            assert cache.get(f"{n}-key-dec") == -n
            assert cache.dec(f"{n}-key-inc", 5) == n - 5

    def test_expiration(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(f"{k}-t0", v, timeout=0)
            cache.set(f"{k}-t0.1", v, timeout=0.1)
            cache.set(f"{k}-t5.0", v, timeout=5.0)
        sleep(1)
        for k, v in self.sample_pairs.items():
            assert cache.get(f"{k}-t0") == v
            assert cache.get(f"{k}-t5.0") == v
            assert not cache.get(f"{k}-t0.1")
