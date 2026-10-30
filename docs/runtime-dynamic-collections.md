# Dynamic collection iteration

One-dimensional arrays and nested views accept runtime selectors, including
reference-formal views and rows selected from multidimensional arrays. Geometry
and selected values are captured at loop entry. Only selected cells are read;
undefined selected values fail before any body iteration. Empty selections run
zero iterations. The binding is a fresh scalar converted from each captured
value, independent of the loop cursor. Assignment to the binding or backing
array cannot change later captured values. This entry snapshot is the product's
chosen evaluation model; the language specification does not explicitly settle
mutation of future iterable elements.

Bit-register slices also capture geometry and values once, with dynamic positive
or negative strides. Bit endpoints remain nonnegative; integer overflow cannot
turn an invalid endpoint into a valid negative array index. Repeated entry
refreshes each snapshot. Existing scope handling owns break, continue and return.

Private backing arrays count toward the existing 4096-slot storage ceiling.
Array iteration no longer has a separate 64-value ceiling. Explicit discrete
collections retain 64 values, and bit registers retain their 64-bit width limit.
Snapshots preserve the backing shape but copy only the selected cells, so a
small view of a large array still charges a full private backing allocation.
All loop work remains subject to the existing execution budgets.

The lowering uses existing array-copy, view, scalar and range-loop model steps.
Saved documents, editor operations and OpenQASM export retain those explicit
snapshots; reimport does not introduce another collection snapshot. No protocol
or document version change is needed. Export removes unreachable instructions only from a snapshot of an already
validated circuit. A clear after unconditional continue never executes, so its
removal preserves the retained value rather than ending a lifetime. Reachable
clears retain their definedness effects. Source diagnostics and the saved model
are preserved.

Classical-bit aliases can be iterated through ranges, scalar selections, discrete
selections and concatenation. Alias declarations capture selected identities;
loop entry captures their current values. Nested aliases retain ordering, and
duplicate identities in concatenated or discrete selections fail before use.
Alias selectors support negative array-style indices and reverse strides.
Aliases remain lexical and can refer to bit-valued subroutine formals. Iteration
uses an independent Boolean scalar for a scalar `bit` binding, preserving the
full 64-bit physical register capacity. Other alias reads and writes are outside
this iteration feature. The existing rejection of nested bit-register
declaration shadowing remains; alias-name shadowing is supported.

Private identity and value maps each reserve 64 array slots and count toward
the shared storage budget. Contiguous identity-backed aliases reuse captured
geometry against their value map; concatenated selections gather through an
identity map. Both paths retain normal saved-model and export validation limits.

DEV-08 remains open for final fixture/oracle/editor acceptance and verified release.
