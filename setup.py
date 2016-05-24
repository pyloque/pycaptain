# -*- coding: utf-8 -*-
# pylint: disable=all

import os

from setuptools import setup, find_packages

f = open(os.path.join(os.path.dirname(__file__), 'version.txt'))
version = f.read().strip()
f.close()

setup(
    name="pycaptain",
    version=version,
    description="python client for captain[service discovery]",
    author="zhangyue",
    author_email="qianwnepin@zhangyue.com",
    license="MIT",
    packages=find_packages(),
    keywords=['pycaptain captain zhangyue service discovery'])
