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
---------------------

These distributions will not be installed automatically. CacheLib will
detect and use them if you install them.

-   `redis-py <https://redis-py.readthedocs.io/>`_ for
    :class:`.RedisCache`.
-   `pylibmc <https://sendapatch.se/projects/pylibmc/>`_ or
    `python-memcached <https://github.com/linuxfoundation/python-memcached>`_
    for :class:`.MemcachedCache`.
-   `boto3 <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>`_
    for :class:`.DynamoDbCache`.
-   `pymongo <https://pymongo.readthedocs.io/>`_ for
    :class:`.MongoDbCache`.

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

Create an environment
~~~~~~~~~~~~~~~~~~~~~

Create a project folder and a ``.venv`` folder within:

.. code-block:: text

    # macOS/Linux
    $ mkdir myproject
    $ cd myproject
    $ python3 -m venv .venv

    # Windows
    > mkdir myproject
    > cd myproject
    > py -3 -m venv .venv

Activate the environment
~~~~~~~~~~~~~~~~~~~~~~~~

Before you work on your project, activate the corresponding environment:

.. code-block:: text

    # macOS/Linux
    $ . .venv/bin/activate

    # Windows
    > .venv\Scripts\activate

Your shell prompt will change to show the name of the activated
environment.

Install CacheLib
----------------

Within the activated environment, use the following command to install
CacheLib:

.. code-block:: text

    $ pip install cachelib

CacheLib is now installed. Check out the :doc:`quickstart` to get
started.
