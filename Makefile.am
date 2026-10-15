## Process this file with automake to produce Makefile.in

ACLOCAL_AMFLAGS = -I m4

SUBDIRS = po-defs po-defs-fixed po-defs-fixed/fixed data libqalculate src man po docs tests

EXTRA_DIST = config.rpath  \
	autogen.sh \
	README.translate \
	libqalculate.pc.in \
	src/quantum-worker.cc docs/quantum-notation.md \
	windows/QasmAngle.cs windows/CircuitComposer.cs windows/examples.json windows/MainWindow.xaml windows/QuantumStudio.cs windows/Notation-guide.html \
	windows/README.txt windows/build-gui.ps1 windows/build-native.sh \
	windows/package.ps1 windows/test-quantum.ps1 windows/test-qasm-export.py

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libqalculate.pc

if HAVE_DOXYGEN

.PHONY: docs
docs:
	$(MAKE) -C $(top_srcdir)/docs/reference docs

endif
