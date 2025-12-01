py-desmume
==========

|build| |docs| |pypi-version| |pypi-downloads| |pypi-license| |pypi-pyversions|

.. |build| image:: https://img.shields.io/github/actions/workflow/status/SkyTemple/py-desmume/build-test-publish.yml
    :target: https://pypi.org/project/skytemple-ssb-emulator/
    :alt: Build Status

.. |docs| image:: https://readthedocs.org/projects/py-desmume/badge/?version=latest
    :target: https://py-desmume.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

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

- Library to interface with DeSmuME's "interface" frontend.
- Reimplementation of the DeSmuME Glade-GTK UI with GTK3.

Running the setup.py (eg. via pip) compiles the library from the fork. Wheels are available
for Linux, Windows and MacOS.

Documentation can be found in the ``docs`` directory and at
https://py-desmume.readthedocs.org.

Build Requirements
------------------

**For using pre-built wheels (recommended):**

Simply install via pip - all dependencies are included.

**For building from source:**

Linux:

- SDL2 >= 2.0.14 (for full game controller support including touchpad features)
- Other dependencies: zlib, libpcap, soundtouch, openal-soft, glib2, meson

macOS:

- Install via Homebrew: ``brew install sdl2 meson glib gcc``

Windows:

- Visual Studio 2019 or later
- SDL2 is included in the repository
