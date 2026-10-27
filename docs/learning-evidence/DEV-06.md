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

## Reviewed implementation and released acceptance

| Increment | PR | Reviewed head | Merge |
| --- | --- | --- | --- |
| Broader gates | [#379](https://github.com/badtyprr/quantumstudio/pull/379) | `0f6ac6b5e2bc23fa26eecfdf1913ac5cf16b018d` | `44d7bddabf8c2249a90317a8f59ea7f0ff7c1436` |
| Native numeric core | [#380](https://github.com/badtyprr/quantumstudio/pull/380) | `bc6ef112dbe67d4e59622b298a773590131350f1` | `6c1f6050a28c5ed87a5d37528738b20a4f6734ac` |
| Application integration | [#381](https://github.com/badtyprr/quantumstudio/pull/381) | `eadc0a43fed6e98f0132b22b95d7dc78c0806d45` | `b0befb7c0e5293f816d1b6cd27409ad975420833` |
| Pinned source audit | [#382](https://github.com/badtyprr/quantumstudio/pull/382) | `988745b703dccc151cec5df0cc5a4ec6448ce2f6` | `1666b09a4e326f6b30a8df6aa33b11ad1ead0424` |

Released [checkpoint 1666b09a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-1666b09a) from `1666b09a4e326f6b30a8df6aa33b11ad1ead0424`. ZIP SHA-256
`d9679429503ed9a08e981b25ad1f53f42360696b0ca1b77300e3436387635c26`. The clean source checkout produced the package and source archive;
the manifest, extracted payload and uploaded asset hashes match the tested files.
The [source archive](https://github.com/badtyprr/quantumstudio/releases/download/checkpoint-1666b09a/QuantumStudio-source.tar.gz) has SHA-256
`53bfe29e0e114ceab027b449676f3fa68fd083f20e341580dcd1931d55c3bd40`.

- [Native build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40448000042/job/122003755119): passed on the merged release revision.
- [Windows GUI build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40447999974/job/122003754564): passed on the merged release revision.
- [Windows OpenQASM build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40448000106/job/122003755037): passed on the merged release revision.

Exact-head Standards and Spec reviews have no outstanding findings. Review found
and resolved numeric condition/cast routing issues and two source-oracle gaps;
the final oracle independently pins declaration schemas and operator dimensions.

The clean build passes 61 native tests with one existing thread skip and no
failures/errors; all 285 required source inputs match the generated archive. The
portable worker passes 2,178 process checks. The released payload passes 340 numeric protocol, 197 gate protocol, 337 numeric
import/model/export and 128 pinned-source checks. A separate local extraction run
passes 143 checks, including all fifteen original source re-extractions. Nine
editor-created save/load/execution checks pass against the packaged worker. Five
actual-payload screenshots verify numeric declarations, numeric assignment and
controlled multi-parameter gate editing at normal/minimum window sizes. The full
package workflow also runs existing native, worker, importer, export and GUI gates.

DEV-06d/e/f and their parent are complete for this finite contract. The exclusions
above remain explicit; this release does not complete an entire IBM/qBraid notebook,
all OpenQASM constructs, DEV-07 or the remaining DEV-08b parameter forms.
