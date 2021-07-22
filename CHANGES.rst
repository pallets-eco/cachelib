Version 0.3.0
-------------

Unreleased

-   Optimize ``FileSystemCache`` prunning functionality
-   Fix bug in ``FileSystemCache`` where entries would not be removed
    when total count was over threshold and entry count would be lost
-   ``FileSystemCache`` will now log system-related exceptions
-   Removal of expired entries in ``FileSystemCache`` will only be
    triggered if the total number of entries is over the defined
    ``threshhold`` when attempting to ``FileSystemCache.set``.
    ``FileSystemCache.get`` and ``FileSystemCache.has`` will still
    return ``None`` and ``False`` (respectively) for expired entries
    but they will not remove the entry files. All removals will now
    be conducted at prunning time or explicitly with ``clear`` and
    ``delete``.


Version 0.2.0
-------------

Released 2021-06-25

-   Support for Python 2 has been dropped. Only Python 3.6 and above are
    supported.
-   Fix ``FileSystemCache.set`` incorrectly considering value overrides
    on existing keys as new cache entries. :issue:`18`
-   ``SimpleCache`` and ``FileSystemCache`` first remove expired
    entries, followed by older entries, when cleaning up. :pr:`26`
-   Fix problem where file count was not being updated in
    ``FileSystemCache.get`` and ``FileSystemCache.has`` after removals.
    :issue:`20`
-   When attempting to access non-existent entries with ``Memcached``,
    these will now be initialized with a given value ``delta``.
    :pr:`31`


Version 0.1.1
-------------

Released 2020-06-20

-   Fix ``FileSystemCache`` on Windows.
