# DEV-08b4: return/bit source acceptance audit

Initial research audit: 2026-10-24. The chronological sections below retain the initial failures and candidate evidence; the final release section records the subsequently verified result.

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

The source compiler prototype accepts the concatenated invocation. Nine exact-worker probes cover four basis inputs, H/H, mixed-width and computed/literal operands, and precedence. These are development checks, not release or full-notebook acceptance. At implementation commit `979447eb`, the frozen compiler passed the same nine exact-worker probes, and 12 parser controls checked aliases, comments, strings, precedence, parentheses and malformed syntax. Two candidate-GUI export/reimport checks retained source/history/save behavior and matched four original/exported distributions (parity: one half each; asymmetric concatenation: 10110 with certainty). The mixed-width GUI fixture adds an unused qubit required by the existing export test harness; its initial harness rejection is not counted as a successful test. Six normal/minimum/rejected screenshots were inspected. The candidate combines the published `9975e211` GUI/worker with the new frozen compiler; it is not a released package. Final exact-commit review, CI and release remain pending.

## Released bounded source acceptance (REL-19)

PR [#368](https://github.com/badtyprr/quantumstudio/pull/368), exact reviewed head `a0dbb22158b771746fa9f4b353d6cf4999674f5e`, merged as `3663fa58cb17965b8d3c65da1a00340748bc1404`. Actual merge parents/tree and fresh remote master were verified; the merged branch was deleted. All three required Native/GUI/OpenQASM checks passed on the reviewed head and merged tip. The [published Windows checkpoint](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-3663fa58) is the exact tested ZIP.

Separate Standards and Spec reviews covered two scoped change rounds and final integration confirmation (three rounds). Initial Native CI found one high source-distribution omission: the new parser and two fixtures were absent from the source archive. The manifest fix passed 260 byte-for-byte archive input checks. Final Standards review found no documented-standard breaches and deferred one minor duplicate-test heuristic; final Spec review had no findings. No correctness finding remained open.

The clean release package passed 1,992 worker checks, 1,648 compiler checks and native tests (56 passed, one existing thread skip, zero failures/errors). Two actual GUI export/reimport checks covered measured parity and asymmetric bit ordering; four original/exported exact distributions matched the independently expected one-half/one-half parity and certain 10110 result. Six normal/minimum/rejected screenshots were inspected. Source bytes, history and save/reopen checks passed.

Three unchanged QASM literals from pinned PyQASM `167cff141b270cae023137971e716d5fec68e9f0` were statically extracted and tested against the released compiler. Numerical output matched both the earlier frozen compiler and the upstream gate/wire/angle oracles: `test_function_call_in_expression` (four H), `test_classical_quantum_function` (five H and one X), and `test_function_call_from_within_fn` (three H and three Rx(3.14) on qubit one). Their three existing classical-mode rejections also matched. These are compiler/oracle checks, not Python, notebook, provider or simulator execution of the unchanged programs.

The measured-parity fixture remains an executable completion with disclosed header/include, n=2, declarations/output, H/H preparation and explicit zero initialization of the accumulator. Its source invocation and parity operations are retained. The asymmetric GUI fixture adds an unused qubit for the existing export harness. Concatenation remains a documented extension of the reference expression grammar, bounded to explicitly sized bit values and at most 64 total bits, with the left operand in lower register indices.

This completes the bounded DEV-08b4 audit. Quantum-register/array parameters, dynamic quantum indices, runtime float/angle forms, complete source-example acceptance and whole notebook rows remain open. The prior release's intermittent export replacement IOException remains an unresolved reliability follow-up; the passing identical retry is not a root-cause fix.

All 340 payload hashes and archive contents matched; the uploaded digest, size and release tag were verified. ZIP SHA-256: `6511b256872342df2ab5be0374e889bc9b0537625177e1e15598b509b2dca63c`.
