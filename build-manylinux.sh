#!/usr/bin/env bash
set -x
set -e

rm __build_desmume -rf || true
rm build -rf || true

yum install zlib-devel libpcap-devel SDL2-devel agg-devel soundtouch-devel openal-soft-devel glib2-devel libtool autoconf automake meson -y

# Fun! The pkgconfig version of CentOS 6 is way too old!
cat << 'EOF' > /usr/lib64/pkgconfig/libpcap.pc
prefix="/usr"
exec_prefix="${prefix}"
includedir="${prefix}/include"
libdir="${exec_prefix}/lib"

Name: libpcap
Description: Platform-independent network traffic capture library
Version: 1.53.3
Libs: -L${libdir}  -lpcap
Cflags: -I${includedir}
EOF
# End fun!

# Posix C-Source required for some time constants.
export CXXFLAGS="-DFORCE_AVX512_0=1 -D_POSIX_C_SOURCE=199309L"
export CFLAGS="-D_POSIX_C_SOURCE=199309L"
export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
