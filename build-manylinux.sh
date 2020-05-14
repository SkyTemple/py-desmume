#!/usr/bin/env bash
set -x
set -e
cd /io

rm /io/__build_desmume -rf || true
rm /io/build -rf || true

yum install zlib-devel libpcap-devel SDL-devel agg-devel soundtouch-devel openal-soft-devel glib2-devel libtool autoconf automake -y

# Fun! The pkgconfig version of CentOS 6 is way too old!
curl https://pkgconfig.freedesktop.org/releases/pkg-config-0.29.2.tar.gz -s -o /tmp/pkg-config.tar.gz
cd /tmp/
tar -zxvf /tmp/pkg-config.tar.gz
cd /tmp/pkg-config-0.29.2
./configure --prefix=/usr/local        \
            --with-internal-glib       \
            --disable-host-tool
make
make install
export PKG_CONFIG_PATH=/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig
# End fun!

# For some reasons AVX512 stage 1 support seems to be broken on the build server
export CXXFLAGS="-DFORCE_AVX512_0=1"

for PYBIN in /opt/python/*/bin; do
    if [[ "$PYBIN" != *"cp27"* ]] && [[ "$PYBIN" != *"cp35"* ]]; then
        "${PYBIN}/pip" install -r /io/dev-requirements.txt
        "${PYBIN}/pip" wheel /io/ --no-deps -w dist/ -vvv
    fi
done
for whl in dist/*.whl; do
    auditwheel repair "$whl" -w /io/dist/
done
mkdir -p /io/dist
cp dist/*.whl /io/dist/

rm /io/__build_desmume -rf
rm /io/build -rf
chmod a+rwX /io/dist -R
