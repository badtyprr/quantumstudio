# Runtime array views from OpenQASM

Runtime array selectors retain scalar-axis removal, inclusive ranges, negative
indices, strides and nested logical bounds. `sizeof` observes selected dimensions
without reading elements. Scalar reads and writes through nested slices use the
same typed backing allocation; float32, angle, integer and Boolean semantics are
inherited from that allocation.

Readonly/mutable array formals accept explicit fixed shapes or a fixed `#dim`
rank. Each actual's geometry is captured before later actuals and before the body.
Selectors are evaluated in parent, axis, start, step, stop order. Address-only
reference checks validate each captured part before narrowing snapshots; they do
not read or initialize array elements. A singleton geometry check validates a
scalar address without inventing a value. A final check enforces fixed shapes and
physical overlap among mutable actuals. Overlapping readonly references and a
mixed readonly/mutable pair are allowed. Readonly access cannot be regained by
forwarding, and no call-local view cleanup clears its backing allocation.

Calls within selected assignment targets and their right-hand sides preserve the
captured destination before RHS effects. Saved version16 models retain view
geometry, preflight and local snapshot lifetime; exported reference checks use
empty typed helpers and are accepted by this source lowerer on reimport.

This increment is not all of DEV-08. Bulk/slice copying, array concatenation,
dynamic view collection iteration and dynamic quantum-reference capture remain
unfinished. Full unchanged upstream fixtures, independent oracle acceptance,
packaged release verification and milestone closure also remain. Source support
inherits bounded rank/storage/expression/call/operation budgets; complex and
duration elements remain outside the supported scalar types.
