Quickstart
==========

Eager to get started? This page gives a good introduction to CacheLib.
Follow :doc:`installation` to set up a project and install CacheLib first.


A Minimal Example
-----------------

A minimal example of using :class:`.SimpleCache` from CacheLib
looks like this:

.. code-block:: python

    from cachelib import SimpleCache

    # Create a cache instance
    cache = SimpleCache()

    # Set a value in the cache
    cache.set('my_key', 'my_value')

    # Retrieve the value from the cache
    value = cache.get('my_key')
    print(value)  # Output: my_value

    # Delete the value from the cache
    cache.delete('my_key')

    # Try to retrieve the deleted value
    value = cache.get('my_key')
    print(value)  # Output: None

The code above does the following:

1. Import the :class:`.SimpleCache` class from the ``cachelib`` module.
2. Create a cache instance using ``cache = SimpleCache()``.
3. Set a value in the cache with the key ``'my_key'`` and the value
   ``'my_value'`` using the :meth:`.SimpleCache.set` method.
4. Retrieve the value from the cache using the
   :meth:`.SimpleCache.get` method.
5. Print the retrieved value, which outputs ``my_value``.
6. Delete the value from the cache using the
   :meth:`.SimpleCache.delete` method.
7. Retrieve the deleted value again, which returns ``None`` since it has
   been removed from the cache.

This example uses the :class:`.SimpleCache` backend. CacheLib
supports multiple backends, such as :class:`.RedisCache`,
:class:`.MemcachedCache`, and more. Each backend is used
the same way by creating an instance of the desired cache class.


To run the application, use ``python quickstart.py``.
The output shows the retrieved value and ``None`` for the deleted key.

.. code-block:: console

    $ python quickstart.py
    my_value
    None
