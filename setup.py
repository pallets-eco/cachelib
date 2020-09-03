#!/usr/bin/env python
import re

from setuptools import setup

with open("cachelib/__init__.py", encoding="utf8") as f:
    version = re.search(r"__version__ = \'(.*?)\'", f.read()).group(1)

# Metadata in setup.cfg
setup(name="cachelib", version=version)
