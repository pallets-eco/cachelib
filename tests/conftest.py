from time import sleep


class CommonTests:
    def cache_factory(self, *args, **kwargs):
        raise NotImplementedError()

    sample_numbers = [-50, -25, 25, 50]

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
            cache.set(k, v)
            assert cache.get(k) == v

    def test_get_many(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
        values = cache.get_many(*self.sample_pairs)
        assert values == list(self.sample_pairs.values())

    def test_get_dict(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
        d = cache.get_dict(*self.sample_pairs)
        assert d == self.sample_pairs

    def test_set_many(self):
        cache = self.cache_factory()
        assert cache.set_many(self.sample_pairs)
        assert cache.get_dict(*self.sample_pairs) == self.sample_pairs

    def test_delete(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
            assert cache.delete(k)
        assert not any(cache.get_many(*self.sample_pairs))

    def test_delete_many(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
        assert cache.delete_many(*self.sample_pairs)
        assert not any(cache.get_many(*self.sample_pairs))

    def test_add(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(k, v)
        for idx, k in enumerate(self.sample_pairs.keys()):
            cache.add(k, idx)
        assert cache.get_dict(*self.sample_pairs) == self.sample_pairs

    def test_inc(self):
        cache = self.cache_factory()
        for idx, n in enumerate(self.sample_numbers):
            assert cache.inc(idx, n)
            assert cache.get(idx) == n
            assert cache.inc(idx, 10)
            assert cache.get(idx) == n + 10

    def test_dec(self):
        cache = self.cache_factory()
        for idx, n in enumerate(self.sample_numbers):
            assert cache.dec(idx, n)
            print(idx, n)
            assert cache.get(idx) == -n
            assert cache.dec(idx, 10)
            assert cache.get(idx) == -n - 10

    def test_expiration(self):
        cache = self.cache_factory()
        for k, v in self.sample_pairs.items():
            cache.set(f"{k}-t0", v, timeout=0)
            cache.set(f"{k}-t0.20", v, timeout=0.20)
            cache.set(f"{k}-t0.5", v, timeout=0.5)
        sleep(0.25)
        for k, v in self.sample_pairs.items():
            assert cache.get(f"{k}-t0") == v
            assert not cache.get(f"{k}-t0.20")
            assert cache.get(f"{k}-t0.5") == v
        sleep(0.3)
        for k, v in self.sample_pairs.items():
            assert cache.get(f"{k}-t0") == v
            assert not cache.get(f"{k}-t0.5")
