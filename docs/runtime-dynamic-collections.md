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
or document version change is needed. Export removes only duplicate tail cleanup after direct transfers, from a
snapshot of an already validated circuit. Every removed clear must already
occur immediately before the transfer. Source diagnostics and the saved model
are preserved.

DEV-08 remains open for classical aliases, dynamic quantum reference binding,
full fixture/oracle/editor acceptance and verified release.
