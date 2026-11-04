## Process this file with automake to produce Makefile.in

ACLOCAL_AMFLAGS = -I m4

SUBDIRS = po-defs po-defs-fixed po-defs-fixed/fixed data libqalculate src man po docs tests

EXTRA_DIST = config.rpath  \
	autogen.sh \
	README.translate \
	docs/quantum-notation.md \
	docs/exact-circuit-protocol.md \
	docs/classical-expression-protocol.md \
	docs/runtime-gate-protocol.md \
	docs/classical-circuit-files.md \
	docs/classical-expression-text.md \
	docs/learning-source-inventory.json \
	libqalculate.pc.in \
	windows/test-source-dist.py \
	windows/build-qasm-import.ps1 \
	windows/test-qasm-arrays.py \
	windows/fixtures/qb-arrays/ripple-carry.qasm \
	windows/fixtures/runtime-subroutines/README.md \
	windows/fixtures/runtime-subroutines/measured-parity.qasm \
	windows/fixtures/runtime-subroutines/qbraid-register-return.qasm \
	windows/fixtures/runtime-subroutines/qbraid-loop-index.qasm \
	windows/build-runtime-angle-import-test.ps1 \
	windows/RuntimeAngleImportTests.cs \
	windows/test-qasm-runtime-numeric.py \
	windows/test-qasm-runtime-numeric-calls.py \
	windows/test-qasm-runtime-collections.py \
	windows/fixtures/dev08-collection-upstream.json \
	docs/runtime-collection-loops.md \
	windows/test-dev08-numeric-source.py \
	windows/fixtures/dev08-numeric-upstream.json \
	docs/learning-evidence/DEV-08-research.md \
	docs/learning-evidence/DEV-08.md \
	windows/test-dev06-source-evidence.py \
	windows/fixtures/dev06-upstream.json \
	windows/fixtures/pyqasm-LICENSE.txt \
	windows/test-qasm-runtime-angles.py \
	windows/test-qasm-runtime-wires.py \
	windows/test-dev07-source-evidence.py \
	windows/fixtures/dev07-upstream.json \
	windows/test-qasm-runtime-gates.py \
	windows/ClassicalRealExpressionText.cs \
	windows/ClassicalRealExpressionTextTests.cs \
	windows/test-real-expression-text.ps1 \
	windows/test-runtime-angle-editor.ps1 \
	windows/test-runtime-angle-editor.py \
	windows/qasm-import-requirements.txt \
	windows/qasm-import.py \
	windows/qasm_import_request.py \
	windows/test-qasm-file-import.py \
	windows/fixtures/qb004/README.md \
	windows/fixtures/qb004/oracle.qasm \
	windows/fixtures/qb004/bernvaz.qasm \
	windows/qasm_source_bundle.py \
	windows/SourceCircuitDocument.cs \
	windows/SourceCircuitDocumentTests.cs \
	windows/SourceImportBridgeTests.cs \
	windows/test-source-import-bridge.ps1 \
	windows/fixtures/qb004/provenance-envelope.json \
	windows/test-qasm-source-bundle.py \
	docs/qasm-source-bundles.md \
	windows/test-qasm-import.py \
	windows/test-qasm-protocol.py \
	windows/test-qasm-classical-expressions.py \
	windows/BoundedUtf8File.cs \
	windows/CircuitComposer.cs \
	windows/NumericalSampling.cs \
	windows/ClassicalExpression.cs \
	windows/ClassicalExpressionQasm.cs \
	windows/ClassicalQasmStorage.cs \
	windows/ClassicalQasmStorageTests.cs \
	windows/test-classical-storage-qasm.ps1 \
	windows/ClassicalProgramQasm.cs \
	windows/ClassicalQasmScopes.cs \
	windows/ClassicalQasmExport.cs \
	windows/ClassicalQasmExportTests.cs \
	windows/test-classical-export.ps1 \
	windows/ClassicalProgramQasmTests.cs \
	windows/test-classical-program-qasm.ps1 \
	windows/ClassicalExpressionQasmTests.cs \
	windows/test-classical-expression-qasm.ps1 \
	windows/test-classical-expression-qasm.py \
	windows/ClassicalExpressionTests.cs \
	windows/ClassicalExpressionText.cs \
	windows/ClassicalExpressionTextTests.cs \
	windows/ExactCircuit.cs \
	windows/ExactCircuitWindow.cs \
	windows/test-exact-window.ps1 \
	windows/ExactCircuitTests.cs \
	windows/ClassicalCircuit.cs \
	windows/ClassicalCircuitTests.cs \
	windows/ClassicalProgramHistory.cs \
	windows/ClassicalProgramHistoryTests.cs \
	windows/ClassicalProgramWindow.cs \
	windows/SamplingTests.cs \
	windows/SamplingWindow.cs \
	windows/SamplingReadout.cs \
	windows/CircuitFileTests.cs \
	windows/ComposerSourceTests.cs \
	windows/qasm_source_diagnostics.py \
	windows/qasm_subroutine_scope.py \
	windows/qasm_runtime_subroutines.py \
	windows/qasm_runtime_numeric.py \
	windows/qasm_runtime_wires.py \
	windows/qasm_concat_parser.py \
	windows/test-classical-module-export.py \
	windows/test-classical-export-ui.py \
	windows/test-composer-source-import.py \
	windows/test-classical-module-import.py \
	windows/test-source-files-ui.py \
	windows/CssCircuitTests.cs \
	windows/CssEncoderCircuitTests.cs \
	windows/MainWindow.xaml \
	windows/Notation-guide.html \
	windows/QasmAngle.cs \
	windows/QasmGateSerializer.cs \
	windows/QasmImport.cs \
	windows/SourceFilesWindow.cs \
	windows/QasmImportTests.cs \
	windows/QuantumStudio.cs \
	windows/SessionStore.cs \
	windows/MatrixDeclarations.cs \
	windows/BasisDeclarations.cs \
	windows/BasisDeclarationEditor.cs \
	windows/BasisDeclarationsTests.cs \
	windows/BasisDeclarationsGuiTests.cs \
	windows/MatrixDeclarationEditor.cs \
	windows/MatrixDeclarationsTests.cs \
	windows/MatrixDeclarationsGuiTests.cs \
	windows/NamedStateEditor.cs \
	windows/WorkspaceTheme.cs \
	windows/WorkspaceTheme.xaml \
	windows/GUI-design.md \
	windows/SessionStoreTests.cs \
	windows/build-gui.ps1 \
	windows/examples.json \
	windows/test-gui.ps1 \
	windows/test-keyboard.ps1 \
	windows/test-sampling-shutdown.ps1 \
	windows/test-sampling-shutdown-observation.ps1 \
	windows/package.ps1 \
	windows/README.txt \
	windows/test-package.py \
	windows/build-native.sh

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libqalculate.pc

