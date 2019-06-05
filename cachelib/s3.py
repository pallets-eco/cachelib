# -*- coding: utf-8 -*-
import datetime

try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle

try:
    import boto3
    import botocore.exceptions
except ImportError:  # pragma: no cover
    raise RuntimeError("no boto3 module found")

from cachelib.base import BaseCache
from cachelib._compat import string_types, integer_types


class S3Cache(BaseCache):
    """Uses an S3 bucket as a cache backend.

    Note: Cache keys must meet S3 criteria for a valid object name (a sequence
    of Unicode characters whose UTF-8 encoding is at most 1024 bytes long).

    Note: Expired cache objects are not automatically purged. If
    delete_expired_objects_on_read=True, they will be deleted following an
    attempted read (which reduces performance). Otherwise, you have to delete
    stale objects yourself. Consider an S3 bucket lifecycle rule or other
    out-of-band process.

    :param bucket: Required. Name of the bucket to use. It must already exist.
    :param key_prefix: A prefix that should be added to all keys.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    :param delete_expired_objects_on_read: If True, if a read finds a stale
                                           object, it will be deleted before
                                           a response is returned. Will slow
                                           down responses.

    Any additional keyword arguments will be passed to ``boto3.client``.
    """

    def __init__(
        self,
        bucket,
        key_prefix=None,
        default_timeout=300,
        delete_expired_objects_on_read=True,
        **kwargs
    ):
        BaseCache.__init__(self, default_timeout)
        if not isinstance(bucket, string_types):
            raise ValueError("S3Cache bucket parameter must be a string")
        self._client = boto3.client("s3", **kwargs)
        self.bucket = bucket
        self.key_prefix = key_prefix or ""
        self.default_timeout = default_timeout
        self.delete_expired_objects_on_read = delete_expired_objects_on_read

    def dump_object(self, value):
        """Dumps an object into a string for S3.  By default it serializes
        integers as regular string and pickle dumps everything else.
        """
        t = type(value)
        if t in integer_types:
            return str(value).encode("ascii")
        return b"!" + pickle.dumps(value)

    def load_object(self, value):
        """The reversal of :meth:`dump_object`.  This might be called with
        None.
        """
        if value is None:
            return None
        if value.startswith(b"!"):
            try:
                return pickle.loads(value[1:])
            except pickle.PickleError:
                return None
        try:
            return int(value)
        except ValueError:
            # before 0.8 we did not have serialization.  Still support that.
            return value

    def get(self, key):
        full_key = self.key_prefix + key
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=full_key)
        except botocore.exceptions.ClientError as e:
            code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            if code == 404:
                # Object does not exist
                return None
            # Unhandled
            raise

        if "Expires" in resp and self._now() > resp["Expires"]:
            # Object is stale
            if self.delete_expired_objects_on_read:
                self._delete(full_key)
            return None
        else:
            return self.load_object(resp["Body"].read())

    def get_many(self, *keys):
        return [self.get(key) for key in keys]

    def get_dict(self, *keys):
        return {key: self.get(key) for key in keys}

    def set(self, key, value, timeout=None):
        full_key = self.key_prefix + key
        dump = self.dump_object(value)

        if timeout is None:
            timeout = self.default_timeout
        # Figure out expires header
        if timeout is 0:
            expires = {}
        else:
            expires = {"Expires": self._now() + datetime.timedelta(seconds=timeout)}
        self._client.put_object(Bucket=self.bucket, Key=full_key, Body=dump, **expires)
        return True

    def set_many(self, mapping, timeout=None):
        return all(map(lambda item: self.set(item[0], item[1], timeout), mapping))

    def add(self, key, value, timeout=None):
        full_key = self.key_prefix + key
        if self._has(full_key):
            return False
        else:
            return self.set(full_key, value)

    def delete(self, key):
        full_key = self.key_prefix + key
        return self._delete(full_key)

    def delete_many(self, *keys):
        return self._delete_many(self.key_prefix + key for key in keys)

    def has(self, key):
        full_key = self.key_prefix + key
        return self._has(full_key)

    def clear(self):
        # Delete in batches of 1000 which is much faster than individual deletes
        paginator = self._client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=self.bucket, Prefix=self.key_prefix
        )
        to_delete = []
        for page in response_iterator:
            for item in page["Contents"]:
                to_delete.append(item["Key"])
                if len(to_delete) == 1000:
                    self._delete_many(to_delete)
                    to_delete = []
        # Delete the remainder
        self._delete_many(to_delete)
        return True

    def _delete_many(self, keys):
        self._client.delete_objects(
            Bucket=self.bucket, Delete={"Objects": [{"Key": i} for i in keys]}
        )
        return True

    def _delete(self, key):
        return self._delete_many([key])

    def _has(self, key):
        try:
            resp = self._client.head_object(Bucket=self.bucket, Key=key)
        except botocore.exceptions.ClientError as e:
            code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            if code == 404:
                return False
            # Unhandled
            raise
        if "Expires" in resp and self._now() > resp["Expires"]:
            # Exists but is stale
            if self.delete_expired_objects_on_read:
                self._delete(key)
            return False
        return True

    def _now(self):
        return datetime.datetime.now(datetime.timezone.utc)
