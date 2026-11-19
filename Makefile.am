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
	windows/dev13-notebooks/execute_ibm019.py \
	windows/dev13-notebooks/ibm019-requirements.lock \
	docs/learning-evidence/dev13/execution-interface.md \
	windows/dev13-notebooks/contracts/ibm019.json \
	windows/dev13-notebooks/contracts/ibm020.json \
	windows/dev13-notebooks/execution.py \
	windows/dev13-notebooks/profiles/qiskit-aer-win-py312.json \
	windows/dev13-notebooks/run.py \
	windows/dev13-notebooks/test_execution.py \
	windows/dev13-notebooks/witnesses/ibm019.py \
	windows/dev13-notebooks/witnesses/ibm020.py \
	docs/learning-evidence/dev13/IBM-019-execution.md \
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
EXTRA_DIST += docs/learning-evidence/dev17/numeric-k-gui.md
EXTRA_DIST += docs/learning-evidence/dev17/release-proposal.md
EXTRA_DIST += diagnostics/dev17-unattended/KeywordGuiTests.cs \
 diagnostics/dev17-unattended/Run-Acceptance.ps1 \
 diagnostics/dev17-unattended/Inspect-Environment.ps1 \
 diagnostics/dev17-unattended/Test-ChildShell.ps1 \
 diagnostics/dev17-unattended/FEASIBILITY.md \
 diagnostics/dev17-unattended/hosted-workflow.yml.proposed \
 .github/workflows/dev17-release-candidate.yml
EXTRA_DIST += docs/learning-evidence/dev16/reconciliation.md
EXTRA_DIST += docs/learning-evidence/dev16/rel09-composer.json
EXTRA_DIST += docs/learning-evidence/dev16/rel09-export.json
EXTRA_DIST += docs/learning-evidence/dev16/rel09-modules.json
EXTRA_DIST += docs/learning-evidence/dev16/verification.json
EXTRA_DIST += docs/learning-evidence/dev05-scalar-product/README.md docs/learning-evidence/dev05-scalar-product/evidence.json

EXTRA_DIST += windows/ScalarProductGuiTests.cs diagnostics/scalar-product/Run-Acceptance.ps1 diagnostics/scalar-product/fragment.txt diagnostics/scalar-product/source.json
EXTRA_DIST += windows/HadamardTensorGuiTests.cs diagnostics/hadamard-tensor/Run-Acceptance.ps1 diagnostics/hadamard-tensor/fragment.txt diagnostics/hadamard-tensor/source.json diagnostics/hadamard-tensor/expected.json
EXTRA_DIST += windows/RegisterWidthGuiTests.cs diagnostics/register-width/Run-Acceptance.ps1 diagnostics/register-width/fixtures.json
EXTRA_DIST += docs/learning-evidence/dev05-register-width/README.md
EXTRA_DIST += windows/dev13-notebooks/contracts/ibm-timing.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb007.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb013.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb017.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb027.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb030.json
EXTRA_DIST += windows/dev13-notebooks/ibm019-linux-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/linux-notebook-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/linux_lifecycle.py
EXTRA_DIST += windows/dev13-notebooks/observers/ibm_timing.py
EXTRA_DIST += windows/dev13-notebooks/observers/ibm_timing_checkpoint.py
EXTRA_DIST += windows/dev13-notebooks/observers/ibm_timing_cleanup.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb013.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb013_checkpoint.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb013_cleanup.py
EXTRA_DIST += windows/dev13-notebooks/profiles/notebook-linux-py312.json
EXTRA_DIST += windows/dev13-notebooks/profiles/pulser-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/profiles/qir-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/profiles/qiskit-aer-linux-py312.json
EXTRA_DIST += windows/dev13-notebooks/profiles/stim-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/profiles/timing-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/pulser-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/qb013_output_audit.py
EXTRA_DIST += windows/dev13-notebooks/qb013_reference.py
EXTRA_DIST += windows/dev13-notebooks/qir-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/stim-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/test_linux_execution.py
EXTRA_DIST += windows/dev13-notebooks/test_qb013.py
EXTRA_DIST += windows/dev13-notebooks/test_qb027.py
EXTRA_DIST += windows/dev13-notebooks/test_qb030.py
EXTRA_DIST += windows/dev13-notebooks/test_timing.py
EXTRA_DIST += windows/dev13-notebooks/test_windows_lifecycle.py
EXTRA_DIST += windows/dev13-notebooks/qir_import.py
EXTRA_DIST += windows/dev13-notebooks/test_qir_import.py
EXTRA_DIST += windows/dev13-notebooks/test_qir_import_native.py
EXTRA_DIST += windows/QirImportBridgeTests.cs
EXTRA_DIST += windows/build-qir-import-test.ps1
EXTRA_DIST += docs/learning-evidence/dev14-static-qir-import.md
EXTRA_DIST += docs/learning-evidence/dev13/ibm-timing-source-audit.md
EXTRA_DIST += docs/learning-evidence/dev13/ibm-timing-source-audit.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb018.json
EXTRA_DIST += windows/dev13-notebooks/profiles/squin-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/squin-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb018.py
EXTRA_DIST += windows/dev13-notebooks/test_qb018.py
EXTRA_DIST += docs/learning-evidence/dev13/qb018-squin.md
EXTRA_DIST += docs/learning-evidence/dev13/qb018-squin.json
EXTRA_DIST += docs/learning-evidence/dev13/qb015/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb015/probe.py
EXTRA_DIST += docs/learning-evidence/dev13/qb015/index.json
EXTRA_DIST += windows/dev13-notebooks/timing-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/timing_reference.py
EXTRA_DIST += windows/dev13-notebooks/windows_lifecycle.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/ibm_timing.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb007.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb013.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb017.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb027.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb030.py
EXTRA_DIST += windows/dev13-notebooks/.gitattributes
EXTRA_DIST += docs/learning-evidence/dev13/shared-runtime-integration.md
EXTRA_DIST += docs/learning-evidence/dev13/qb013-runtime-replay/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb013-runtime-replay/index.json
EXTRA_DIST += docs/learning-evidence/dev13/qb013-runtime-replay/.gitattributes

