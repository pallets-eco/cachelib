Caching with Redis
==================

This tutorial walks you through using :class:`.RedisCache` from CacheLib
against a Redis server, from an empty project to a cache that stores values,
expires them, and counts things. Every step builds on the previous one, so
follow them in order.

What you will build
-------------------

A small Python module that talks to Redis through CacheLib and does the four
things a cache is actually used for: store a value, expire it, take a lock, and
count hits. No web framework is needed.


Before you start
----------------

You need:

- Python 3.9 or newer.
- A Redis server reachable from your machine. The default address is
  ``localhost:6379``.
- CacheLib installed in a virtual environment.

Create the environment and install CacheLib:

.. code-block:: console

   $ python -m venv .venv
   $ source .venv/bin/activate
   $ pip install cachelib

On Windows, activate with ``.venv\Scripts\activate`` instead.

If you do not have a Redis server running, the examples still work with
`fakeredis <https://pypi.org/project/fakeredis/>`_, which implements the same
client interface. Install it and pass an instance instead of a host name; the
outputs shown below were produced that way.


Step 1: Connect to Redis
------------------------

Create a file called ``cache_demo.py`` and open a connection:

.. code-block:: python

   from cachelib import RedisCache

   cache = RedisCache(host="localhost", port=6379, db=0)

The constructor takes the address of the server. The first argument can also be
an object that behaves like ``redis.Redis``, which is what the ``fakeredis``
note above uses:

.. code-block:: python

   import fakeredis
   from cachelib import RedisCache

   cache = RedisCache(fakeredis.FakeRedis())

Nothing is sent to the server yet. ``RedisCache`` opens connections lazily, so
the constructor does not fail if the server is down. Pass
``check_connection=True`` if you want the failure to happen immediately
instead of on the first read or write.


Step 2: Store and read a value
------------------------------

.. code-block:: python

   cache.set("user:42:name", "Ada")
   print(cache.get("user:42:name"))
   print(cache.get("user:404:name"))

.. code-block:: console

   Ada
   None

:meth:`.RedisCache.set` stores any value that the serializer can handle, which
includes strings, numbers, lists and dictionaries. :meth:`.RedisCache.get`
returns ``None`` for a key that is not there, so a missing key and a key holding
``None`` look the same from the caller's side. Use :meth:`.RedisCache.has` when
that distinction matters.

Values are serialized before they are stored, so what lands in Redis is not
readable text. That is expected: the cache is not a database, and other
applications should not read these keys directly.


Step 3: Expire a key
--------------------

A cache without expiry fills up and serves stale data forever. Pass
``timeout`` in seconds:

.. code-block:: python

   cache.set("session:abc", "token-value", timeout=60)
   print(cache.get("session:abc"))

   cache.set("config:forever", "value", timeout=0)
   print(cache.get("config:forever"))

.. code-block:: console

   token-value
   value

``timeout=0`` means "never expire". The constructor also accepts
``default_timeout``, which applies to every ``set`` that does not pass one;
the default is 300 seconds.

The timeout can be a :class:`datetime.timedelta` as well, which is easier to
read when the value is long:

.. code-block:: python

   import datetime as dt

   cache.set("report:daily", "ready", timeout=dt.timedelta(hours=6))


Step 4: Add only if the key is missing
--------------------------------------

:meth:`.RedisCache.set` overwrites. :meth:`.RedisCache.add` does not, and
returns whether it actually wrote:

.. code-block:: python

   print(cache.add("lock:report", "worker-1", timeout=30))
   print(cache.add("lock:report", "worker-2", timeout=30))
   print(cache.get("lock:report"))

.. code-block:: console

   True
   False
   worker-1

That makes ``add`` the simplest way to take a short-lived lock between workers:
the first caller wins and the others are told they lost. It is not a
replacement for a real lock, because the value expires rather than being
released by the holder, but it is enough to stop two cron jobs from running the
same report at the same minute.


Step 5: Count with inc and dec
------------------------------

.. code-block:: python

   cache.set("page:hits", 0)
   print(cache.inc("page:hits"))
   print(cache.inc("page:hits", 5))
   print(cache.dec("page:hits", 2))
   print(cache.get("page:hits"))

.. code-block:: console

   1
   6
   4
   4

:meth:`.RedisCache.inc` and :meth:`.RedisCache.dec` change the stored number in
place and return the new value, so two workers incrementing at the same time do
not lose an update the way a read-then-write would.

Both return ``None`` if the key holds something that is not a number.


Step 6: Work with several keys at once
--------------------------------------

.. code-block:: python

   cache.set_many({"a": 1, "b": 2, "c": 3})
   print(cache.get_many("a", "b", "missing"))
   print(cache.get_dict("a", "c"))
   print(cache.has("a"), cache.has("missing"))
   print(cache.delete("a"), cache.delete("a"))
   print(cache.delete_many("b", "c"))

.. code-block:: console

   [1, 2, None]
   {'a': 1, 'c': 3}
   True False
   True False
   ['b', 'c']

:meth:`.RedisCache.get_many` returns a list in the order the keys were asked
for, with ``None`` in the holes. :meth:`.RedisCache.get_dict` drops the missing
keys instead, which is usually what you want when rendering a page.

:meth:`.RedisCache.delete` returns whether the key was there.
:meth:`.RedisCache.delete_many` returns the list of keys it actually removed.


Step 7: Clear the cache
-----------------------

.. code-block:: python

   cache.set("k", "v", timeout=300)
   print(cache.clear())
   print(cache.get("k"))

.. code-block:: console

   True
   None

:meth:`.RedisCache.clear` removes every key this cache instance owns. Keys are
namespaced with ``key_prefix``, so two applications can share one Redis
database without clearing each other:

.. code-block:: python

   reports = RedisCache(host="localhost", key_prefix="reports:")
   sessions = RedisCache(host="localhost", key_prefix="sessions:")

   reports.clear()  # leaves the session keys alone


Where to go next
----------------

- :doc:`../quickstart` shows the same API on the in-memory backends, which is
  useful when you want the same code in tests and in production.
- :doc:`../api/redis` lists every :class:`.RedisCache` method with its exact
  signature.
- The other backends, such as :class:`.MemcachedCache` and
  :class:`.FileSystemCache`, are used the same way: build an instance, then call
  the same methods.
