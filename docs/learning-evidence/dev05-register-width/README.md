# DEV-05 register-width development

This work is not released and does not complete DEV-05. The full checklist is
in [learning-coverage-checklist.md](../../learning-coverage-checklist.md#dev-05).
General tensor ellipses and register sums now have local source and worker
acceptance. Full regression, packaged GUI/session checks, reviewed integration
and published-artifact verification remain required.

Register validity is separate from dense expansion. A nonnegative integer width
may exceed the numerical matrix limit. Typed labels preserve that width, including
leading zeros; numerical bit values must still fit it. Large shapes remain exact
symbolic powers. Wide tensor products and register families retain their operands
and constraints instead of allocating a dense matrix.

The indexed-family extension treats descending adjacent reversed
endpoints as an empty range: `|x_(n-1) ... x_0>` at `n=0` is the one-dimensional
empty-register identity, with amplitude 1. Endpoint notation defines the range;
additional explicitly displayed trailing bits impose presence constraints.
Stored bit assignments and those presence constraints are validated before the
empty identity is returned. Thus supplying `x_0=1` before resolving `n=0`, or
requiring an explicit trailing `x_1`, must report an invalid register rather than
silently discard the bit. More widely reversed endpoints denote negative width
and remain invalid.

Focused tests cover typed widths, large literal states, symbolic domain sizes,
dimension contradictions, indexed assignments and empty-register constraints.
Each suite's source and execution evidence is retained in `cleanup-audit/`.
Source review alone is not execution evidence, and focused checks are not a
replacement for testing the final packaged application.

The current implementation also retains indexed tensor series and complete-alphabet
register sums beyond their expansion limits. Ordered substitutions preserve bound
indices and free register components. Arithmetic computational kets retain an
unresolved dimension until an operator or an equality supplies compatible context;
pure equality chains share that context. Inequality does not assign a dimension.

`bits(value, width)` validates the integer value and width independently of its
1,024-entry vector expansion budget. Symbolic and larger widths remain deferred.
Empty registers have value zero, zero binary dot product, and empty XOR output.
Late substitutions still reject invalid values and incompatible widths.

The local focused run passed 2,732 native checks and 89 worker requests. It includes
the original Fourier equality with explicit finite parameter and root-of-unity
substitutions, stable ordinary Copy, and exact reference comparisons. These finite
witnesses do not establish a general symbolic proof or whole-lesson coverage.

Permanent regression coverage includes the register-width, indexed-width,
tensor-series, register-sum, wide-basis and binary test suites in `src/`. The
`quantum-arithmetic-basis-worker-test.py`, `quantum-wide-basis-worker-test.py`,
`quantum-tensor-chain-worker-test.py` and indexed-display worker tests exercise
ordinary Copy and exact reference comparisons. All are registered for `make check`.
The full project has 95 registered tests; the fresh full-suite result is pending.

`diagnostics/register-width/` and `windows/RegisterWidthGuiTests.cs` add nine
hosted application fixtures with 53 successful calculations and two invalid-width
checks. The driver tests actual Copy, readable results, production session Save/Open,
and independent finite references. Its source and worker-only fixture preflight
have been checked; actual hosted execution and visual review remain pending.
