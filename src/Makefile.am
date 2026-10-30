#
# src/Makefile.am for qalculate
#

AM_CPPFLAGS = \
	-DPACKAGE_DATA_DIR=\""$(datadir)"\" \
	-I$(top_srcdir) \
	-I$(top_srcdir)/libqalculate \
	@LIBCURL_CFLAGS@ @LIBXML_CFLAGS@ @ICU_CFLAGS@

bin_PROGRAMS = @QALCULATE_TEXT@ quantum-worker
noinst_PROGRAMS = @QALCULATE_DEFS2DOC@ @QALCULATE_TEST@ @QALCULATE_UNITTEST@
EXTRA_PROGRAMS = qalc defs2doc test unittest
check_PROGRAMS = quantum-readout-test quantum-trajectory-test quantum-numerical-sampling-test quantum-numerical-state-test quantum-parser-integration-test quantum-negativity-test quantum-css-test quantum-stabilizer-test quantum-indexed-test quantum-order-test quantum-binary-test quantum-evolution-test quantum-hellinger-test quantum-channel-representations-test quantum-superoperators-test quantum-geometry-test quantum-reset-test quantum-noise-test quantum-operators-test quantum-subsystem-test quantum-gates-test quantum-measurement-test quantum-matrix-power-test quantum-matrix-exp-test quantum-algebra-test quantum-state-functions-test quantum-notation-test quantum-state-test threadtest quantumtex-test quantum-singular-test
TESTS_ENVIRONMENT = QALCULATE_DEFINITIONS_DIR=$(abs_top_builddir)/data
TESTS = quantum-readout-test quantum-trajectory-test quantum-sampling-request-test.py quantum-numerical-sampling-test quantum-numerical-state-test quantum-worker-test.py quantum-parser-integration-test quantum-negativity-test quantum-css-test quantum-stabilizer-test quantum-indexed-test quantum-order-test quantum-binary-test quantum-evolution-test quantum-hellinger-test quantum-channel-representations-test quantum-superoperators-test quantum-geometry-test quantum-reset-test quantum-noise-test quantum-operators-test quantum-subsystem-test quantum-gates-test quantum-measurement-test quantum-matrix-power-test quantum-matrix-exp-test quantum-algebra-test quantum-state-functions-test quantum-notation-test quantum-state-test unittest threadtest quantumtex-test quantum-singular-test

qalc_SOURCES = qalc.cc

qalc_LDADD = \
	@LIBXML_LIBS@ \
	@LIBCURL_LIBS@ \
	@ICU_LIBS@ \
	@READLINE_LIBS@ \
	@LTLIBINTL@ \
	@LTLIBICONV@ \
	../libqalculate/libqalculate.la

defs2doc_SOURCES = defs2doc.cc

defs2doc_LDADD = \
	@LIBXML_LIBS@ \
	@LIBCURL_LIBS@ \
	@ICU_LIBS@ \
	@LTLIBINTL@ \
	@LTLIBICONV@ \
	../libqalculate/libqalculate.la

test_SOURCES = test.cc

test_LDADD = \
	@LIBXML_LIBS@ \
	@LIBCURL_LIBS@ \
	@ICU_LIBS@ \
	@LTLIBINTL@ \
	@LTLIBICONV@ \
	../libqalculate/libqalculate.la

unittest_SOURCES = unittest.cc

threadtest_SOURCES = threadtest.cc
threadtest_LDADD = $(test_LDADD)

quantumtex_test_SOURCES = quantumtex-test.cc
quantumtex_test_LDADD = ../libqalculate/libqalculate.la

quantum_singular_test_SOURCES = quantum-singular-test.cc
quantum_singular_test_LDADD = $(test_LDADD)

#install-exec-local:
#	cd $(DESTDIR)$(bindir) && rm -f qalculate; $(LN_S) @LN_QALCULATE@ qalculate


quantum_state_test_SOURCES = quantum-state-test.cc
quantum_state_test_LDADD = $(test_LDADD)

quantum_notation_test_SOURCES = quantum-notation-test.cc
quantum_notation_test_LDADD = ../libqalculate/libqalculate.la

quantum_state_functions_test_SOURCES = quantum-state-functions-test.cc
quantum_state_functions_test_LDADD = $(test_LDADD)

quantum_algebra_test_SOURCES = quantum-algebra-test.cc
quantum_algebra_test_LDADD = $(test_LDADD)

quantum_matrix_exp_test_SOURCES = quantum-matrix-exp-test.cc
quantum_matrix_exp_test_LDADD = $(test_LDADD)

quantum_matrix_power_test_SOURCES = quantum-matrix-power-test.cc
quantum_matrix_power_test_LDADD = $(test_LDADD)

