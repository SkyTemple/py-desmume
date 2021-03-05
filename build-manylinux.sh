#!/usr/bin/env bash
set -x
set -e

rm __build_desmume -rf || true
rm build -rf || true

yum install zlib-devel libpcap-devel SDL2-devel agg-devel soundtouch-devel openal-soft-devel glib2-devel libtool autoconf automake meson -y

# Fun! The pkgconfig version of CentOS 6 is way too old!
(
  curl https://parakoopa.de/pkg-config-0.29.2.tar.gz -s -o /tmp/pkg-config.tar.gz
  cd /tmp/
  tar -zxvf /tmp/pkg-config.tar.gz
  cd /tmp/pkg-config-0.29.2
  ./configure --prefix=/usr/local        \
              --with-internal-glib       \
              --disable-host-tool
  make
  make install
)
# End fun!

# Posix C-Source required for some time constants.
export CXXFLAGS="-DFORCE_AVX512_0=1 -D_POSIX_C_SOURCE=199309L"
export CFLAGS="-D_POSIX_C_SOURCE=199309L"
export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
