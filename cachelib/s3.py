# -*- coding: utf-8 -*-
try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle

from cachelib.base import BaseCache, _items
from cachelib._compat import string_types, integer_types


class S3Cache(BaseCache):
    """Uses an S3 bucket as a cache backend.

    Note: Cache keys must meet S3 criteria for a valid object name (a sequence
    of Unicode characters whose UTF-8 encoding is at most 1024 bytes long).

    Note: Cache item timeout is not currently supported. (It could be
    implemented efficiently with S3 GetObject's IfModifiedSince.)

    :param bucket: Required. Name of the bucket to use. It must already exist.
    :param key_prefix: A prefix that should be added to all keys.

    Any additional keyword arguments will be passed to ``boto3.client``.
    """

    def __init__(self, bucket, key_prefix=None, **kwargs):
        BaseCache.__init__(self, default_timeout=0)
        if not isinstance(bucket, string_types):
            raise ValueError("S3Cache bucket parameter must be a string")
        try:
            import boto3
            import botocore.exceptions
        except ImportError:
            raise RuntimeError("no boto3 module found")
        self._client = boto3.client("s3")
        self.bucket = bucket
        self.key_prefix = key_prefix or ""

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
            return self.load_object(resp["Body"].read())
        except botocore.exceptions.ClientError:
            return None

    def set(self, key, value):
        full_key = self.key_prefix + key
        dump = self.dump_object(value)
        self._client.put_object(Bucket=self.bucket, Key=full_key, body=dump)
        return True

    def add(self, key, value):
        full_key = self.key_prefix + key
        if self._has(full_key):
            return False
        else:
            return self.set(full_key, value)

    def delete(self, key):
        full_key = self.key_prefix + key
        try:
            self._client.delete_object(Bucket=self.bucket, Key=full_key)
        except botocore.exceptions.ClientError:
            return False
        else:
            return True

    def has(self, key):
        full_key = self.key_prefix + key
        return self._has(full_key)

    def clear(self):
        paginator = self._client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=self.bucket, Prefix=self.key_prefix
        )
        # Delete in batches of 1000 which is much faster than individual deletes
        to_delete = []
        for page in response_iterator:
            for item in page["Contents"]:
                key = item["Key"]
                to_delete.append(key)
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

    def _has(self, key):
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
        except botocore.exceptions.ClientError:
            return False
        else:
            return True
