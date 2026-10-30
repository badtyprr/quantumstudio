# DEV-08: runtime arrays, iteration and subroutine storage

Status: **released**, 2026-10-30, in [REL-24 / checkpoint `35d9e753`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-35d9e753). DEV-08 is complete for the finite contract below. Whole-source notebook and provider audits remain open.

## Supported contract

Runtime scalar calls preserve independent int/uint/bool/bit, float32/64 and angle
arguments, locals and returned values. Nested and repeated calls, early returns,
missing returns, undefined reads and loop transfers retain activation lifetimes.
Quantum actuals capture physical identities before later actual effects; scalar,
register, sliced and concatenated aliases retain order and collision checks.

Global classical arrays use one to seven dimensions, immutable shape and typed
per-element initialization. Dynamic and negative indices, multidimensional and
nested slices, `sizeof`, readonly/mutable references, fixed shapes and fixed-rank
`#dim` formals share the same backing storage. Mutable references write through;
readonly permission cannot be regained by forwarding. Overlapping mutable actuals
are rejected; overlapping readonly and mixed readonly/mutable actuals are allowed.
Bulk and overlapping slice assignments snapshot the source before writing.

Finite discrete collections retain order and duplicates. One-dimensional arrays,
views, bit registers and bit aliases capture selected values at loop entry into
independent loop bindings. Backing mutations do not change later captured values;
this is the documented product evaluation model. Bit alias geometry is captured
when the alias is declared, and current bit values when iteration begins.

## Sources and independent observations

The source contract and original hashes are in [the research record](DEV-08-research.md).
Pinned PyQASM revision `167cff141b270cae023137971e716d5fec68e9f0` fixtures are retained
unchanged in `windows/fixtures/dev08-numeric-upstream.json`,
`dev08-collection-upstream.json` and `dev08-upstream.json`.

`test-dev08-numeric-source.py` checks the original numeric sources and separate
inverse-state observations using independently rounded IEEE binary32 values.
`test-qasm-runtime-collections.py` preserves the original four-qubit discrete-loop
source, whose expected distribution is uniform over sixteen outputs.
`test-dev08-source-evidence.py` preserves six array/call sources, including unused
uninitialized references. Original sources execute unchanged. Operator witnesses
are separate model copies: computational-basis, plus and plus-i preparations and
independent inverse operators establish ordered operations, not merely zero-state
probabilities. Expected rotations are Rx(10), Rx(14), Rx(3), Rx(18), and the
two-wire float32-return operator described in the research record.

Authored runtime tests separately cover measurement-dependent selectors and
values, typed conversion, mutation, evaluation order, repeated calls, cleanup,
readonly enforcement, physical overlap, undefined elements and finite budgets.
Both exact and sampled engines execute original and exported/reimported models.
The unchanged QB-003 adder and QB-004 generated modules remain package controls;
no fixture is rewritten to remove local storage or inline subroutines.

## Implementation and review

| PRs | Construct |
|---|---|
| #387–#388 | Numeric calls and finite scalar collections |
| #389–#390 | Native typed arrays, model/editor/source integration |
| #391 | Array and bit-register iteration |
| #392–#395 | Native views, protocol, model/editor and source references |
| #396–#397 | Atomic array copies and dynamic collection snapshots |
| #398–#402 | Quantum reference preflight, captured actuals and dynamic aliases |
| #403 | Exact rotation-chain simplification regression |
| #404 | Typed scalar array reads, bracket shorthand and pinned acceptance |
| #405 | Runtime quantum-call loops and bound evaluation order |
| #406 | Classical-bit alias iteration |
| #407 | Declared bit-binding assignment rules and physical-bit budgets |

Every implementation increment received scoped standards/specification review and
required Native, Windows GUI and OpenQASM CI. Findings were resolved before merge;
exact reviewed heads, merge trees and CI links are retained in the external audit.
The release record below identifies the tested revision, artifact digests and
actual editor observations. The superseded ae38807e candidate was withheld after
a bit-binding assignment edge case; #407 corrected it before publication.

## Explicit boundaries

Runtime storage is bounded to 4096 combined scalar/array slots; private snapshots
and identity maps consume that budget. Ranks are 1–7; explicit discrete lists and
physical bit registers are bounded to 64. A `bit` loop binding uses one physical
bit; explicit Boolean/integer bindings use scalar storage and can iterate a full
64-bit register. Existing call depth, expansion,
expression, operation, execution and 256 KiB canonical-document limits compose
across lowered constructs. Saved models and worker protocol versions remain
validated on load; source export retains typed allocations and reference checks.

