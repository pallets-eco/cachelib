Version 0.2.0
------------

Unreleased

-   fix :meth:`cachelib.FileSystemCache.set` wrongfuly considering value overrides on
    existing keys as new cache entries

-   :class:`cachelib.Simplecache` and :class:`cachelib.FileSystemCache` will
    now first remove expired entries, followed by removal of older entries when
    cleaning up.

-   Fix problem where file count was not being updated in :meth:`FileSystemCache.get`
    and :meth:`FileSystemCache.has` after removals (:meth:`os.remove`) in
    :class:`FileSystemCache`. ``Issue #20``

-   When attempting to access non-existent entries with :class:`Memcached`,
    these will now be initialized with a given value ``delta`` as specified
    in :class:`BaseCache`

-   Support for python 2 has been dropped. The supported releases are now
    python 3.6 and above.


Version 0.1.1
------------

Released 2020-06-20

-   Fix FileSystemCache on Windows
