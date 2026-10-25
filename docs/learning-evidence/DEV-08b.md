# DEV-08b: runtime subroutine activations

Status: **partial**, with scalar runtime calls released in [checkpoint-96595d01](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-96595d01), bit arguments/local storage in [checkpoint-9975e211](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-9975e211), and typed returns/early exits in [checkpoint-abb947c0](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-abb947c0). This does not complete DEV-08b or any whole IBM/qBraid source row.

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

Remaining source acceptance and parameter work is prioritized as DEV-08b4–b5 in the [development checklist](../learning-coverage-checklist.md#dev-08): complete source acceptance and other parameter forms. Bit-register storage and integer/Boolean/bit returns are now released; floating-point/angle returns remain open. Runtime arrays/dynamic indexing remain coordinated with DEV-08c/DEV-07.

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

## Bit and return release evidence (REL-17 / REL-18)

PR [#366](https://github.com/badtyprr/quantumstudio/pull/366) merged as `9975e211e3fcabcac501fe1ae87f3a609957bca0`. Two scoped self-review rounds resolved one medium and one minor finding. The released package passed 1,504 compiler checks, two GUI exports and four exact input/export distributions, including nested bit activations and repeated-loop initialization. Six captures were inspected. All 340 payload hashes and 341 ZIP entries matched; the uploaded asset digest was verified. ZIP SHA-256: `6e25ed7b7d06c13cb2a0d8a164a75ae1137d8acdb80fabbd8d653fa15b21ba62`.

PR [#367](https://github.com/badtyprr/quantumstudio/pull/367), reviewed head `7d2ec34d5dabf83ea83614f6f67fef7124a6a443`, merged as `abb947c0e45219b2511cd42b334b5570025d7567`. Five scoped self-review rounds resolved one high and three medium findings, with none outstanding. These were self-reviews, not independent reviews. Actual merge parents/tree and branch deletion were verified. All three required reviewed-head and merged-tip CI checks passed. The immutable package passed 1,608 compiler checks; three actual GUI exports and six exact original/exported distributions covered measurement returns, repeated while-condition calls and returned range bounds. Nine normal/rejected/minimum captures were inspected. The initial returned-range GUI run failed with an IOException replacing an existing export; an identical targeted rerun on the same package, fixture and destination passed. The original failure is retained; its cause is unconfirmed. All 340 payload hashes and 341 ZIP entries matched. Uploaded asset digest/size and tag were verified. ZIP SHA-256: `802ad97058b477ee8a2fbc5e805d315ad6304b385c2cfe42ba2ce77498ed1065`.

Both packages passed 1,992 worker checks and native tests (56 passed, one existing thread skip, zero failures/errors). Each published ZIP is the exact tested artifact, without rebuilding after validation.

The return release supports int/uint/bool/bit results, measurement returns, missing-return errors even when discarded, nested calls, short-circuit effects, returned loop conditions/bounds and void early returns. Quantum-register/array parameters, computed quantum indices, runtime floating-point/angle returns and full source-example/notebook acceptance remain open. The measured-parity concatenated invocation requires separately reviewed compatibility work; the adapted released register fixture does not establish that source-call acceptance. Keep DEV-08b, DEV-08b4 and whole IBM/qBraid rows open.

Open reliability follow-up: diagnose the intermittent existing-destination export replacement failure. The targeted passing rerun permits recording the successful artifact checks but does not prove the failure mechanism repaired. Preserve the failing export report when investigating file contention or filesystem behavior.
