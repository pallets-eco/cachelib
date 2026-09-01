import datetime as dt
import typing as _t

from cachelib.redis_base import BaseRedisCache
from cachelib.serializers import RedisSerializer


class RedisCache(BaseRedisCache):
    """Uses the Redis key-value store as a cache backend.

    The first argument can be either a string denoting address of the Redis
    server or an object resembling an instance of a redis.Redis class.

    Note: Python Redis API already takes care of encoding unicode strings on
    the fly.

    :param host: address of the Redis server or an object which API is
        compatible with the official Python Redis client (``redis-py``).
    :param port: port number on which Redis server listens for connections.
    :param password: password authentication for the Redis server.
    :param db: db (zero-based numeric index) on Redis Server to connect.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~.BaseCache.set`. Either a number of seconds or a
        :class:`datetime.timedelta`. A timeout of
        0 indicates that the cache never expires.

        .. versionchanged:: 0.17.0
            Accepts a :class:`datetime.timedelta`.
    :param key_prefix: A prefix that should be added to all keys.
    :param ignore_delete_many_errors: If False, delete_many() will raise
        a RuntimeError if any key fails to delete. Keys that do not
        exist are considered successfully deleted and do not raise.

        .. versionadded:: 0.16.0

    :param check_connection: If True, the constructor will verify the
        connection to the Redis server and raise a RuntimeError if it fails.
        If False (default), connection errors are ignored at construction
        and surface on first use.

        .. versionadded:: 0.16.1

    Any additional keyword arguments will be passed to ``redis.Redis``.
    """

    serializer = RedisSerializer()

    def __init__(
        self,
        host: _t.Any = "localhost",
        port: int = 6379,
        password: str | None = None,
        db: int = 0,
        default_timeout: int | dt.timedelta = 300,
        key_prefix: str | _t.Callable[[], str] | None = None,
        ignore_delete_many_errors: bool = True,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ):
        if host is None:
            raise ValueError("RedisCache host parameter may not be None")
        if isinstance(host, str):
            try:
                import redis
            except ImportError as err:
                raise RuntimeError("no redis module found") from err
            if kwargs.get("decode_responses", None):
                raise ValueError("decode_responses is not supported by RedisCache.")
            client = redis.Redis(
                host=host, port=port, password=password, db=db, **kwargs
            )
        else:
            client = host
        if check_connection:
            try:
                client.ping()
            except Exception as err:
                raise RuntimeError(f"could not connect to Redis server: {err}") from err
        super().__init__(
            client,
            default_timeout,
            key_prefix,
            ignore_delete_many_errors=ignore_delete_many_errors,
            check_connection=check_connection,
        )


class RedisSentinelCache(BaseRedisCache):
    """Uses the Redis key-value store as a cache backend, via Redis Sentinel.

    The first argument can be either a list or a tuple of sentinel addresses
    used to construct a ``redis.sentinel.Sentinel``, or an object resembling
    an already instantiated ``redis.sentinel.Sentinel``.

    Note: Python Redis API already takes care of encoding unicode strings on
    the fly.


    :param sentinels: A list or a tuple of Redis sentinel addresses,
        e.g. ``[("sentinel-host", 26379)]``, or an object
        which API is compatible with
        ``redis.sentinel.Sentinel``. Required.
    :param master: The name of the master server in a sentinel configuration.
    :param password: password authentication for the Redis server.
    :param db: db (zero-based numeric index) on Redis Server to connect.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~BaseCache.set`. A timeout of
        0 indicates that the cache never expires.
    :param key_prefix: A prefix that should be added to all keys.
    :param ignore_delete_many_errors: If set to ``False`` the ``delete_many``
        method raises a ``RuntimeError`` in case
        a key couldn't be deleted.
        Defaults to ``False``.
    :param check_connection: If True, the constructor will verify the
        connection to the Redis server and raise a
        RuntimeError if it fails.

    Any additional keyword arguments will be passed to
    ``redis.sentinel.Sentinel``.
    """

    serializer = RedisSerializer()

    def __init__(
        self,
        sentinels: _t.Any,
        master: str = "mymaster",
        password: str | None = None,
        db: int = 0,
        default_timeout: int = 300,
        key_prefix: str = "",
        ignore_delete_many_errors: bool = False,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ) -> None:
        if not sentinels:
            raise ValueError("sentinels is required, e.g. [('sentinel-host', 26379)]")
        if isinstance(sentinels, (list, tuple)):
            try:
                import redis.sentinel
            except ImportError as e:
                raise RuntimeError("no redis module found") from e
            if kwargs.get("decode_responses", None):
                raise ValueError(
                    "decode_responses is not supported by RedisSentinelCache."
                )
            sentinel_kwargs = {
                key[9:]: value
                for key, value in kwargs.items()
                if key.startswith("sentinel_")
            }
            kwargs = {
                key: value
                for key, value in kwargs.items()
                if not key.startswith("sentinel_")
            }
            sentinel = redis.sentinel.Sentinel(
                sentinels=sentinels,
                password=password,
                db=db,
                sentinel_kwargs=sentinel_kwargs,
                **kwargs,
            )
        else:
            sentinel = sentinels
        write_client = sentinel.master_for(master)
        read_client = sentinel.slave_for(master)
        if check_connection:
            try:
                write_client.ping()
                read_client.ping()
            except Exception as err:
                raise RuntimeError(f"could not connect to Redis server: {err}") from err
        super().__init__(
            write_client,
            default_timeout=default_timeout,
            key_prefix=key_prefix,
            ignore_delete_many_errors=ignore_delete_many_errors,
            check_connection=check_connection,
        )
        # must stay after super().__init__, which points both clients at write_client
        self._read_client = read_client