EXTRA_DIST += windows/dev13-notebooks/autoqasm-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/profiles/autoqasm-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb015.json
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb015.py
EXTRA_DIST += windows/dev13-notebooks/test_qb015.py
EXTRA_DIST += docs/learning-evidence/dev13/qb015/autoqasm-route.md
EXTRA_DIST += docs/learning-evidence/dev13/qb015/autoqasm-route.json
EXTRA_DIST += docs/learning-evidence/dev14-qir-width.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb001.json
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb001.py
EXTRA_DIST += windows/dev13-notebooks/test_qb001.py
EXTRA_DIST += docs/learning-evidence/dev13/qb001/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb001/index.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb002.json
EXTRA_DIST += windows/dev13-notebooks/observers/qb002_checkpoint.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb002.py
EXTRA_DIST += windows/dev13-notebooks/test_qb002.py
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb002-transformations.json
EXTRA_DIST += docs/learning-evidence/dev13/qb002/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb002/index.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb003.json
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb003.py
EXTRA_DIST += windows/dev13-notebooks/test_qb003.py
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb003-unrolled.qasm
EXTRA_DIST += docs/learning-evidence/dev13/qb003/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb003/index.json
EXTRA_DIST += docs/learning-evidence/dev13/selected-setup.md
EXTRA_DIST += docs/learning-evidence/dev13/selected-setup.json
EXTRA_DIST += docs/learning-evidence/dev13/qb003/clean-build.md
EXTRA_DIST += docs/learning-evidence/dev13/qb003/clean-build.json

EXTRA_DIST += windows/dev13-notebooks/algorithms-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/profiles/algorithms-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb004.json
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb004.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb004_windows.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb004_checkpoint.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb004_cleanup.py
EXTRA_DIST += windows/dev13-notebooks/test_qb004.py
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb004-1011.qasm
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb004-101.qasm
EXTRA_DIST += docs/learning-evidence/dev13/qb004/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb004/index.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb005.json
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb005.py
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb005-qft3.qasm
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb005-iqft3.qasm
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb005-qft4.qasm
EXTRA_DIST += windows/dev13-notebooks/test_qb005.py
EXTRA_DIST += docs/learning-evidence/dev13/qb005/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb005/index.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb006.json
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb006.py
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb006-default.qasm
EXTRA_DIST += windows/dev13-notebooks/fixtures/qb006-three-counting.qasm
EXTRA_DIST += windows/dev13-notebooks/test_qb006.py
EXTRA_DIST += docs/learning-evidence/dev13/qb006/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb006/index.json
EXTRA_DIST += windows/dev13-notebooks/contracts/qb007-cpu.json
EXTRA_DIST += windows/dev13-notebooks/profiles/qsim-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/qsim-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb007_cpu.py
EXTRA_DIST += windows/dev13-notebooks/test_qb007_cpu.py
EXTRA_DIST += docs/learning-evidence/dev13/qb007-cpu/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb007-cpu/index.json

