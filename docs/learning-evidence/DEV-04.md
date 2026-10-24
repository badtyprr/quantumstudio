# DEV-04: explicit operator properties

Status: released in [checkpoint-a1d85f61](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-a1d85f61), revision `a1d85f61fe64ef1224ba7a0ef494e560b9b19d66`. This completes the explicit DEV-04 acceptance criteria, not the broader IBM/qBraid coverage goal.

## Source and scope

IBM Quantum Learning defines a square unitary operator by U†U = UU† = I in [Unitary operations](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/quantum-information#unitary-operations). Its [Projection matrices](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/inner-products-and-projections#projection-matrices) section uses Hermitian, idempotent projectors.

These definitions justify local conditional rewrites. Preserving the premise after simplification is a QuantumStudio engineering requirement: a copied identity must still reject a later invalid substitution. This is an adapted symbolic acceptance fixture, not an end-to-end lesson compatibility claim.

## Reproduce

In Quantum notation, open Matrices and declare A with Rows = n, Columns = n, Property = Unitary. Enter `A†A`. The result displays I_n with its unitary premise, and canonical copy retains `qunitaryidentity`. Change the property to Hermitian and enter `A†`; change it to Projector and enter `A*A`. Both return the declared A.

Backend regression examples:

- `operatorassume(adjoint(A)*A,A,2,unitary)` retains a guarded identity.
- Substituting `[0,1;1,0]` is valid; `[1,0;0,2]`, a rectangular matrix, or an identity of the wrong dimension is rejected.
- `operatorparam(A,2,projector)*operatorparam(A,2,projector)` reduces to the declared projector.
- Unrelated projector products and generic Hermitian squares are not given extra identities.
- `adjoint(operatorparam(A,2,unitary))*matrixparam(B,2,2)*operatorparam(A,2,unitary)` does not cancel across B.

## Implementation and validation

- [#360](https://github.com/badtyprr/quantumstudio/pull/360): property domains and concrete substitution validation.
- [#361](https://github.com/badtyprr/quantumstudio/pull/361): guarded identities and conservative local rewrites.
- [#362](https://github.com/badtyprr/quantumstudio/pull/362): property editor, scoped declarations, and version 4 workspace/history storage.
- Automated coverage: `src/quantum-algebra-test.cc`, `src/quantum-worker-test.py`, `windows/MatrixDeclarationsTests.cs`, `windows/SessionStoreTests.cs`, `windows/MatrixDeclarationsGuiTests.cs`.
- Pre-release local validation: 1,992 worker checks, 60 declaration checks, 67 session checks, full GUI suite, actual dropdown selection, natural calculation, guarded copy, session/history roundtrip, normal/minimum captures.
- Review: two domain self-review rounds, two identity self-review rounds, one editor self-review round; no outstanding findings. Required exact-head CI passed before each merge.

## Released artifact

[Download Windows x64 ZIP](https://github.com/badtyprr/quantumstudio/releases/download/checkpoint-a1d85f61/QuantumStudio-Windows-x64.zip). Extract the entire archive and run QuantumStudio.exe.

ZIP SHA-256: `1cb453630fb0a2798860f8c481b2b6b5608276782666f9105b32c305d007c488`.

The merged-tip package pipeline passed: 57 native tests (56 passed, one existing thread-test skip, zero failures/errors), full GUI checks, 1,992 worker checks, 568 numerical sampling checks, 71 exact-circuit worker checks, 1,576 classical-expression checks and 1,400 classical-expression import checks. The packaged operator-property GUI probe passed dropdown selection, natural calculation, guarded copy, save/reopen and history restoration. Normal and minimum editor captures and the main workspace smoke capture were visually inspected. All 340 payload files and 341 ZIP entries were hash-verified; the uploaded asset digest and size match the tested archive.

Merged-tip CI:

- [Windows GUI build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40089990308/job/120860538195): passed.
- [Windows OpenQASM build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40089990333/job/120860538174): passed.
- [Native build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40089990347/job/120860538072): passed.

Versions 1–3 remain readable; older builds reject version 4 sessions. Broader lesson audits and external qBraid/provider compatibility remain separate checklist items.