if HAVE_DOXYGEN

.PHONY: docs
docs:
	$(MAKE) -C $(top_srcdir)/docs/reference docs

endif

EXTRA_DIST += docs/runtime-numeric-protocol.md docs/learning-evidence/DEV-06.md

EXTRA_DIST += docs/runtime-wire-protocol.md
EXTRA_DIST += docs/runtime-array-storage.md
EXTRA_DIST += windows/qasm_runtime_arrays.py windows/test-qasm-runtime-arrays.py windows/test-runtime-array-model.py

EXTRA_DIST += docs/learning-evidence/DEV-07-research.md

EXTRA_DIST += docs/learning-evidence/DEV-07.md

EXTRA_DIST += docs/runtime-array-views.md docs/runtime-array-view-protocol.md

EXTRA_DIST += docs/runtime-array-view-model.md windows/test-runtime-array-view-model.py

EXTRA_DIST += windows/test-qasm-runtime-array-views.py docs/runtime-array-view-source.md

EXTRA_DIST += windows/test-qasm-runtime-array-copies.py docs/runtime-array-copy.md

EXTRA_DIST += windows/test-qasm-runtime-dynamic-collections.py docs/runtime-dynamic-collections.md

EXTRA_DIST += docs/runtime-wire-reference-checks.md

