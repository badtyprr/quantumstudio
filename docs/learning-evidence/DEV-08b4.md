# DEV-08b4: return/bit source acceptance audit

Audit date: 2026-10-24. Research only; no compiler execution, build, or application edits performed here.

## Source boundary

The [OpenQASM live subroutine specification](https://openqasm.com/language/subroutines.html), inspected on the audit date (no immutable revision supplied by the rendered page), gives X-basis measurement, classical parity on measured inputs, and array-reference examples. Its parity call uses concatenation of separately measured values. The illustrative snippet leaves the constant size and classical declarations incomplete. Array references have distinct aliasing/mutation contracts; success with bit registers does not establish array support.

Local `runtime-return-baseline/xmeasure.qasm` retains the specification's entire `xmeasure` definition unchanged. Its added header, standard-gate include, qubit declaration, explicit output bit, and invocation are an authored executable driver. Call this **unchanged source definition with disclosed driver**, not an unchanged full source program.

Local `runtime-return-baseline/measured-parity.qasm` preserves the parity definition's operations while changing whitespace. It completes the size as `const int n=2`, adds header/include, and substitutes a two-qubit register plus one measured bit register for the source's separate measurements and concatenated call. It adds X preparation on qubit zero and an explicit scalar output. Thus it is an **adapted source fixture**, not acceptance of the source call expression. The expected odd parity is one.

The repository test `computed-result-measured-parity` repeats that adapted driver. Recorded `final-frozen-typed-results.json` reports probability one for result one. This is existing recorded evidence, not a fresh execution by this audit. Historical `requirements.json` failures predate return support and must not be presented as current failures.

## Strongest next acceptance case

Keep the existing parity body, complete n as typed integer constant two, declare separate qubits q/r and separate scalar bits c/c2, and preserve the source's `parity(c ++ c2)` call. Add only header/include, explicit output selection, and clearly labeled state preparation. Test inputs 00, 01, 10, 11: parity respectively 0, 1, 1, 0. Add independent H preparation on both qubits: each parity has probability one half. Export/reimport the same program and verify exact probabilities; retain source bytes through GUI import/history/save.

This directly closes the difference between the tested adapted fixture and the source invocation. **Concatenation at a runtime call is unverified here, not asserted broken.** If it fails, retain the failure as a source-backed regression rather than replacing concatenation with a register. This source case is stronger for DEV-08b4 than another authored scalar-feedback test.

## qBraid boundaries and next unchanged controls

Reuse [PyQASM subroutine tests](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/subroutines/test_subroutines.py) at immutable revision `167cff141b270cae023137971e716d5fec68e9f0`, locally saved as `.tools/runtime-source-test_subroutines.py`:

- `test_function_call_in_expression`: unchanged QASM string checks a Boolean return and broadcast H on four qubits; source asserts four H gates. Good unchanged return compatibility control.
- `test_classical_quantum_function`: unchanged QASM uses compile-time loop arguments and returned integer arithmetic; source asserts five H gates and one X. It is not measurement-dependent runtime evidence.
- `test_function_call_from_within_fn`: unchanged QASM has nested/repeated calls, trailing void returns, and compile-time float parameters/locals. Source asserts three H and three Rx(3.14) operations on qubit one. Preserve this mixed-type compile-time path; replacing floats with integers would invalidate unchanged-source acceptance.

The adjacent qubit-renaming test is skipped upstream for a scope conflict; upstream unrolling is not an infallible oracle. None of these test strings establishes whole notebook or provider workflow acceptance.

[PyQASM Deutsch-Jozsa example](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/examples/unroll_example.py), same revision, keeps measurement after the routine and has compile-time N. Existing source audit also cites [qBraid Algorithms examples](https://docs.qbraid.com/v2/algorithms/user-guide/examples) for generated subroutine usage, not measured activation storage. No new unchanged qBraid lesson requiring runtime bit/return storage was established by this bounded audit.

## Remaining evidence / limits

Run and retain the concatenated source driver plus unchanged qBraid controls, then attach reviewed commit, CI, and released-package evidence. The return release is not proved published by these files. Runtime angle/float formals, array references, and dynamic indexing remain separate DEV-08b5/DEV-06/DEV-08c/DEV-07 tasks. Keep whole qBraid lesson rows open. DEV-08b4 can record bounded source acceptance with explicit fixture boundaries; it cannot certify every subroutine example or the whole parent epic.

## Executed source acceptance (2026-10-24)

The retained `windows/fixtures/runtime-subroutines/measured-parity.qasm` preserves the source parity body (whitespace reformatted) and its `parity(c ++ c2)` invocation. Additions are the OpenQASM header, standard-gate include, typed constant n=2, missing bit declarations, explicit result output, and H preparation on each qubit. The independently expected parity probabilities are 0=1/2 and 1=1/2.

The frozen compiler built from 7d2ec34d (merged as abb947c0) rejects this program with `Failed to parse OpenQASM string`. This is a retained failing acceptance fixture, not a passing regression test. Parsing/concatenated runtime argument support remains to implement; do not replace the concatenation to claim DEV-08b4 complete. The existing returned-register parity test still covers its narrower adapted program.

The unchanged pinned PyQASM `test_function_call_from_within_fn` string also rejects in classical mode: checkpoint9975e211 reports unsupported noninteger classical declarations, while the return candidate reports nonscalar quantum parameters. This comparison does not establish a new classical-import regression. Numerical-mode acceptance and the other unchanged controls remain to test.

## Compatibility extension and executable completion

The [live grammar](https://openqasm.com/grammar/index.html) permits `DOUBLE_PLUS` in `aliasExpression` but omits it from `expression`, whereas the subroutine page uses `parity(c ++ c2)`. Accepting this example is a QuantumStudio compatibility extension, not proof that the reference parser violates its grammar. The extension gives `++` lower precedence than ordinary expression operators; parentheses override this grouping. Concatenation copies values in register index order, with the left operand occupying lower indices. An asymmetric two-bit/three-bit probe checks this project-defined ordering; parity alone cannot distinguish reversed operands.

The [types page](https://openqasm.com/language/types.html) describes uninitialized classical values as undefined. The executable fixture therefore now explicitly initializes the parity accumulator with `bit c = 0`; this addition is disclosed instead of claiming a fully unchanged definition. The invocation and parity operations remain intact. Header/include, typed n=2, missing declarations, output selection and H/H preparation are also additions.

The source compiler prototype accepts the concatenated invocation. Nine exact-worker probes cover four basis inputs, H/H, mixed-width and computed/literal operands, and precedence. These are development checks, not release or full-notebook acceptance. Frozen compiler, GUI export/reimport and final review remain pending.
