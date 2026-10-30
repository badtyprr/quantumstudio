# Runtime array views from OpenQASM

Runtime array selectors retain scalar-axis removal, inclusive ranges, negative
indices, strides and nested logical bounds. `sizeof` observes selected dimensions
without reading elements. Scalar reads and writes through nested slices use the
same typed backing allocation; float32, angle, integer and Boolean semantics are
inherited from that allocation.

Readonly/mutable array formals accept explicit fixed shapes or a fixed `#dim`
rank. Each actual's geometry is captured before later actuals and before the body.
Selectors are evaluated in parent, axis, start, step, stop order. Stride magnitudes
above the maximum backing dimension are captured as an equivalent signed stride
of magnitude4097, preserving direction even for `uint[64]` maximum values. Address-only
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

[Bulk/slice copying and array concatenation](runtime-array-copy.md),
[dynamic collection iteration](runtime-dynamic-collections.md) and
[quantum-reference capture](runtime-wire-reference-checks.md) build on this
integration. Source support inherits bounded rank/storage/expression/call/operation
budgets; complex and duration elements remain outside the supported scalar types.

Multidimensional bracket shorthand consumes the source dimensions in order: `a[i:j][k:l]` selects the same rectangle as `a[i:j,k:l]`, matching the pinned upstream importer. After all dimensions have been supplied, additional brackets select the resulting view. In particular, the one-dimensional `a[1:3][2]` still refers to original element 3. Scalar destinations read arrays through typed runtime storage even when their indices are constants, retaining element precision and undefined-value checks.
