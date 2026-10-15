## Process this file with automake to produce Makefile.in

ACLOCAL_AMFLAGS = -I m4

SUBDIRS = po-defs po-defs-fixed po-defs-fixed/fixed data libqalculate src man po docs tests

EXTRA_DIST = config.rpath  \
	autogen.sh \
	README.translate \
	libqalculate.pc.in \
	windows/test-source-dist.py \
	windows/build-qasm-import.ps1 \
	windows/qasm-import-requirements.txt \
	windows/qasm-import.py \
	windows/test-qasm-import.py \
	windows/test-qasm-protocol.py \
	windows/build-native.sh

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libqalculate.pc

if HAVE_DOXYGEN

.PHONY: docs
docs:
	$(MAKE) -C $(top_srcdir)/docs/reference docs

endif