class RedisClusterCache(BaseRedisCache):
    """Uses the Redis key-value store as a cache backend.

    The first argument can be either a string denoting address of the Redis
    server or an object resembling an instance of a rediscluster.RedisCluster
    class.

    Note: Python Redis API already takes care of encoding unicode strings on
    the fly.


    :param cluster: The redis cluster nodes address separated by comma.
        e.g. host1:port1,host2:port2,host3:port3 .
    :param redis_url: A Redis URL to connect to the cluster,
        e.g. ``redis://host:port``.

    One of ``cluster`` or ``redis_url`` is required. If both are
    supplied, ``redis_url`` wins and ``cluster`` is ignored.

    :param password: password authentication for the Redis server.
    :param default_timeout: the default timeout that is used if no timeout is
        specified on :meth:`~BaseCache.set`. A timeout of
        0 indicates that the cache never expires.
    :param key_prefix: A prefix that should be added to all keys.
    :param ignore_delete_many_errors: If set to ``False`` the ``delete_many``
        method raises a ``RuntimeError`` in case
        a key couldn't be deleted.
        Defaults to ``False``.
    :param check_connection: If True, the constructor will verify the
        connection to the Redis server and raise a
        RuntimeError if it fails.

    Any additional keyword arguments will be passed to
    ``rediscluster.RedisCluster``.
    """

    serializer = RedisSerializer()

    def __init__(
        self,
        cluster: _t.Any = "",
        redis_url: str | None = None,
        password: str = "",
        default_timeout: int = 300,
        key_prefix: str = "",
        ignore_delete_many_errors: bool = False,
        check_connection: bool = False,
        **kwargs: _t.Any,
    ) -> None:
        if not cluster and not redis_url:
            raise ValueError(
                "cluster is required, e.g. 'host1:port1,host2:port2,host3:port3'"
            )
        if isinstance(cluster, str) or redis_url:
            try:
                from redis import RedisCluster
                from redis.cluster import ClusterNode
            except ImportError as e:
                raise RuntimeError("no redis.cluster module found") from e
            if kwargs.get("decode_responses", None):
                raise ValueError(
                    "decode_responses is not supported by RedisClusterCache."
                )
            # Use URL-based connection if provided, otherwise use startup nodes.
            if redis_url:
                client = RedisCluster.from_url(redis_url, **kwargs)
            else:
                try:
                    nodes = [(node.split(":")) for node in cluster.split(",")]
                    startup_nodes = [
                        ClusterNode(node[0].strip(), int(node[1].strip()))
                        for node in nodes
                    ]
                except IndexError as e:
                    raise ValueError(
                        "Please give the correct cluster argument "
                        "e.g. host1:port1,host2:port2,host3:port3"
                    ) from e

                # Skips the check of cluster-require-full-coverage config,
                # useful for clusters without the CONFIG command (like aws)
                skip_full_coverage_check = kwargs.pop("skip_full_coverage_check", True)

                client = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=password,
                    skip_full_coverage_check=skip_full_coverage_check,
                    **kwargs,
                )
        else:
            client = cluster
        if check_connection:
            try:
                client.ping()
            except Exception as err:
                raise RuntimeError(f"could not connect to Redis server: {err}") from err
        super().__init__(
            client,
            default_timeout=default_timeout,
            key_prefix=key_prefix,
            ignore_delete_many_errors=ignore_delete_many_errors,
            check_connection=check_connection,
        )