EXTRA_DIST += windows/test-runtime-wire-reference-model.py

EXTRA_DIST += windows/test-runtime-scalar-quantum-bindings.py

EXTRA_DIST += windows/test-runtime-quantum-register-views.py

EXTRA_DIST += windows/test-runtime-dynamic-quantum-aliases.py

EXTRA_DIST += windows/test-dev08-source-evidence.py windows/fixtures/dev08-upstream.json

EXTRA_DIST += windows/test-runtime-quantum-call-loops.py

EXTRA_DIST += windows/qasm_runtime_bit_aliases.py windows/test-runtime-bit-alias-iteration.py

EXTRA_DIST += docs/learning-evidence/DEV-09.md
EXTRA_DIST += docs/learning-evidence/DEV-10.md docs/learning-evidence/DEV-11.md docs/learning-evidence/dev11/release-summary.json docs/learning-evidence/dev11/probe-release.py docs/learning-evidence/dev11/results-release.json.gz docs/learning-evidence/dev11/results-dev10-reassessment.json.gz
EXTRA_DIST += docs/quantum-domains.md windows/DomainGuiTests.cs windows/test-domains-gui.ps1

EXTRA_DIST += windows/MeasurementGuiTests.cs windows/test-measurements-gui.ps1 docs/quantum-measurements.md
EXTRA_DIST += docs/learning-evidence/dev11/README.md docs/learning-evidence/dev11/comparison-tables.md docs/learning-evidence/dev11/fetch_sources.py docs/learning-evidence/dev11/fixtures.json.gz docs/learning-evidence/dev11/performance-followup.md docs/learning-evidence/dev11/performance-results.json docs/learning-evidence/dev11/primary-inventory.md docs/learning-evidence/dev11/probe.py docs/learning-evidence/dev11/product_cost_probe.py docs/learning-evidence/dev11/results.json.gz docs/learning-evidence/dev11/source-manifest.json docs/learning-evidence/dev11/source-map.json docs/learning-evidence/dev11/summary.json docs/learning-evidence/dev11/test_probe.py docs/learning-evidence/dev11/timing_probe.py

EXTRA_DIST += docs/learning-evidence/dev11/toric-probe.py docs/learning-evidence/dev11/compact-toric.md docs/learning-evidence/dev11/steane-probe.py docs/learning-evidence/dev11/steane-transversal.md windows/CompactPauliGuiTests.cs windows/test-compact-pauli-gui.ps1 windows/SteaneTransversalGuiTests.cs windows/test-steane-transversal-gui.ps1

EXTRA_DIST += docs/learning-evidence/dev11/compact-gui-fixtures.py docs/learning-evidence/dev11/steane-verify-gui.py
# DEV-11d finite instrument audit and standalone GUI validation.
EXTRA_DIST += docs/learning-evidence/dev11/instrument-audit.py \
 docs/learning-evidence/dev11/instrument-audit.md \
 docs/learning-evidence/dev11/instrument-results.json.gz \
 docs/learning-evidence/dev11/instrument-summary.json \
 docs/learning-evidence/dev11/instrument-baseline.json.gz \
 docs/learning-evidence/dev11/instrument-corrected-harness.json.gz \
 docs/learning-evidence/dev11/instrument-expanded.json.gz \
 windows/InstrumentRecoveryGuiTests.cs windows/test-instrument-recovery-gui.ps1
