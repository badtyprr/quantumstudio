# DEV-06 runtime parameter source audit

## Scope and provenance

This audit pins qBraid PyQASM revision
[`167cff141b270cae023137971e716d5fec68e9f0`](https://github.com/qBraid/pyqasm/tree/167cff141b270cae023137971e716d5fec68e9f0).
The fixture manifest is `windows/fixtures/dev06-upstream.json`; each entry records
its original path, literal start line, unchanged UTF-8 source value and SHA-256.
Leading/trailing whitespace is retained. Python AST parsing normalizes source-file
newlines to LF; extraction never strips or dedents the string. The adjacent
`pyqasm-LICENSE.txt` retains the upstream Apache-2.0 license.

`windows/test-dev06-source-evidence.py --upstream <checkout>` verifies the checkout
revision and re-extracts every original AST string. Ordinary CI verifies the stored
hashes, source/frozen imports, canonical save/load and export/reimport. Packaging
also runs both execution modes and the independent references described below.
This is a selected source audit, not a claim that the complete upstream test suite
or an IBM/qBraid lesson notebook is supported.

## Unchanged accepted examples

| Fixture | Original source | Independent expected behavior |
| --- | --- | --- |
| broadcast-u3 | [test_gates.py:201](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L201) | U3(.5,.5,.5) on both qubits |
| controlled-u3 | [test_gates.py:216](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L216) | Full controlled U3 matrix, including the active-control columns |
| global-phase | [test_gates.py:263](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L263) | exp(i*pi/4) times identity |
| powers | [test_gates.py:388](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L388) | inv(H^8), then H^-2, giving identity |
| inverses | [test_gates.py:403](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L403) | Ordered H, Y, Rx(-.5), S-adjoint, CX and CCX |
| negative-control | [test_gates.py:655](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L655) | diag(1,1,-1,1), basis order q1q0 |
| controlled-global-phase / phase | [test_gates.py:769–780](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_gates.py#L769) | Both unchanged literals produce diag(1,exp(i)) |
| angle-bits | [declarations/test_classical.py:771](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/declarations/test_classical.py#L771) | Six stored angle patterns: 0100, 01111000, 1100, 1000, 01100000, 00100000 |
| integer-casts | [resources/variables.py:392](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/resources/variables.py#L392) | x=-3, b=true, ux=253, float32 f=-3, output bits1101 |
| float-casts | [resources/variables.py:416](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/resources/variables.py#L416) | Binary64 f=1.5585244804918115 (bits3ff8efb75d9ba4be), b=true, i=u=1 |

There are eleven accepted programs. The scalar cast literals are the original
`CASTING_TESTS` entries used by the upstream `test_explicit_casting` test. The
commented angle conversion in the float fixture remains commented and supplies
no angle-cast coverage.

## Reference method and adaptations

The gate oracle constructs small dense matrices directly from the standard U3,
phase, Pauli and controlled-gate equations. It does not call PyQASM decomposition
or derive expected gates from QuantumStudio's output. Every matrix entry is
compared, with global phase retained, at absolute tolerance 2e-12. Wire0 is the
least-significant basis bit; the first wire of a local gate is its most-significant
local bit. Candidate matrix entries are evaluated by the worker and embedded in
source order. This checks all basis columns, including controls inactive on |0>.

The original unchanged circuit also executes in exact and sampled modes. Export
adds explicit zero initialization. For the exported matrix comparison, the harness
asserts and removes only that leading reset sequence and compares the remaining
unitary suffix; it separately executes the entire exported program. It does not
claim that a resetting exported program is a unitary on arbitrary initial states.

Declaration-only sources have no public output. Their unchanged programs execute
first. A separately labeled observer then appends equality readouts to a **copy of
the imported model**, comparing each final stored scalar with independently stated
integer/IEEE values. Source bytes are never modified. Observer export/reimport and
both engines are checked separately; empty-output success alone is not the value
oracle. Exact probabilities are numerically evaluated for these comparisons at
1e-12 tolerance; sampled deterministic outputs require all10000 shots.

These source examples demonstrate static gate and scalar behavior. Authored
`test-qasm-runtime-numeric.py`, `test-qasm-runtime-gates.py` and native numeric
regressions separately cover measurement feedback, runtime mutation, typed math,
precision boundaries, odd 64-bit angles, errors and controlled published-U phase.
They are not relabeled as unchanged upstream examples.

## Preserved exclusions

Four additional unchanged sources remain expected rejections, with pinned hashes
and matching source/frozen diagnostics:

- Custom-gate body parameter expression, test_gates.py:138: runtime arguments to
  user-defined gates are outside the supported primitive-gate path.
- Scalar implicit casts, declarations/test_classical.py:156: float-to-integer
  assignment needs an explicit numeric cast in the supported runtime subset.
- Bool_test, resources/variables.py:372: widening Boolean-to-bit casts are outside
  the existing one-bit conversion contract.
- Generated `sin(1.0);` expression statement, test_expressions.py:128: PyQASM1.0.4
  does not support the discarded built-in function statement. The manifest stores
  the unchanged upstream JoinedStr with its original parameter. Runtime sin used
  in a supported numeric assignment is covered by authored tests; this source
  rejection is not reported as math-example acceptance.

The official iterative phase-estimation example's uninitialized angle feedback,
angle-bit assignment and power512 are also outside the finite DEV-06 contract.
Runtime subroutine activation parameter forms remain DEV-08b; dynamic wire indices
remain DEV-07. See `runtime-numeric-protocol.md` for the implemented value contract.

## Acceptance status

The implementation is split across DEV-06d gate coverage (#379), DEV-06e native
values (#380), and DEV-06e application integration (#381). This evidence increment
adds source hashes, independent references and automated package checks. Reviewed
head, CI and final released revision will be reconciled after the clean merged-tip
package and payload GUI audit. DEV-06 is not marked complete by this document alone.
