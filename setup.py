#!/usr/bin/env python
import re

from setuptools import setup

with open("README.rst", encoding="utf8") as f:
    readme = f.read()

with open("cachelib/__init__.py", encoding="utf8") as f:
    version = re.search(r"__version__ = \'(.*?)\'", f.read()).group(1)


setup(
    name="cachelib",
    version=version,
    url="https://github.com/pallets/cachelib",
    license="BSD",
    author="Pallets team",
    author_email="contact@palletsprojects.com",
    description="A collection of cache libraries in the same API interface.",
    long_description=readme,
    packages=["cachelib"],
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
