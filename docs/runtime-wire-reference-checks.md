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

This increment supplies native execution and protocol support. Saved-model,
editor, export and source call/alias binding integration are still required;
DEV-08 remains unfinished and no release is claimed.
