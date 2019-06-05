import boto3
from moto import mock_s3
from cachelib import S3Cache
import pytest

BUCKET = "mybucket"
KEY = "mykey"


@mock_s3
@pytest.mark.parametrize("test_input", ["foo", "", b"foo", b""])
def test_cache_get_string(test_input):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=test_input)

    cache = S3Cache(BUCKET)
    assert cache.get(KEY) == s3.get_object(Bucket=BUCKET, Key=KEY)["Body"].read()


@mock_s3
@pytest.mark.parametrize("test_input", [0, 1, 1_000_000_000_000_000])
def test_cache_get_num(test_input):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=str(test_input))

    cache = S3Cache(BUCKET)
    assert cache.get(KEY) == int(s3.get_object(Bucket=BUCKET, Key=KEY)["Body"].read())


@mock_s3
@pytest.mark.parametrize(
    "test_input", ["foo", "", b"foo", b"", 0, 1, ["foo", "bar"], {"foo": "bar"}]
)
def test_cache_roundtrip(test_input):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)

    cache = S3Cache(BUCKET)
    cache.set(KEY, test_input)
    assert test_input == cache.get(KEY)


@mock_s3
@pytest.mark.parametrize("prefix", ["foo/", "foo"])
def test_cache_key_prefix(prefix):
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)

    cache = S3Cache(BUCKET, key_prefix=prefix)
    cache.set(KEY, "contents")
    assert s3.head_object(Bucket=BUCKET, Key=prefix + KEY)


@mock_s3
def test_cache_has():
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body="foo")

    cache = S3Cache(BUCKET)
    assert cache.has(KEY)


@mock_s3
def test_cache_delete():
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body="foo")

    cache = S3Cache(BUCKET)
    assert cache.has(KEY)
    cache.delete(KEY)
    assert not cache.has(KEY)


@mock_s3
def test_cache_clear():
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body="foo")

    cache = S3Cache(BUCKET)
    assert cache.has(KEY)
    cache.clear()
    assert not cache.has(KEY)


@mock_s3
def test_cache_timeout():
    import time

    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET)

    cache = S3Cache(BUCKET, default_timeout=1)
    cache.set(KEY, "foo")
    assert cache.has(KEY)
    time.sleep(1)
    assert not cache.has(KEY)
