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
classical storage operations do not. The exact phase shortcut declines selected
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
