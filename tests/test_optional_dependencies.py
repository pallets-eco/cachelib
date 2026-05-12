from importlib import metadata as importlib_metadata

BACKEND_EXTRAS = {
    "dynamodb": {"boto3"},
    "memcached": {"pylibmc"},
    "mongodb": {"pymongo"},
    "redis": {"redis"},
    "uwsgi": {"uwsgi"},
    "valkey": {"valkey"},
}


def is_for_extra(requirement, extra):
    return f"extra == '{extra}'" in requirement or f'extra == "{extra}"' in requirement


def test_backend_extras_are_advertised():
    metadata = importlib_metadata.metadata("cachelib")
    extras = set(metadata.get_all("Provides-Extra") or [])

    assert BACKEND_EXTRAS.keys() <= extras


def test_backend_extras_install_expected_dependencies():
    requirements = importlib_metadata.requires("cachelib") or []

    for extra, expected_names in BACKEND_EXTRAS.items():
        extra_requirements = [
            requirement
            for requirement in requirements
            if is_for_extra(requirement, extra)
        ]

        for expected_name in expected_names:
            assert any(
                requirement.lower().startswith(expected_name)
                for requirement in extra_requirements
            )
