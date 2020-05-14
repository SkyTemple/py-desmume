py-desmume
==========

|build| |pypi-version| |pypi-downloads| |pypi-license| |pypi-pyversions|

.. |build| image:: https://jenkins.riptide.parakoopa.de/buildStatus/icon?job=py-desmume%2Fmaster
    :target: https://jenkins.riptide.parakoopa.de/blue/organizations/jenkins/py-desmume/activity
    :alt: Build Status

.. |pypi-version| image:: https://img.shields.io/pypi/v/py-desmume
    :target: https://pypi.org/project/py-desmume/
    :alt: Version

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/py-desmume
    :target: https://pypi.org/project/py-desmume/
    :alt: Downloads

.. |pypi-license| image:: https://img.shields.io/pypi/l/py-desmume
    :alt: License (GPLv3)

.. |pypi-pyversions| image:: https://img.shields.io/pypi/pyversions/py-desmume
    :alt: Supported Python versions

A Python library for DeSmuME, the Nintendo DS library.

- Library to interface with a `DeSmuME fork`_ that has a binary interface.
- Reimplementation of the Glade GTK interface in GTK3.

Running the setup.py (eg. via pip) compiles the library from the fork. Wheels are available
for Linux and Windows.

There's no API documentation at the moment, but you can find the entire libary in
``desmume.emulator``.

.. _DeSmuME fork: https://github.com/SkyTemple/desmume/tree/binary-interface
