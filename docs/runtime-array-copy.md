# Runtime array value copies

Whole arrays and slices copy values with matching element type and shape.
Multiple sources concatenate along the outer axis, retaining matching inner
axes. Integer widths, float32 rounding and angle bit patterns remain unchanged.
Readonly destinations and mismatched ranks/types/shapes are rejected. Empty
arrays copy without reading an invented element.

The runtime resolves destination geometry, validates all source geometry and
shape, captures all source values, then writes the destination. Overlapping
copies and self-concatenation therefore do not depend on traversal direction.
An undefined source value causes no partial destination writes. Both exact and
sampled engines execute the same bounded copy operation.

The source compiler captures destination geometry before RHS calls. Compound
array-element assignments also capture their old value before RHS effects. When a later
concatenation operand can call a routine, an earlier operand's selected values
are copied to a private backing allocation before that call. Only selected cells
are read; undefined cells outside a slice remain untouched. Initializer lists
with calls likewise materialize elements in order. These private allocations
count toward the existing4096-slot storage budget. Ordinary copies need no extra
declared backing; their bounded temporary values live within the copy operation.

Empty array-only helper routines without calls in actual expressions lower to a
single reference preflight. This keeps exported checks from repeatedly growing
new geometry snapshots on reimport. Their body has no effects requiring a
retained activation snapshot.

Saved circuit version17 adds `ArrayCopy` metadata: `Destination` and `Sources`
views on a `CopyArray` step. QEXACT16 and QSAMPLE17 add operation24, encoded as
destination view, source count1..64, then source views. Existing versions remain
readable. At most512 combined expression nodes and4096 copied values are
accepted. The editor displays the copy and preserves it through save/reopen;
export uses ordinary assignment and `++` expressions.

DEV-08 remains open for dynamic collection/alias iteration, quantum reference
capture, full fixture/oracle/editor acceptance and verified packaged release.
