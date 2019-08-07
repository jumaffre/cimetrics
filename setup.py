# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cimetrics",
    version="0.1.2",
    description="Lightweight python module to track crucial metrics",
    url="https://github.com/jumaffre/cimetrics",
    author="Julien Maffre",
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    packages=["cimetrics"],
    python_requires=">=3.3",
    install_requires=[
        "pymongo",
        "pyyaml",
        "gitpython",
        "requests",
        "matplotlib",
        "numpy",
        "black",
    ],
)
