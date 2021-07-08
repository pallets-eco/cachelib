import errno
import logging
import os
import pickle
import tempfile
from hashlib import md5
from time import time

from cachelib.base import BaseCache


class FileSystemCache(BaseCache):

    """A cache that stores the items on the file system.  This cache depends
    on being the only user of the `cache_dir`.  Make absolutely sure that
    nobody but this cache stores files there or otherwise the cache will
    randomly delete files therein.

    :param cache_dir: the directory where cache files are stored.
    :param threshold: the maximum number of items the cache stores before
                      it starts deleting some. A threshold value of 0
                      indicates no threshold.
    :param default_timeout: the default timeout that is used if no timeout is
                            specified on :meth:`~BaseCache.set`. A timeout of
                            0 indicates that the cache never expires.
    :param mode: the file mode wanted for the cache files, default 0600
    """

    #: used for temporary files by the FileSystemCache
    _fs_transaction_suffix = ".__wz_cache"
    #: keep amount of files in a cache element
    _fs_count_file = "__wz_cache_count"

    def __init__(self, cache_dir, threshold=500, default_timeout=300, mode=0o600):
        BaseCache.__init__(self, default_timeout)
        self._path = cache_dir
        self._threshold = threshold
        self._mode = mode

        try:
            os.makedirs(self._path)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

        # If there are many files and a zero threshold,
        # the list_dir can slow initialisation massively
        if self._threshold != 0:
            self._update_count(value=len(self._list_dir()))

    @property
    def _file_count(self):
        return self.get(self._fs_count_file) or 0

    def _update_count(self, delta=None, value=None):
        # If we have no threshold, don't count files
        if self._threshold == 0:
            return

        if delta:
            new_count = self._file_count + delta
        else:
            new_count = value or 0
        self.set(self._fs_count_file, new_count, mgmt_element=True)

    def _normalize_timeout(self, timeout):
        timeout = BaseCache._normalize_timeout(self, timeout)
        if timeout != 0:
            timeout = time() + timeout
        return int(timeout)

    def _list_dir(self):
        """return a list of (fully qualified) cache filenames"""
        mgmt_files = [
            self._get_filename(name).split(os.sep)[-1]
            for name in (self._fs_count_file,)
        ]
        return [
            os.path.join(self._path, fn)
            for fn in os.listdir(self._path)
            if not fn.endswith(self._fs_transaction_suffix) and fn not in mgmt_files
        ]

    def _over_threshold(self):
        return self._threshold != 0 and self._file_count > self._threshold

    def _remove_expired(self, now):
        entries = self._list_dir()
        for fname in entries:
            try:
                with open(fname, "rb") as f:
                    expires = pickle.load(f)
                if expires != 0 and expires < now:
                    os.remove(fname)
                    self._update_count(delta=-1)
            except (OSError, EOFError):
                logging.warning(
                    "Exception raised while handling cache file '%s'",
                    fname,
                    exc_info=True,
                )

    def _remove_older(self):
        entries = self._list_dir()
        exp_fname_tuples = []
        for fname in entries:
            try:
                with open(fname, "rb") as f:
                    exp_fname_tuples.append((pickle.load(f), fname))
            except (OSError, EOFError):
                logging.warning(
                    "Exception raised while handling cache file '%s'",
                    fname,
                    exc_info=True,
                )
        fname_sorted = (
            fname for _, fname in sorted(exp_fname_tuples, key=lambda item: item[1][0])
        )
        for fname in fname_sorted:
            try:
                os.remove(fname)
                self._update_count(delta=-1)
            except OSError:
                logging.warning(
                    "Exception raised while handling cache file '%s'",
                    fname,
                    exc_info=True,
                )
                return False
            if not self._over_threshold():
                break

    def _prune(self):
        if self._over_threshold():
            now = time()
            self._remove_expired(now)
        # if still over threshold
        if self._over_threshold():
            self._remove_older()

    def clear(self):
        for fname in self._list_dir():
            try:
                os.remove(fname)
            except OSError:
                logging.warning(
                    "Exception raised while handling cache file '%s'",
                    fname,
                    exc_info=True,
                )
                self._update_count(value=len(self._list_dir()))
                return False
        self._update_count(value=0)
        return True

    def _get_filename(self, key):
        if isinstance(key, str):
            key = key.encode("utf-8")  # XXX unicode review
        hash = md5(key).hexdigest()
        return os.path.join(self._path, hash)

    def get(self, key):
        filename = self._get_filename(key)
        try:
            with open(filename, "rb") as f:
                pickle_time = pickle.load(f)
                if pickle_time == 0 or pickle_time >= time():
                    return pickle.load(f)
                else:
                    os.remove(filename)
                    self._update_count(delta=-1)
                    return None
        except (OSError, EOFError, pickle.PickleError):
            logging.warning(
                "Exception raised while handling cache file '%s'",
                filename,
                exc_info=True,
            )
            return None

    def add(self, key, value, timeout=None):
        filename = self._get_filename(key)
        if not os.path.exists(filename):
            return self.set(key, value, timeout)
        return False

    def set(self, key, value, timeout=None, mgmt_element=False):
        # Management elements have no timeout
        if mgmt_element:
            timeout = 0
        # Don't prune on management element update, to avoid loop
        else:
            self._prune()

        timeout = self._normalize_timeout(timeout)
        filename = self._get_filename(key)
        overwrite = os.path.isfile(filename)

        try:
            fd, tmp = tempfile.mkstemp(
                suffix=self._fs_transaction_suffix, dir=self._path
            )
            with os.fdopen(fd, "wb") as f:
                pickle.dump(timeout, f, 1)
                pickle.dump(value, f, pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, filename)
            os.chmod(filename, self._mode)
        except OSError:
            logging.warning(
                "Exception raised while handling cache file '%s'",
                filename,
                exc_info=True,
            )
            return False
        else:
            # Management elements should not count towards threshold
            if not overwrite and not mgmt_element:
                self._update_count(delta=1)
            return True

    def delete(self, key, mgmt_element=False):
        try:
            os.remove(self._get_filename(key))
        except OSError:
            logging.warning("Exception raised while handling cache file", exc_info=True)
            return False
        else:
            # Management elements should not count towards threshold
            if not mgmt_element:
                self._update_count(delta=-1)
            return True

    def has(self, key):
        filename = self._get_filename(key)
        try:
            with open(filename, "rb") as f:
                pickle_time = pickle.load(f)
                if pickle_time == 0 or pickle_time >= time():
                    return True
                else:
                    os.remove(filename)
                    self._update_count(delta=-1)
                    return False
        except (OSError, EOFError, pickle.PickleError):
            logging.warning(
                "Exception raised while handling cache file '%s'",
                filename,
                exc_info=True,
            )
            return False