Complex/duration arrays and unsupported scalar widths remain outside the numeric
engine. Arrays are global allocations, not dynamically sized local allocations.
Classical-bit alias support here is iteration, not general dynamic alias reads or
writes. Existing nested bit-register declaration shadowing remains rejected;
alias-name and scalar loop-binding shadowing are covered. The pinned parser
rejects empty discrete-set syntax; zero-length arrays may iterate zero times.
Whole-notebook, provider and general OpenQASM conformance claims remain separate.

## Released artifact

Published revision: `35d9e753af19372a8f6472404726955eeba2190e`. [Release and downloads](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-35d9e753).

- Windows ZIP SHA-256: `19570252fd8b3719623396c05cff1acba448505c3588d1e293d7cee3a457f798`.
- Source archive SHA-256: `8ce82c2eb015ef2951961d73e161be886ea44448256632a92de9e59d2441877a`.
- All 385 payload files and 386 ZIP entries verified; all 321 required source
  inputs matched byte for byte. Both public downloads matched local hashes and sizes.
- Clean native suite: 67 passes, one existing thread-test skip, zero failures/errors.
  Package gates also passed 2,178 worker, 568 sampling, 71 exact-circuit,
  1,576 classical protocol and 1,910 classical compiler checks.
- All three merged-revision CI checks passed:
  [Native](https://github.com/badtyprr/quantumstudio/actions/runs/41075814804),
  [Windows GUI](https://github.com/badtyprr/quantumstudio/actions/runs/41075814779),
  [OpenQASM](https://github.com/badtyprr/quantumstudio/actions/runs/41075814797).

The immutable-payload audit covers 21 groups. Ten were completed during clean
packaging; eleven additional suites used a frozen copy whose complete file set and
hashes matched the final package manifest. These are check counts, not distinct
source examples or a percentage of OpenQASM conformance.

| Suite | Verified result |
|---|---|
| `quantum-classical-array-request-test` | PASS: 660 runtime array protocol checks. |
| `quantum-classical-array-view-request-test` | PASS: 842 array view protocol checks. |
| `quantum-wire-reference-request-test` | PASS: 256 wire reference preflight protocol checks. |
| `quantum-exact-rotation-chain-test` | PASS: 4 exact rotation cancellation chains. |
| `test-qasm-runtime-numeric-calls` | PASS: 143 runtime numeric subroutine checks. |
| `test-qasm-runtime-collections` | PASS: 376 runtime collection checks. |
| `test-qasm-runtime-arrays` | PASS: 430 runtime array source checks. |
| `test-dev08-numeric-source` | PASS: 53 pinned numeric-call source checks; separate inverse witnesses cover zero-input states. |
| `test-dev07-source-evidence` | PASS: 40 pinned DEV-07 checks; unmeasured state uses a separately labeled inverse witness; loop-local quantum alias calls included. |
| `test-runtime-array-model` | PASS: 60 runtime array model checks. |
| `test-qasm-runtime-array-copies` | PASS: 188 runtime array copy source checks. |
| `test-runtime-wire-reference-model` | PASS: 129 wire reference model/source checks. |
| `test-qasm-runtime-dynamic-collections` | PASS: 241 dynamic array iteration checks. |
| `test-runtime-scalar-quantum-bindings` | PASS: 107 scalar quantum binding checks. |
| `test-qasm-runtime-array-views` | PASS: 492 runtime array view source checks. |
| `test-runtime-quantum-register-views` | PASS: 169 quantum register view checks. |
| `test-runtime-quantum-call-loops` | PASS: 252 runtime quantum call-loop checks. |
| `test-runtime-dynamic-quantum-aliases` | PASS: 258 dynamic quantum alias checks. |
| `test-runtime-array-view-model` | PASS: 65 array view model checks (source reimport still pending). |
| `test-runtime-bit-alias-iteration` | PASS: 274 classical-bit alias iteration checks. |
| `test-dev08-source-evidence` | PASS: 204 pinned DEV-08 checks; operator witnesses use separate model copies. |

The actual packaged GUI passed import/edit/export, rejected-export file preservation,
history and save/reopen for three authored drivers: measured float/angle calls,
measurement-selected mutable array references, and bit-alias/array/discrete
iteration snapshots. Original and two exported forms passed both engines.
Separate observations on copies of the edited saved models confirmed integer
cell 7 and float32 cell 16777216. All 26 execution checks passed.

Eleven captures were visually inspected: array targets; float32 views/copy at
normal and minimum size; quantum-reference controls; the three drivers at normal
size and their rejected-export states; and iteration at minimum size. Long
programs scroll; controls and text remained legible. Screenshots support layout
observations; execution and file-preservation checks supply semantic evidence.

Full manifests, logs, source hashes, exact reviewed heads, GUI models/captures and
download verification are retained outside disposable clones in `cleanup-audit/`.
The release audit is `dev08-release-audit/audit.json`; the GUI record is
`dev08-release-editor/editor-audit.json`; publication is `dev08-release.json`.