EXTRA_DIST += docs/learning-evidence/dev11/diagram-audit.md docs/learning-evidence/dev11/diagram-audit.py docs/learning-evidence/dev11/diagram-export.cs docs/learning-evidence/dev11/diagram-fixtures.json.gz docs/learning-evidence/dev11/diagram-media.json docs/learning-evidence/dev11/diagram-native.cc docs/learning-evidence/dev11/diagram-results.json.gz docs/learning-evidence/dev11/family-audit.py docs/learning-evidence/dev11/family-fixtures.json.gz docs/learning-evidence/dev11/family-results.json.gz docs/learning-evidence/dev11/remaining-source-ledger.json docs/learning-evidence/dev11/remaining-source-triage.md docs/learning-evidence/dev11/test_diagram_audit.py docs/learning-evidence/dev11/tranche-summary.json

EXTRA_DIST += docs/learning-evidence/dev11/dev11bc-release-summary.json docs/learning-evidence/dev11/toric-results-final.json.gz docs/learning-evidence/dev11/toric-fixtures-final.json.gz docs/learning-evidence/dev11/steane-results-final.json.gz
EXTRA_DIST += docs/learning-evidence/DEV-12.md docs/learning-evidence/dev12/variational-source-manifest.json
EXTRA_DIST += docs/learning-evidence/dev12/variational-baseline-summary.json
EXTRA_DIST += windows/Dev12GuiTests.cs windows/test-dev12-gui.ps1
EXTRA_DIST += docs/learning-evidence/dev12/gui-verify.py
EXTRA_DIST += docs/learning-evidence/dev12/chemistry-diagonalization.md docs/learning-evidence/dev12/chemistry-diagonalization-source-manifest.json docs/learning-evidence/dev12/chemistry-diagonalization-cell-inventory.json docs/learning-evidence/dev12/chemistry-diagonalization-inventory.py docs/learning-evidence/dev12/chemistry-diagonalization-probe.py
EXTRA_DIST += docs/learning-evidence/dev12/ml-audit.py docs/learning-evidence/dev12/ml-numerical-driver.cc docs/learning-evidence/dev12/ml-audit.md docs/learning-evidence/dev12/ml-source-manifest.json docs/learning-evidence/dev12/ml-data-manifest.json docs/learning-evidence/dev12/ml-cell-ledger.json docs/learning-evidence/dev12/ml-results-summary.json

EXTRA_DIST += docs/learning-evidence/dev12/release-summary.json

# Scoped IBM-019 audit and numeric-exponent regression evidence.
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/CHECKLIST-PROPOSAL.md
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/FOLLOWUP.md
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/README.md
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/checks.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/existing-tests.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/exponent-regression.py
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/fixtures.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/inventory.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/ledger.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/literal.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/minimal-probes.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/proposed-regressions.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/provenance.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/regressions.py
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/run.py
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/source-manifest.json
EXTRA_DIST += docs/learning-evidence/aud01-ibm019/validation.json
EXTRA_DIST += docs/learning-evidence/dev11/reassess-performance.py \
 docs/learning-evidence/dev11/matrix-cost.cc \
 docs/learning-evidence/dev11/performance-reassessment.md \
 docs/learning-evidence/dev11/reassessment-run.json.gz \
 docs/learning-evidence/dev11/reassessment-results.json
EXTRA_DIST += docs/learning-evidence/dev17/contract.md
EXTRA_DIST += windows/Dev17GuiTests.cs windows/test-named-subsystems-gui.ps1
EXTRA_DIST += docs/learning-evidence/dev17/validation.md

EXTRA_DIST += docs/learning-evidence/dev17/integration.md
EXTRA_DIST += docs/learning-evidence/dev16/reconciliation.md
EXTRA_DIST += docs/learning-evidence/dev16/rel09-composer.json
EXTRA_DIST += docs/learning-evidence/dev16/rel09-export.json
EXTRA_DIST += docs/learning-evidence/dev16/rel09-modules.json
EXTRA_DIST += docs/learning-evidence/dev16/verification.json
