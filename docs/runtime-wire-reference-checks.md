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
register formals and dynamic aliases still require source binding integration.

DEV-08 remains unfinished; no release is claimed.
