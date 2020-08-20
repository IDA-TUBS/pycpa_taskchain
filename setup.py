#!/usr/bin/env python

from setuptools import setup

setup(
    name='pycpa_taskchain',
    version='1.0',
    description='pyCPA task-chain analysis extension',
    author='Johannes Schlatow',
    author_email='schlatow@ida.ing.tu-bs.de',
    url='https://bitbucket.org/pycpa/pycpa_taskchain',
    license='MIT',
    packages= ['taskchain'],
    install_requires=['pycpa', 'networkx']
)
