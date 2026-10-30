# Array views in saved programs and the editor

Circuit document version16 adds nested view selectors, access permissions,
view extent expressions and explicit array-reference preflight steps. Existing
versions remain loadable. JSON parsing bounds every expression and view before
construction, rejects unknown fields and rejects permission escalation, rank
mismatches, wrong backing identities and readonly stores. Saved, reopened and
copied documents retain geometry expressions rather than an execution's values.

Both worker request writers emit the view-capable protocol for array programs.
Integer/numeric selections retain their existing element type. Preflight and
view geometry participate in integer and numeric lifetime recovery during
export, including locals referenced only by a view.

The expression editor supports `array(view(...), index)`,
`arrayextent(view(...), indices...)` and `viewextent(view(...), axis)`.
A view is `view(arrayId or parentView, mutable or readonly, selectors...)`;
selectors are `at(integer)` or `range(start, stop, step)`, with `*` for an omitted
range field. Readonly views cannot be assignment targets. The program tree
identifies reference preflight as "Validate array arguments" and shows its
views and fixed shapes. Float-array editing uses the allocation's type rather
than looking up a nonexistent scalar target slot.

OpenQASM export emits nested array selectors and `sizeof`, and represents a
preflight as a call to an empty routine with the same readonly/mutable array
parameters and fixed-shape/rank contract. This is a reference check, not a dummy
element read or write. The pinned parser requires a stop when a range has an
explicit step. For an omitted stop, export currently fills a provable nonempty
full-axis boundary with a constant step; otherwise it rejects the unsupported
export before writing. Such omitted-stop stepped views are native/editor forms,
not accepted stepped-range syntax from the pinned source parser.

Saved-model execution, export syntax and editor preservation are covered here.
[Source lowering](runtime-array-view-source.md) captures geometry at call entry
and retains reference checks through reimport. [Bulk copies](runtime-array-copy.md)
and [collection snapshots](runtime-dynamic-collections.md) reuse these views.
