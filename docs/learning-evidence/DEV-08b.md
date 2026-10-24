# DEV-08b: runtime subroutine activations

Status: **partial**, with scalar runtime calls released in [checkpoint-96595d01](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-96595d01). This does not complete DEV-08b or any whole IBM/qBraid source row.

## Source and scope

The [OpenQASM subroutine specification](https://openqasm.com/language/subroutines.html) motivates measured classical arguments, local storage and returned values through its parity example. Its array section additionally specifies reference and mutation rules. Scalar void calls alone cannot run that full example. The specification presents illustrative fragments, so completing declarations or initialization for an executable fixture must be disclosed rather than called unchanged source acceptance.

A bounded audit of qBraid examples did not establish an unchanged learning fixture requiring this runtime scalar subset. The [pinned PyQASM subroutine tests](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/subroutines/test_subroutines.py) include nested calls, but those inspected use compile-time arguments. Existing [QB-004 evidence](QB-004.md) remains separate.

The released engineering fixture adapts the measured-argument pattern: measure a Hadamard-prepared qubit, pass the result as an integer to `feedback`, copy it to a local, mutate the formal, and conditionally apply X using the saved local. Nested `pair` calls test that inner mutation does not change the caller's argument; repeated calls and a same-named outer local test activation isolation. Four output bits must be `1000` and `1011`, each with probability 1/2. This is authored test code, not an unchanged notebook.

## Supported behavior and regression coverage

- Standalone void calls with runtime int/uint/bool arguments capture values before the body runs. Scalar qubit arguments use a scalar or literal-indexed reference; overlapping qubits are rejected.
- Nested/repeated calls, scalar local shadowing, runtime-loop reinitialization and lexical constant/width binding have regression coverage in `windows/test-qasm-classical-expressions.py`.
- Undefined integer reads remain errors. Recursive/excessive expansion, unsupported arguments, annotations and invalid visibility are rejected explicitly.
- `windows/ClassicalProgramQasmTests.cs` covers mid-body and repeated local lifetimes, undefined locals, interleaved declarations and input immutability. Crossing/escaped lifetimes and excessive nesting are rejected.
- Export reconstructs only proven scopes on a copy. The existing path remains first; export does not modify the saved circuit or replace undefined values with zero.

Remaining work is prioritized as DEV-08b2–b5 in the [development checklist](../learning-coverage-checklist.md#dev-08): bit-register arguments/local storage, returned values and early return, source acceptance, and other parameter forms. Runtime arrays/dynamic indexing remain coordinated with DEV-08c/DEV-07.

## Implementation, review and CI

[PR #364](https://github.com/badtyprr/quantumstudio/pull/364), reviewed head `8219651c0a861f1d2e3aac685fa9171e6f49371c`, merged as `96595d01864935dafc9ddc62e09770f4cfe2f10a`. Actual merge parents and tree were verified; the branch was deleted. Four scoped self-review rounds resolved two high-severity and three medium-severity findings, with none outstanding. This was not independent review.

Required reviewed-head checks: [native](https://github.com/badtyprr/quantumstudio/actions/runs/40096173970/job/120878852905), [GUI](https://github.com/badtyprr/quantumstudio/actions/runs/40096174044/job/120878797676), [OpenQASM](https://github.com/badtyprr/quantumstudio/actions/runs/40096173983/job/120878814809). All three also passed on the merged tip.

## Released artifact

[Download Windows x64 ZIP](https://github.com/badtyprr/quantumstudio/releases/download/checkpoint-96595d01/QuantumStudio-Windows-x64.zip). Extract the entire archive and run `QuantumStudio.exe`.

- Revision: `96595d01864935dafc9ddc62e09770f4cfe2f10a`.
- SHA-256: `031f7c53b3eae58ec1c6f1c2d7ea18c00750bcb401802c09504bb376ea338008`.
- Native package tests: 56 passed, one existing thread-test skip, zero failures/errors.
- Package checks: 1,992 worker, 568 sampling, 71 exact-circuit, 1,576 classical-expression and 1,458 compiler checks passed. Export validation passed 35 cases, 13 expected rejections and 105 compiler/exact/sample checks.
- Actual packaged GUI export/reimport, file preservation, source/history and save/reopen checks passed. Exported feedback retained the exact expected distribution. Normal, minimum-size and rejection captures were inspected.
- All 340 payload files matched the manifest and tested ZIP; all 341 ZIP entries were verified. GitHub's uploaded asset hash and size matched. No rebuild occurred between testing and publication.
