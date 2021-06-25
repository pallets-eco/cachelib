Version 0.2.0
-------------

Unreleased

-   Support for Python 2 has been dropped. Only Python 3.6 and above are
    supported.
-   Fix ``FileSystemCache.set`` incorrectly considering value overrides
    on existing keys as new cache entries.
-   ``SimpleCache`` and ``FileSystemCache`` first remove expired
    entries, followed by older entries, when cleaning up.
-   Fix problem where file count was not being updated in
    ``FileSystemCache.get`` and ``FileSystemCache.has`` after removals.
    :issue:`20`
-   When attempting to access non-existent entries with ``Memcached``,
    these will now be initialized with a given value ``delta``.


Version 0.1.1
-------------

Released 2020-06-20

-   Fix ``FileSystemCache`` on Windows.
