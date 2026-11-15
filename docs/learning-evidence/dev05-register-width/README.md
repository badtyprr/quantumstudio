# DEV-05 register-width release evidence

This work shipped in checkpoint-c5a456cd on 2026-11-15. Full regression,
packaged GUI/session checks, independent reviews and public-download verification
passed as recorded below. The broader source audit remains open in the
[development checklist](../../learning-coverage-checklist.md#dev-05).

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
The final merged Linux suite passed all 95 registered tests. The final Windows package passed 94 tests with the established thread-test skip and no failures, including 2,308 worker process checks.

`diagnostics/register-width/` and `windows/RegisterWidthGuiTests.cs` add nine
hosted application fixtures with 53 successful calculations and two invalid-width
checks. The driver tests actual Copy, readable results, production session Save/Open,
and independent finite references. The final non-candidate hosted run passed all 55 calls, including eight finite reference comparisons. Together with scalar-product and Hadamard suites, all 71 calls and 11 session round trips passed. All 37 DEV-05 captures match previously inspected candidate images exactly; 13 additional named-subsystem/package-smoke captures were inspected individually.

## Published release — 2026-11-15

[checkpoint-c5a456cd](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-c5a456cd) packages merged revision `c5a456cde595b3e1211cfc51a233dea511322a56`, tree `6e197c88983875c2b4b29266e917c6693925bfbc`. The separate build orchestration revision is `d8853d6ddaa561ffce4acb240a3b5e414b236971`; [run 43741675632](https://github.com/badtyprr/quantumstudio/actions/runs/43741675632) passed all four hosted GUI suites. Independent Spec and Standards reviews passed on the actual final evidence.

The ZIP contains 360 payload files plus its manifest. Additional checks against the downloaded worker passed 212 named-subsystem checks, 30 exponent cases plus 30 re-entries, 65 finite fixtures, the original M10/re-entry case and all 286 historical fixtures. Before/after payload hashes matched.

Both public assets were downloaded without credentials and exactly matched the accepted build:

- Windows ZIP: 82,790,916 bytes; SHA-256 `fc37b7d107a883afe2e06dc9ee438a7ac68533f5711db8e41d5439c4b39507f4`.
- Source archive: 5,012,600 bytes; SHA-256 `3e78894de44fa1d7f14651fe384ce702e3551f63a7a5a94406db2b4e14f93602`.

The source audit found 646 matching tracked members, 21 generated INSTALL/catalog differences and 24 omitted metadata/docs/auxiliary files. All 74 generated untracked members were reviewed. These are documented build outputs, not a claim of translation equivalence or inclusion of every tracked file.

Evidence is retained outside disposable clones in `cleanup-audit/coordinator-20261104/`: `dev05-final-release-acceptance-20261115.json`, `dev05-final-actual-spec-review-20261115.json`, `dev05-final-actual-standards-review-20261115.json`, `dev05-final-source-generated-standards-review-20261115.json`, `dev05-final-visual-review-20261115.json`, and `dev05-public-download-20261115/verification.json`. Public release assets are also retained in root `dist/releases/c5a456cd`.

The release supports the documented indexed families and carries unresolved width constraints without forcing dense expansion. Finite reference substitutions do not establish a general symbolic equation solver, every possible ellipsis grammar, or whole-notebook proofs. Saved-session tests exercise production Save/Open methods, not native file dialogs; captures cover the current viewport.
