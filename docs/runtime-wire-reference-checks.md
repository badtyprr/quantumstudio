# Quantum reference preflight

The native `WireSelection::references` factory accepts one to25 ordered targets
for call-entry validation. Existing gate selectors retain their one-to-three
operand limit. Each target has an explicit ordered candidate map and an integer
index. Full-register references therefore use the same mapping and integer
semantics as dynamic gate selection.

`CheckWireReferences` validates candidate maps and expression types in every
body, including untaken branches. At execution it evaluates all selected
identities against the pre-operation classical state, rejects undefined or
out-of-range indices and physical overlap, then leaves quantum state and
classical storage unchanged. It is a dedicated check, not an identity gate.
A reference list has at most512 combined expression nodes, and candidate maps
have at most25 entries. Negative quantum indices remain unsupported.

QEXACT17 and QSAMPLE18 add opcode25: source context, target count, then each
candidate map and integer index. Older request formats reject the new opcode.
Both engines share parsing, validation and reference evaluation.

Saved circuit version18 uses `CheckWireReferences` with `WireTargets` and
`WireSource`, with no ordinary gate operands. Save/load validation rejects
mismatched metadata, oversized target/expression lists and invalid declarations.
The editor labels and edits quantum argument checks, preserves mappings through
undo/redo and save/reopen, and rejects invalid changes without replacing the
current circuit.

OpenQASM export uses empty scalar-qubit helper routines. Their calls lower to
one aggregate preflight; no identity gates or quantum mutations stand in for a
reference check. Runtime indices, constant-invalid indices in untaken branches,
classical scope lifetimes and the full target list survive export/reimport.
This helper path accepts only empty void routines with scalar-qubit formals and
actuals without nested calls. Full call-entry capture, nonempty routine bodies,
register formals and dynamic aliases use the source binding integration below.

## Runtime scalar quantum parameters

A nonempty runtime subroutine accepts a scalar qubit selected by an integer expression from a declared register or fixed alias. Each selector is checked and captured before evaluating the next argument. After all actuals have been evaluated, one reference check rejects physical overlap across the captured scalar references and whole-register parameters before body effects. Nested calls retain the captured identity. Existing fixed-literal calls retain their compile-time diagnostics and document versions.

Register views and dynamic aliases are described below. The scalar binding suite observes wire identity after later argument mutation, nested forwarding, aliases, mixed register parameters, overlap, lazy type checks, and selector-error ordering through original and exported programs on both engines.

## Quantum register parameters

Register parameters accept fixed aliases and register slices, including runtime range bounds. A private uint32 array records each declared register's physical indices; checked array views capture range geometry at argument evaluation. The view must have the formal's fixed width. Scalar indexing, whole-register gate broadcast and ordered measurement destinations use the selected physical indices, and nested register/scalar forwarding preserves the same capture. Selectors are validated in start/step/stop order before later selector calls. All referenced physical qubits participate in the final call overlap check.

Runtime aliases and concatenated quantum selections use the path described below. Existing static aliases and discrete selections retain the pinned compiler's mapping. Private identity arrays count against the existing storage and operation limits; they cannot be accessed or mutated through source parameters.

## Captured quantum aliases

Runtime quantum aliases capture range and discrete-set selections at declaration, with lexical scope, shadowing and per-iteration initialization. They can be indexed, passed to scalar/register parameters, reset, measured, and used by broadcast gates. Private identity arrays use circuit-wide physical indices so views from distinct registers compose without ambiguity.

Concatenation copies only the private index map, never quantum state. Up to 25 selected identities are retained; pairwise reference checks reject physical overlap before the resulting alias is used. An empty alias is invalid. Broadcast operations preflight every lane before physical operations; singleton registers broadcast and other widths must match. Measurement destinations must have matching widths and retain their bit order. The source retains DEV-07's nonnegative quantum-index boundary; ranges may have negative strides.

Private arrays and generated loops are charged to existing storage, operation, expression and loop budgets. Reference expansion is bounded by 4096 views and 32 alias levels. [Classical-bit alias iteration](runtime-dynamic-collections.md) captures bit identities and values without quantum references.

Contract sources: [OpenQASM aliasing/index sets/concatenation](https://openqasm.com/versions/3.0/language/types.html) and [lexical alias scope](https://openqasm.com/versions/3.0/language/scope.html).

Quantum calls in range loops use runtime capture when bounds are computed or the body assigns/shadows the binding or transfers control. The independent range cursor still determines the next value, with the existing typed conversion into the loop binding. Eligible literal loops retain compact expansion. Discrete collections use captured ordered values, including duplicates. Export retains local lifetime intervals around transfers rather than moving their exit cleanup past break, continue, or end.

Range-bound calls capture start, stride, and stop in source order. Each snapshot retains the normalized integer expression type, including unsigned 64-bit bounds, so later calls cannot retarget an earlier bound or change its signedness. Original bound type validation precedes the snapshot.
