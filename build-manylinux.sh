#!/usr/bin/env bash
set -x
set -e

rm __build_desmume -rf || true
rm build -rf || true

# Install base dependencies (except SDL2, which we'll build from source)
yum install zlib-devel libpcap-devel soundtouch-devel openal-soft-devel glib2-devel libtool autoconf automake meson wget -y

# Build SDL2 2.0.22 from source (requires SDL >= 2.0.14 for touchpad APIs)
# See: https://github.com/TASEmulators/desmume/issues/935
SDL2_VERSION="2.0.22"
cd /tmp
wget https://www.libsdl.org/release/SDL2-${SDL2_VERSION}.tar.gz
tar -xzf SDL2-${SDL2_VERSION}.tar.gz
cd SDL2-${SDL2_VERSION}
./configure --prefix=/usr/local
make -j$(nproc)
make install
cd /
rm -rf /tmp/SDL2-${SDL2_VERSION}*

# Ensure pkg-config can find SDL2
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
