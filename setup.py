#  Copyright 2020 Marco Köpcke (Parakoopa)
#
#  This file is part of py-desmume.
#
#  py-desmume is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  py-desmume is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with py-desmume.  If not, see <https://www.gnu.org/licenses/>.
__version__ = '0.0.5.post0'
from setuptools import setup, find_packages

from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install

import os
import platform
import shutil
import subprocess
import sys
from distutils.dist import Distribution
from glob import glob

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in

is_installed_develop = False


class BinaryDistribution(Distribution):
    def is_pure(self):
        return False

    def has_ext_modules(self):
        return True


# Bug in distutils; see https://github.com/google/or-tools/issues/616#issuecomment-371480314
class InstallPlatlib(install):
    def finalize_options(self):
        install.finalize_options(self)
        if self.distribution.has_ext_modules():
            self.install_lib = self.install_platlib


class Develop(develop):
    def run(self):
        global is_installed_develop
        is_installed_develop = True
        super().run()


class BuildExt(build_ext):
    """Compiles the shared object using automake or the DLL using Visual Studio, depending on platform."""
    def run(self):
        # Don't build in develop mode
        if is_installed_develop:
            return

        this_path = os.getcwd()
        path_repo = os.path.join(this_path, 'desmume_src')
        path_interface = os.path.join(path_repo, 'desmume', 'src', 'frontend', 'interface')

        is_windows = platform.system() == "Windows"

        # Run the build script depending on the platform
        if is_windows:
            libraries = self.build_windows(path_interface)
        else:
            libraries = self.build_unix(path_interface)
        if not libraries:
            print("Could not compile the DeSmuME library.")
            print("")
            sys.exit(1)
        os.chdir(this_path)

        # Copy the libraries to the correct place
        for library in libraries:
            build_target = os.path.join(
                self.build_lib, 'desmume',
                os.path.basename(library)
            )
            print(f"Copying {library} -> {build_target}")
            shutil.copyfile(library, build_target)

    def build_unix(self, interface_path):
        """Tested against manylinux2014, see Jenkinsfile for requirements."""
        os.chdir(interface_path)
        environ = os.environ.copy()

        if platform.system() == "Darwin":
            environ["CC"] = "clang"
            environ["CXX"] = "clang++"

        print(f"BUILDING UNIX - meson build")
        retcode = subprocess.call(["meson", "build", "--buildtype=release"], env=environ)
        if retcode:
            return False
        print(f"BUILDING UNIX - ninja")
        retcode = subprocess.call(["ninja", "-C", "build"], env=environ)
        if retcode:
            return False

        if platform.system() == "Darwin":
            return [os.path.abspath(os.path.join(interface_path, 'build', 'libdesmume.dylib'))]
        else:
            return [os.path.abspath(os.path.join(interface_path, 'build', 'libdesmume.so'))]

    def build_windows(self, interface_path):
        """Requires Visual Studio."""
        is_64bits = sys.maxsize > 2 ** 32
        if os.getenv('BUILD_32', False):
            is_64bits = False
        arch_dirname = 'x64' if is_64bits else 'x86'
        arch_targetname = 'x64' if is_64bits else 'Win32'

        win_path = os.path.join(interface_path, "windows")
        os.chdir(win_path)
        print(f"BUILDING WINDOWS - msbuild.exe")
        config = "Release"
        if os.environ.get('FASTBUILD', False):
            config = "Release Fastbuild"
        retcode = subprocess.call(["MSBuild.exe", "DeSmuME_Interface.vcxproj", f"/p:configuration={config}", f"/p:Platform={arch_targetname}"])
        if retcode:
            return False

        # Find and rename DeSmuME DLL file
        path_dll = glob(os.path.join(win_path, '__bins', '*.dll'))[0]
        new_name_dll = os.path.join(os.path.dirname(path_dll), 'libdesmume.dll')
        os.rename(path_dll, new_name_dll)

        return [
            os.path.abspath(new_name_dll),
            # Also include the required SDL lib
            os.path.abspath(os.path.join(win_path, 'SDL', 'lib', arch_dirname, 'SDL2.dll'))
        ]

setup(
    name='py-desmume',
    version=__version__,
    packages=find_packages(),
    package_data={'desmume': ['**/*.css', '**/*.glade', '**/control_ui/*.glade', 'libdesmume.so', 'libdesmume.dylib', '*.dll']},
    description='Python library to interface with DeSmuME, the Nintendo DS emulator + sample GTK-based frontend',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/SkyTemple/py-desmume/',
    install_requires=[
        'Pillow >= 6.1.0'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    distclass=BinaryDistribution,
    cmdclass={'build_ext': BuildExt, 'install': InstallPlatlib, 'develop': Develop}
)