quantum_measurement_test_SOURCES = quantum-measurement-test.cc
quantum_measurement_test_LDADD = $(test_LDADD)

quantum_gates_test_SOURCES = quantum-gates-test.cc
quantum_gates_test_LDADD = $(test_LDADD)

quantum_subsystem_test_SOURCES = quantum-subsystem-test.cc
quantum_subsystem_test_LDADD = $(test_LDADD)

quantum_operators_test_SOURCES = quantum-operators-test.cc
quantum_operators_test_LDADD = $(test_LDADD)

quantum_noise_test_SOURCES = quantum-noise-test.cc
quantum_noise_test_LDADD = $(test_LDADD)

quantum_reset_test_SOURCES = quantum-reset-test.cc
quantum_reset_test_LDADD = $(test_LDADD)

quantum_geometry_test_SOURCES = quantum-geometry-test.cc
quantum_geometry_test_LDADD = $(test_LDADD)

quantum_superoperators_test_SOURCES = quantum-superoperators-test.cc
quantum_superoperators_test_LDADD = $(test_LDADD)

quantum_channel_representations_test_SOURCES = quantum-channel-representations-test.cc
quantum_channel_representations_test_LDADD = $(test_LDADD)

quantum_hellinger_test_SOURCES = quantum-hellinger-test.cc
quantum_hellinger_test_LDADD = $(test_LDADD)

quantum_evolution_test_SOURCES = quantum-evolution-test.cc
quantum_evolution_test_LDADD = $(test_LDADD)

quantum_binary_test_SOURCES = quantum-binary-test.cc
quantum_binary_test_LDADD = $(test_LDADD)

quantum_order_test_SOURCES = quantum-order-test.cc
quantum_order_test_LDADD = $(test_LDADD)

quantum_indexed_test_SOURCES = quantum-indexed-test.cc
quantum_indexed_test_LDADD = $(test_LDADD)

quantum_stabilizer_test_SOURCES = quantum-stabilizer-test.cc
quantum_stabilizer_test_LDADD = $(test_LDADD)

quantum_css_test_SOURCES = quantum-css-test.cc
quantum_css_test_LDADD = $(test_LDADD)

quantum_negativity_test_SOURCES = quantum-negativity-test.cc
quantum_negativity_test_LDADD = $(test_LDADD)

quantum_parser_integration_test_SOURCES = quantum-parser-integration-test.cc
quantum_parser_integration_test_LDADD = $(test_LDADD)

quantum_worker_SOURCES = quantum-worker.cc quantum-display.h quantum-sampling-request.cc quantum-sampling-request.h quantum-exact-request.cc quantum-exact-request.h quantum-classical-request.h
quantum_worker_LDADD = $(test_LDADD)
TEST_EXTENSIONS = .py
PY_LOG_COMPILER = python3
EXTRA_DIST = quantum-worker-test.py quantum-sampling-request-test.py quantum-exact-request-test.py quantum-exact-fixtures.json quantum-classical-request-test.py
TESTS += quantum-exact-request-test.py quantum-classical-request-test.py
EXTRA_DIST += quantum-runtime-angle-request-test.py
TESTS += quantum-runtime-angle-request-test.py

quantum_numerical_state_test_SOURCES = quantum-numerical-state-test.cc
quantum_numerical_state_test_LDADD = ../libqalculate/libqalculate.la

quantum_numerical_sampling_test_SOURCES = quantum-numerical-sampling-test.cc
quantum_numerical_sampling_test_LDADD = ../libqalculate/libqalculate.la

quantum_trajectory_test_SOURCES = quantum-trajectory-test.cc
quantum_trajectory_test_LDADD = ../libqalculate/libqalculate.la

quantum_readout_test_SOURCES = quantum-readout-test.cc
quantum_readout_test_LDADD = ../libqalculate/libqalculate.la

