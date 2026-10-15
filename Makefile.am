## Process this file with automake to produce Makefile.in

ACLOCAL_AMFLAGS = -I m4

SUBDIRS = po-defs po-defs-fixed po-defs-fixed/fixed data libqalculate src man po docs tests

EXTRA_DIST = config.rpath  \
	autogen.sh \
	README.translate \
	libqalculate.pc.in \
	src/quantum-worker.cc \
	docs/quantum-notation.md \
	docs/ibm-learning-sections.json \
	docs/learning-source-inventory.json \
	docs/qbraid-notebook-audit.json \
	windows/CircuitComposer.cs \
	windows/CssCircuitTests.cs \
	windows/CssEncoderCircuitTests.cs \
	windows/MainWindow.xaml \
	windows/Notation-guide.html \
	windows/QasmAngle.cs \
	windows/QasmImport.cs \
	windows/QuantumStudio.cs \
	windows/README.txt \
	windows/SessionStore.cs \
	windows/build-gui.ps1 \
	windows/build-native.sh \
	windows/build-qasm-import.ps1 \
	windows/examples.json \
	windows/package.ps1 \
	windows/qasm-import-requirements.txt \
	windows/qasm-import.py \
	windows/test-adjacent-registers.py \
	windows/test-basis-dim.py \
	windows/test-bell-circuits.py \
	windows/test-bell-labels.py \
	windows/test-bernstein-vazirani.py \
	windows/test-binary-fractions.py \
	windows/test-bitdot.py \
	windows/test-bits-conversion.py \
	windows/test-bitxor.py \
	windows/test-blocksum.py \
	windows/test-boolean.py \
	windows/test-chi.py \
	windows/test-comma-registers.py \
	windows/test-comparisons.py \
	windows/test-css-circuits.py \
	windows/test-css-encoder-circuits.py \
	windows/test-css-encoder.py \
	windows/test-css.py \
	windows/test-entropy.py \
	windows/test-gate-powers.py \
	windows/test-gf2-inverse.py \
	windows/test-gf2.py \
	windows/test-grover.py \
	windows/test-guide.cjs \
	windows/test-guide.py \
	windows/test-hellinger.py \
	windows/test-ibm-measurement-lessons.py \
	windows/test-indexed-kets.py \
	windows/test-indexed-spin.py \
	windows/test-indexed-tensor.py \
	windows/test-lindblad.py \
	windows/test-linear-gate.py \
	windows/test-linear-synthesis.py \
	windows/test-logm.py \
	windows/test-matrix-order.py \
	windows/test-mod-notation.py \
	windows/test-negativity.py \
	windows/test-operator-norms.py \
	windows/test-oracle-function.py \
	windows/test-output-registers.py \
	windows/test-pauli-labels.py \
	windows/test-phase-function.py \
	windows/test-physics-tex.py \
	windows/test-power-gates.py \
	windows/test-ptm.py \
	windows/test-qasm-export.py \
	windows/test-qasm-import.py \
	windows/test-qbraid-notebooks.py \
	windows/test-qpe.py \
	windows/test-quantum.ps1 \
	windows/test-rectangular-channels.py \
	windows/test-reflections.py \
	windows/test-register-elements.py \
	windows/test-register-repeat.py \
	windows/test-schmidt.py \
	windows/test-simon.py \
	windows/test-source-dist.py \
	windows/test-stabilizer-correction.py \
	windows/test-stabilizer-distance.py \
	windows/test-stabilizer-notation.py \
	windows/test-stabilizers.py \
	windows/test-tex-norms.py \
	windows/test-unicode-indexed.py \
	windows/test-xor-labels.py

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libqalculate.pc

if HAVE_DOXYGEN

.PHONY: docs
docs:
	$(MAKE) -C $(top_srcdir)/docs/reference docs

endif
