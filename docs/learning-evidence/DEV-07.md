# DEV-07: bounded runtime wire selection

Scalar integer indices now select wires from declared registers and fixed aliases
at execution time. Both engines check bounds and physical operand collisions;
measurement and reset retain their existing semantics. Source diagnostics preserve
file/line context. The editor, model14 and export retain selections and their error
behavior. See [the finite contract](../runtime-wire-protocol.md).

## Source and reference evidence

[Research and primary sources](DEV-07-research.md) retain the pinned PyQASM revision
`167cff141b270cae023137971e716d5fec68e9f0`. Exact source bytes and SHA-256 values are in
`windows/fixtures/dev07-upstream.json`; the upstream license is retained alongside.
REL-22 rejects the first three programs as unsupported runtime quantum targets.

- `test_while_loop_with_continue`: H on q0 and q2 gives 000/001/100/101, each 1/4.
- `test_while_loop_with_break`: H on q0 gives 000/001, each 1/2.
- `test_while_loop_unroll_qasm_output`: H0,CX01,H1,CX12,H2,CX23. The unchanged
  source has no outputs. Separately appending the independently derived inverse
  and terminal measurements to a copy of its model verifies the pure state up to
  global phase; empty output alone is not used as state evidence.
- `test_alias_arg_from_loop_validates` remains a documented rejection control for
  dynamic alias/subroutine binding; it is not counted as accepted source coverage.

`windows/test-dev07-source-evidence.py` checks source/frozen parity, original and
exported execution, and separate state witnesses. The local extraction run has
35 checks including four upstream byte re-extractions; the package run has 31.
`windows/test-qasm-runtime-wires.py` has 270 checks, including measured feedback,
fixed alias order, negative/large/undefined indices, collisions, reset, measurement,
invalid models, source-local included-file errors and raw-model export validation.
These authored probes are separate from unchanged-source acceptance.

## Review and release

| Increment | PR | Reviewed head | Merge |
| --- | --- | --- | --- |
| Native resolver/protocol | [#384](https://github.com/badtyprr/quantumstudio/pull/384) | `647261d624a1c719d88cc74b2047876511f8920b` | `04ea756782e25610e3b086b5a5c9e2d946423a4d` |
| Application and source evidence | [#385](https://github.com/badtyprr/quantumstudio/pull/385) | `29dd447b8891d0225436cf2c37c2dd2ee2623f1d` | `afca2fe60c5523401fd6061596493b28ad7abc70` |

Released [afca2fe6](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-afca2fe6) from `afca2fe60c5523401fd6061596493b28ad7abc70`. ZIP SHA-256 `7a6224e40467616fe1ca9b65cd556f2d368afcf34dda78c155a19308c9d10deb`.

- [Native build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40459358149/job/122040041571): passed on the merged release revision.
- [Windows GUI build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40459358174/job/122040041544): passed on the merged release revision.
- [Windows OpenQASM build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40459358172/job/122040040812): passed on the merged release revision.

Both exact-head reviews have zero outstanding findings. Review resolved legacy
conditional-child inconsistency and scalar-phase/decomposed export losing selector
validation. The final export preflights operands in order before decomposition.

The clean package has 62 native passes, one existing thread-test skip and zero
failures/errors. Its workflow also runs worker, compiler, model, export and GUI
checks. The immutable payload audit repeats 280 wire protocol checks, 270 wire
roundtrip checks, 31 pinned-source checks and 12 editor-created execution checks,
alongside numeric/gate regression checks. Seven captures cover runtime selectors,
numeric declarations and controlled gate editing at normal/minimum sizes. All
manifest entries, the extracted payload, ZIP and uploaded assets are hash-verified.

Finalization initially stopped after all tests passed because the last GitHub fetch
could not resolve its hostname. Connectivity recovered; the reviewed source-check,
manifest and archive tail was resumed, with all tested payload hashes unchanged.
An initial recovery helper selected an older PowerShell; using the build runner
resolved that tooling issue. Original failure and recovery logs are retained.

## Explicit limits

Dynamic alias creation, runtime-selected subroutine actuals and remaining parameter
forms stay DEV-08b work. Runtime-sized slices/sets, negative-relative indices,
dynamic classical destinations and dynamic barriers are unsupported. Existing
fixed whole-register subroutine parameters may use scalar runtime indices inside
their body. This milestone does not claim all OpenQASM constructs or completion
of an entire IBM/qBraid notebook.