check_PROGRAMS += quantum-exact-records-test
TESTS += quantum-exact-records-test
quantum_exact_records_test_SOURCES = quantum-exact-records-test.cc
quantum_exact_records_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-operation-test
TESTS += quantum-exact-operation-test
quantum_exact_operation_test_SOURCES = quantum-exact-operation-test.cc
quantum_exact_operation_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-readout-test
TESTS += quantum-exact-readout-test
quantum_exact_readout_test_SOURCES = quantum-exact-readout-test.cc
quantum_exact_readout_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-circuit-test
TESTS += quantum-exact-circuit-test
quantum_exact_circuit_test_SOURCES = quantum-exact-circuit-test.cc
quantum_exact_circuit_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-test
TESTS += quantum-classical-test
quantum_classical_test_SOURCES = quantum-classical-test.cc
quantum_classical_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-integer-test
TESTS += quantum-classical-integer-test
quantum_classical_integer_test_SOURCES = quantum-classical-integer-test.cc
quantum_classical_integer_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-range-test
TESTS += quantum-classical-range-test
quantum_classical_range_test_SOURCES = quantum-classical-range-test.cc
quantum_classical_range_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-real-expression-test
TESTS += quantum-classical-real-expression-test
quantum_classical_real_expression_test_SOURCES = quantum-classical-real-expression-test.cc
quantum_classical_real_expression_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-runtime-rotation-test
TESTS += quantum-runtime-rotation-test
quantum_runtime_rotation_test_SOURCES = quantum-runtime-rotation-test.cc
quantum_runtime_rotation_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-runtime-rotation-test
TESTS += quantum-exact-runtime-rotation-test
quantum_exact_runtime_rotation_test_SOURCES = quantum-exact-runtime-rotation-test.cc
quantum_exact_runtime_rotation_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-phase-test
TESTS += quantum-exact-phase-test
quantum_exact_phase_test_SOURCES = quantum-exact-phase-test.cc
quantum_exact_phase_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-phase-expression-test
TESTS += quantum-exact-phase-expression-test
quantum_exact_phase_expression_test_SOURCES = quantum-exact-phase-expression-test.cc
quantum_exact_phase_expression_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-phase-circuit-test
TESTS += quantum-exact-phase-circuit-test
quantum_exact_phase_circuit_test_SOURCES = quantum-exact-phase-circuit-test.cc
quantum_exact_phase_circuit_test_LDADD = $(test_LDADD)
TESTS += quantum-phase-circuit-request-test.py
EXTRA_DIST += quantum-phase-circuit-request-test.py quantum-phase-iqft.qasm

check_PROGRAMS += quantum-trajectory-range-test
TESTS += quantum-trajectory-range-test
quantum_trajectory_range_test_SOURCES = quantum-trajectory-range-test.cc
quantum_trajectory_range_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-exact-range-test
TESTS += quantum-exact-range-test
quantum_exact_range_test_SOURCES = quantum-exact-range-test.cc
quantum_exact_range_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-integer-type-test
TESTS += quantum-classical-integer-type-test
quantum_classical_integer_type_test_SOURCES = quantum-classical-integer-type-test.cc
quantum_classical_integer_type_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-integer-expression-test
TESTS += quantum-classical-integer-expression-test
quantum_classical_integer_expression_test_SOURCES = quantum-classical-integer-expression-test.cc
quantum_classical_integer_expression_test_LDADD = $(test_LDADD)

check_PROGRAMS += quantum-classical-integer-storage-test
TESTS += quantum-classical-integer-storage-test
quantum_classical_integer_storage_test_SOURCES = quantum-classical-integer-storage-test.cc
quantum_classical_integer_storage_test_LDADD = $(test_LDADD)

EXTRA_DIST += quantum-loop-request-test.py
TESTS += quantum-loop-request-test.py

check_PROGRAMS += quantum-runtime-gate-test
TESTS += quantum-runtime-gate-test
quantum_runtime_gate_test_SOURCES = quantum-runtime-gate-test.cc
quantum_runtime_gate_test_LDADD = $(test_LDADD)

EXTRA_DIST += quantum-runtime-gate-request-test.py
TESTS += quantum-runtime-gate-request-test.py

check_PROGRAMS += quantum-classical-numeric-test quantum-runtime-numeric-test
TESTS += quantum-classical-numeric-test quantum-runtime-numeric-test
quantum_classical_numeric_test_SOURCES = quantum-classical-numeric-test.cc
quantum_classical_numeric_test_LDADD = $(test_LDADD)
quantum_runtime_numeric_test_SOURCES = quantum-runtime-numeric-test.cc
quantum_runtime_numeric_test_LDADD = $(test_LDADD)
check_PROGRAMS += quantum-classical-array-test
TESTS += quantum-classical-array-test
quantum_classical_array_test_SOURCES = quantum-classical-array-test.cc
quantum_classical_array_test_LDADD = $(test_LDADD)
EXTRA_DIST += quantum-runtime-numeric-request-test.py
TESTS += quantum-runtime-numeric-request-test.py

EXTRA_DIST += quantum-wire-selection-request-test.py
TESTS += quantum-wire-selection-request-test.py
EXTRA_DIST += quantum-classical-array-request-test.py
TESTS += quantum-classical-array-request-test.py

EXTRA_DIST += quantum-classical-array-view-request-test.py
TESTS += quantum-classical-array-view-request-test.py

EXTRA_DIST += quantum-wire-reference-request-test.py
TESTS += quantum-wire-reference-request-test.py