EXTRA_DIST += windows/dev13-notebooks/contracts/qb008.json
EXTRA_DIST += windows/dev13-notebooks/profiles/grover-win-py312.json
EXTRA_DIST += windows/dev13-notebooks/grover-requirements.lock
EXTRA_DIST += windows/dev13-notebooks/observers/qb008_capture.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb008_install.py
EXTRA_DIST += windows/dev13-notebooks/observers/qb008_restore.py
EXTRA_DIST += windows/dev13-notebooks/witnesses/qb008.py
EXTRA_DIST += windows/dev13-notebooks/test_qb008.py
EXTRA_DIST += docs/learning-evidence/dev13/qb008/README.md
EXTRA_DIST += docs/learning-evidence/dev13/qb008/index.json
EXTRA_DIST += docs/learning-evidence/dev13/qb010-device-discovery.json
EXTRA_DIST += docs/learning-evidence/dev13/transpiler-notebooks.json
EXTRA_DIST += docs/learning-evidence/dev13/qb014-visualization.json
EXTRA_DIST += docs/learning-evidence/dev13/qb016-batch.json
EXTRA_DIST += docs/learning-evidence/dev13/qb017-qir.json
EXTRA_DIST += docs/learning-evidence/dev13/qb019-bv.json
EXTRA_DIST += docs/learning-evidence/dev13/qb020-local.json
EXTRA_DIST += docs/learning-evidence/dev13/qb021-qb022-local.json
EXTRA_DIST += docs/learning-evidence/dev13/qb023-qb024-local.json
EXTRA_DIST += docs/learning-evidence/dev13/qb025-qb026-quobly.json
EXTRA_DIST += docs/learning-evidence/dev13/qb027-qb029-providers.json
EXTRA_DIST += docs/learning-evidence/dev13/qb030-qb033-providers.json
EXTRA_DIST += docs/learning-evidence/dev13/qb034-benchmark.json
EXTRA_DIST += docs/learning-evidence/dev13/qb035-quickstart.json

EXTRA_DIST += docs/learning-evidence/aud02/qbraid-catalog-20261117.md docs/learning-evidence/aud02/qbraid-catalog-20261117.json

EXTRA_DIST += docs/learning-evidence/aud02/ibm-catalog-20261117.md docs/learning-evidence/aud02/ibm-catalog-20261117.json
EXTRA_DIST += docs/learning-evidence/aud02/mod007-grover-runtime050.json
EXTRA_DIST += docs/learning-evidence/aud02/mod006-mod010-runtime050.json
EXTRA_DIST += docs/learning-evidence/aud02/mod008-teleportation.json
EXTRA_DIST += docs/learning-evidence/aud02/mod011-order-finding.json
EXTRA_DIST += docs/learning-evidence/aud02/mod012-vqe.json
EXTRA_DIST += docs/learning-evidence/aud02/mod013-nmr.json
EXTRA_DIST += docs/learning-evidence/aud02/mod005-bell-inequality.json
EXTRA_DIST += docs/learning-evidence/aud02/mod004-uncertainty.json
EXTRA_DIST += docs/learning-evidence/aud02/mod003-stern-gerlach.json
EXTRA_DIST += docs/learning-evidence/aud02/mod001-mod002-introductory.json
EXTRA_DIST += docs/learning-evidence/aud02/mod009-key-distribution.json
EXTRA_DIST += docs/learning-evidence/dev13/qb036-qb038-local.json
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-query-algorithms.json
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-inventory-map.json
EXTRA_DIST += docs/learning-evidence/aud01/map-ibm020-inventory.py
EXTRA_DIST += docs/learning-evidence/aud01/replay-ibm020-native.py
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-literal-results.json
EXTRA_DIST += docs/learning-evidence/aud01/replay-ibm020-literals.py
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-display-punctuation.json
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-wrapped-comparison.json
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-oracle-semantics.json
EXTRA_DIST += docs/learning-evidence/aud01/check-ibm020-oracle-semantics.py
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-typed-dot.json
EXTRA_DIST += docs/learning-evidence/aud01/check-ibm020-classical-queries.py
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-classical-queries.json
EXTRA_DIST += docs/learning-evidence/aud01/check-ibm020-query-cost.py
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-query-cost.json
EXTRA_DIST += docs/learning-evidence/aud01/ibm020.md
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-hadamard-gui.json
EXTRA_DIST += docs/learning-evidence/aud01/ibm020-gui-corpus.json
