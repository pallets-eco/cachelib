Version 0.4.1
-------------

Released 2021-10-04

-   Fix break in ``RedisCache`` when a host object was passed
    in ``RedisCache.host`` instead of a string. :pr:`82`


Version 0.4.0
-------------

Released 2021-10-03

-   All cache types now implement ``BaseCache`` interface both
    in behavior and method return types. Thus, code written
    for one cache type should work with any other cache type. :pr:`71`
-   Add type information for static typing tools. :pr:`48`
-   ``FileNotFound`` exceptions will not be logged anymore
    in ``FileSystemCache`` methods in order to avoid polluting
    application log files. :pr:`69`


Version 0.3.0
-------------

Released 2021-08-12

-   Optimize ``FileSystemCache`` pruning. :pr:`52`
-   Fix a bug in ``FileSystemCache`` where entries would not be removed
    when the total was over the threshold, and the entry count would be
    lost. :pr:`52`
-   ``FileSystemCache`` logs system-related exceptions. :pr:`51`
-   Removal of expired entries in ``FileSystemCache`` is only triggered
    if the number of entries is over the ``threshhold`` when calling
    ``set``. ``get`` ``has`` still return ``None`` and ``False``
    respectively for expired entries, but will not remove the files. All
    removals happen at pruning time or explicitly with ``clear`` and
    ``delete``. :pr:`53`


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
