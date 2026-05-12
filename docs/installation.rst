Installation
============


Python Version
--------------

We recommend using the latest version of Python. CacheLib supports
Python 3.8 and newer.


Dependencies
------------

There are no required dependencies beyond Python itself. CacheLib is a
standalone library that works out of the box.


Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~

When you install CacheLib :class:`.SimpleCache` and :class:`.FileSystemCache`
will work without any additional dependencies.
However, some backends require additional dependencies to be installed.

CacheLib will detect and use them if they are already installed but if not,
you can use pip extras to install them as needed:

.. tabs::

   .. group-tab:: Redis

      Installs `redis-py`_ required for :class:`.RedisCache`.

      .. code-block:: sh

         $ pip install cachelib[redis]

   .. group-tab:: Memcached

      Installs `pylibmc`_ required for :class:`.MemcachedCache`.

      .. code-block:: sh

         $ pip install cachelib[memcached]

   .. group-tab:: DynamoDB

      Installs `boto3`_ required for :class:`.DynamoDbCache`.

      .. code-block:: sh

         $ pip install cachelib[dynamodb]

   .. group-tab:: MongoDB

      Installs `pymongo`_ required for :class:`.MongoDbCache`.

      .. code-block:: sh

         $ pip install cachelib[mongodb]

   .. group-tab:: Valkey

      Installs `valkey-py`_ required for :class:`.ValkeyCache`.

      .. code-block:: sh

         $ pip install cachelib[valkey]

   .. group-tab:: uWSGI

      Installs `uWSGI`_ required for :class:`.UWSGICache`.

      .. code-block:: sh

         $ pip install cachelib[uwsgi]

.. _redis-py: https://redis.readthedocs.io/en/stable/
.. _pylibmc: https://sendapatch.se/projects/pylibmc/
.. _boto3: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
.. _pymongo: https://pymongo.readthedocs.io/
.. _valkey-py: https://valkey-py.readthedocs.io/en/latest/
.. _uWSGI: https://uwsgi-docs.readthedocs.io/en/latest/


Virtual Environments
--------------------

Use a virtual environment to manage the dependencies for your project,
both in development and in production.

What problem does a virtual environment solve? The more Python projects
you have, the more likely it is that you need to work with different
versions of Python libraries, or even Python itself. Newer versions of
libraries for one project can break compatibility in another project.

Virtual environments are independent groups of Python libraries, one for
each project. Packages installed for one project will not affect other
projects or the operating system's packages.

Python comes bundled with the :mod:`venv` module to create virtual
environments.


.. _install-create-env:

Create an environment
~~~~~~~~~~~~~~~~~~~~~

Create a project folder and a :file:`.venv` folder within:

.. tabs::

   .. group-tab:: macOS/Linux

      .. code-block:: text

         $ mkdir myproject
         $ cd myproject
         $ python3 -m venv .venv

   .. group-tab:: Windows

      .. code-block:: text

         > mkdir myproject
         > cd myproject
         > py -3 -m venv .venv


.. _install-activate-env:

Activate the environment
~~~~~~~~~~~~~~~~~~~~~~~~

Before you work on your project, activate the corresponding environment:

.. tabs::

   .. group-tab:: macOS/Linux

      .. code-block:: text

         $ . .venv/bin/activate

   .. group-tab:: Windows

      .. code-block:: text

         > .venv\Scripts\activate

Your shell prompt will change to show the name of the activated
environment.


Install CacheLib
----------------

Within the activated environment, use the following command to install
CacheLib:

.. code-block:: sh

    $ pip install cachelib

CacheLib is now installed. Check out the :doc:`quickstart` to get
started.
