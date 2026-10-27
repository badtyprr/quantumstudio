# Runtime wire selection (DEV-07a)

This increment supplies the native execution and worker protocol seam. Importer,
saved-document/editor integration, source-example acceptance and release remain
required before DEV-07 is complete.

`QuantumClassical::WireSelection` owns one to three ordered targets. Each target
contains a fixed list of 1–25 physical wires and a typed integer expression. The
list represents register/alias order, including noncontiguous selections. Index
expressions reuse the existing 32-level/512-node, typed storage and arithmetic
rules. They may read measured bits and scoped variables.

At each reached operation all indices read the same pre-operation classical
state. Negative values and indices at least the target list length are rejected;
there is no narrowing to a machine wire number before bounds checking. Resolved
physical wires must be distinct across operands. All resolution completes before
the operation changes quantum state or measurement memory. Untaken branches do
not evaluate indices; their expression references and candidate maps are still
validated. Errors abort the run without returning partial counts/probabilities.

Nonnegative indices match the existing pinned compiler subset. This is a product
limitation: OpenQASM's register slicing examples also include negative indices.
It is not a claim that all negative indexing is invalid in the language.

The exact and sampled engines share the resolver. Gates, channels, rotations,
parameterized gates, measurements and resets accept selection. Readout and
classical storage operations do not. Conditions use an explicit branch containing
the selected operation; wrapping the legacy conditional opcode is rejected by
both engines. The exact phase shortcut declines selected
operations and uses the general evaluator. Static operations keep their existing
representation and protocol behavior.

## Wire encoding

`QEXACT13` and `QSAMPLE14` extend the numeric protocol with operation 20:

```text
20
source_utf8_byte_length (1..512)
source_bytes (no terminator)
target_count (1..3)
repeat target_count:
    candidate_count (1..25)
    candidate_wire (repeated candidate_count; each in quantum register)
    typed_integer_expression (existing prefix encoding)
quantum_operation (existing operation encoding, local wires 0,1,...)
```

Source bytes are diagnostic context and never evaluated. The operation must use
local ordinal targets and have the same arity as the selection. Nested selectors
and non-quantum child operations are rejected. Wrapper and child both count
toward the existing request step budget; nesting is checked before decoding.
The selection is stored directly on the native operation, not interpreted as a
runtime control-flow block. Existing protocol versions reject operation 20.

`src/quantum-wire-selection-request-test.py` compares exact probabilities and
sampled results for mutation, measured feedback, alias ordering, dynamic reset,
measurement destination overwrite, controlled gates and runtime parameters. It
also checks undefined/negative/large indices, divide-by-zero, operand collisions,
untaken branches, invalid maps/arity/operation kinds, truncation and old versions.

## Application contract (model 14)

The classical importer accepts scalar integer wire indices into declared registers
and existing fixed aliases, including ordered static sets and slices. Gates,
measurement sources and reset resolve the selection at each executed operation.
All broadcast lanes are preflighted before effects. Bare Boolean and floating
indices are rejected; explicit integer casts use the existing typed arithmetic.
Negative indices are outside this product subset, including negative-relative
alias indexing shown in some OpenQASM examples.

Model 14 stores `WireTargets` (ordered `Candidates` and typed `Index`) and
`WireSource` on quantum steps. `Wires` contains local ordinals. Imported source
bundles map diagnostics back to their original file and position. The editor
shows `q[i]` or `q[{2,0}][i]`, with semicolons separating operands. Save/reopen,
undo/redo and export retain selectors; export emits static aliases and runtime
indices, including identity preflights for elided or broadcast operations.

Dynamic alias creation (`let a=q[i]`), runtime-selected subroutine arguments,
runtime-sized slices/sets, dynamic classical destinations and barriers remain
unsupported. Subroutine binding forms remain tracked under DEV-08b; this milestone
covers runtime indexing of existing fixed aliases, not every OpenQASM alias form.

`windows/test-qasm-runtime-wires.py` checks import, frozen parity, model validation,
execution and export/reimport. `windows/test-dev07-source-evidence.py` checks three
unchanged PyQASM loop literals pinned in `windows/fixtures/dev07-upstream.json`.
Continue/break distributions follow direct H-gate reasoning. The unmeasured H/CX
program is separately observed on a copy of the model with its independently
derived inverse and terminal measurements: all-zero probability one verifies its
pure state up to global phase. Its empty original output is only a smoke check.
The fourth fixture preserves the deferred alias/subroutine rejection. Upstream
fixture licensing is retained in `windows/fixtures/pyqasm-LICENSE.txt`.
