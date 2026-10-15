#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/ucrt64/bin:$PATH"
export ACLOCAL_PATH="/ucrt64/share/aclocal${ACLOCAL_PATH:+:$ACLOCAL_PATH}"
# MSYS2 UCRT64 packages: gcc gmp mpfr libxml2 pkgconf, plus
# MSYS autoconf automake libtool gettext-devel make.
autoreconf -fi
./configure --host=x86_64-w64-mingw32 --disable-shared --enable-static \
  --without-libcurl --without-icu --disable-nls
make -j2 LIBS="-lmpfr -lgmp -lpthread -lbcrypt"
mkdir -p dist/QuantumStudio
g++ -std=c++17 -O2 -I. src/quantum-worker.cc libqalculate/.libs/libqalculate.a \
  $(pkg-config --cflags --libs libxml-2.0) -lmpfr -lgmp -lpthread -lbcrypt \
  -o dist/QuantumStudio/quantum-worker.exe
make check LIBS="-lmpfr -lgmp -lpthread -lbcrypt"
