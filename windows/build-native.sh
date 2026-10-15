#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/ucrt64/bin:$PATH"
export ACLOCAL_PATH="/ucrt64/share/aclocal${ACLOCAL_PATH:+:$ACLOCAL_PATH}"
# Run in MSYS2 with the UCRT64 GCC, GMP, MPFR, libxml2 and pkgconf packages,
# plus autoconf, automake, libtool, gettext-devel and make.
# QUANTUM_PYTHON may select a Python executable when python3 is not on PATH.
python="${QUANTUM_PYTHON:-python3}"
"$python" -c 'import sys; assert sys.version_info >= (3, 8)'
printf -v python_command '%q' "$python"
autoreconf -fi
./configure --host=x86_64-w64-mingw32 --disable-shared --enable-static \
  --without-libcurl --without-icu --disable-nls
make -j2 LIBS="-lmpfr -lgmp -lpthread -lbcrypt"
# Native Windows processes need a Windows path, including when launched by Python.
export QALCULATE_DEFINITIONS_DIR="$(cygpath -m "$PWD/data")"
make check LIBS="-lmpfr -lgmp -lpthread -lbcrypt" \
  PY_LOG_COMPILER="$python_command" TESTS_ENVIRONMENT=
mkdir -p dist/QuantumStudio
cp src/quantum-worker.exe src/qalc.exe dist/QuantumStudio/
printf '%s\n' 'Native build and tests passed; executables staged for packaging.'
