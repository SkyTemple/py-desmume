#!/usr/bin/env bash
set -x
set -e

rm __build_desmume -rf || true
rm build -rf || true

yum install zlib-devel libpcap-devel SDL2-devel soundtouch-devel openal-soft-devel glib2-devel libtool autoconf automake meson -y
