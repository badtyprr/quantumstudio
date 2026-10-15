#
# src/Makefile.am for qalculate
#

AM_CPPFLAGS = \
	-DPACKAGE_DATA_DIR=\""$(datadir)"\" \
	-I$(top_srcdir) \
	-I$(top_srcdir)/libqalculate \
	@LIBCURL_CFLAGS@ @LIBXML_CFLAGS@ @ICU_CFLAGS@

bin_PROGRAMS = @QALCULATE_TEXT@
noinst_PROGRAMS = @QALCULATE_DEFS2DOC@ @QALCULATE_TEST@ @QALCULATE_UNITTEST@
EXTRA_PROGRAMS = qalc defs2doc test unittest
check_PROGRAMS = quantum-superoperators-test quantum-geometry-test quantum-reset-test quantum-noise-test quantum-operators-test quantum-subsystem-test quantum-gates-test quantum-measurement-test quantum-matrix-power-test quantum-matrix-exp-test quantum-algebra-test quantum-state-functions-test quantum-notation-test quantum-state-test threadtest quantumtex-test quantum-singular-test
TESTS_ENVIRONMENT = QALCULATE_DEFINITIONS_DIR=$(abs_top_builddir)/data
TESTS = quantum-superoperators-test quantum-geometry-test quantum-reset-test quantum-noise-test quantum-operators-test quantum-subsystem-test quantum-gates-test quantum-measurement-test quantum-matrix-power-test quantum-matrix-exp-test quantum-algebra-test quantum-state-functions-test quantum-notation-test quantum-state-test unittest threadtest quantumtex-test quantum-singular-test

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
