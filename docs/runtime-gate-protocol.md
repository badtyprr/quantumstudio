# Runtime parameterized gates

DEV-06d extends the existing finite binary64 runtime expressions to P, global
phase, controlled Rx/Ry/Rz/P, U3 and the published OpenQASM U convention.
This increment does not complete DEV-06e numeric storage or DEV-06f source audits.

Parameters are evaluated once in their written order, then the integer power is
evaluated. This happens even for power zero. Undefined reads, nonfinite arithmetic
and powers outside -64 through 64 fail the run without partial results. Integer
arithmetic retains its existing width and overflow rules before real conversion.
Fractional powers and runtime control counts are unsupported.

Controls occupy the leading wires, most significant first. Control state is an
unsigned bit pattern of exactly that many logical bits; 0 selects a negative
control. The total is at most three wires. P is diag(1, exp(i theta)); global phase
has no target wires. Its controlled form applies exp(i theta) only to the selected
control state. U3 has parameters theta, phi, lambda in that order. Published U
is exp(i theta/2) times U3. Integer powers apply the whole unitary, preserving
phase; they do not scale all three U parameters.

The exact engine uses dyadic rational representations of the evaluated doubles.
It validates a single application and repeats it for the absolute power, using
the inverse for negative powers. This avoids requiring symbolic certification of
an expanded matrix power. Sampling applies the corresponding complex matrix.
Both modes retain the existing cancellation and resource limits.

## Worker encoding

`QEXACT11` and `QSAMPLE12` extend the previous headers without changing their
declarations, budget, outputs or existing operations. Operation 17 is:

```text
17
wire count
wire indices, in order
kind
control count
control state
parameter count
parameter expression trees, in order
integer power expression tree
```

Kinds 0–6 mean Rx, Ry, Rz, P, global phase, U3 and published U. The first five
require one real expression; U3 and published U require three. The wire count is
control count plus one, except for global phase, which has only controls.
Existing real/integer expression encodings and bounds are unchanged. Older
headers reject operation 17, and trailing data remains invalid.

## Saved circuits and editor

Circuit version 12 adds `Kind: ParameterGate` with a `ParameterGate` object:
`Gate`, `Controls`, decimal-string `ControlState`, ordered `Parameters`, and
integer-expression `Power`. `Wires` lists controls before the target. The model
rejects inconsistent metadata, unknown fields and unrelated operation fields.
Version 11 rotations remain supported without migration.

The runtime gate editor exposes each U parameter, control-state pattern and
integer power. Selection, replacement, invalid edits, undo/redo and save/reopen
are tested. Export uses explicit modifiers and U3; published U adds an explicit
controlled phase so re-importing under either U convention retains its meaning.
Import broadcasts static wire selections lane by lane, checks size agreement and
wire collisions, and preserves runtime expressions rather than compiler initial
values. Runtime custom-gate/subroutine parameters remain explicitly unsupported.

## Regression locations

- `src/quantum-runtime-gate-test.cc`: native matrices, controls, inverse, powers,
  runtime values, validation and exact/sample interference.
- `src/quantum-runtime-gate-request-test.py`: protocol and malformed inputs.
- `windows/ClassicalCircuitTests.cs`: strict model, versions and serialization.
- `windows/test-qasm-runtime-gates.py`: import/export/save/reopen, feedback,
  analytic probability references and both U conventions in both engines.
- `windows/ClassicalProgramWindow.cs`: editor interaction and normal/minimum-size
  captures through the existing classical editor verification entry point.

The authored probes verify these semantics; they are not unchanged lesson evidence.
