# Sets, Cartesian alphabets and indexed families

Quantum mode distinguishes an ordered tuple from a vector or matrix:

* `tuple(0,2)` is an ordered pair; `tuple()` is the empty tuple.
* `cartesian(vector(0,1),vector(2,3,4))` forms six ordered pairs.
* `cartesianpower(vector(0,1,2),2)` forms the nine length-two ternary tuples.
* `cardinality(...)` counts distinct elements; `member(value,domain)` tests membership.
* `setimage(k^2,vector(0,1,2),k)` produces the image `{0,1,4}`.
* `setfilter(k>0,vector(-1,0,1),k)` retains only `1`.

TeX literal powers such as `\{0,1,2\}^{2}`, integer ranges such as
`\{0,\ldots,n-1\}`, images `\{k^2:k\in\{0,1,2\}\}` and filtered sets
`\{k\in\{0,1\}:k=x\}` accept the same operations. Use explicit `cartesian`
and `cartesianpower` for named domains; ordinary multiplication and powers do not
declare an unknown symbol to be a set.

Binary literal powers `\{0,1\}^n` retain the established binary-string type,
including leading zeros. General Cartesian powers use tuples. These are distinct
representations: a binary string is not a number or a tuple.

An unknown membership, equality, predicate, width or endpoint stays conditional.
For example, `cardinality(vector(x,y))` cannot become 2 until the entries are known
to differ. Copy preserves the executable expression and its conditions;
`replace(copied_expression,y,x)` resolves that example to 1. Displayed binder
names are local and may be renamed without changing meaning. Saved sessions
retain input and history. A domain does not confer an assumption on a free symbol.

Empty sets have cardinality zero; singleton sets have cardinality one. A zero-fold
Cartesian power contains the empty tuple. A positive power of an empty alphabet
is empty. Nested Cartesian products retain nested tuples and their ordering.
Substitution into an indexed image/filter respects its local binder and nested
sum/image/filter scopes.

Concrete materialization supports at most 1024 entries, Cartesian powers and
tuples at most 32 coordinates, and nested tuples at most 32 levels. Binary-string
widths retain the existing 0-to-10 bound. Unknown counts retain these constraints
until substitution; a known invalid count, label or domain rejects even when
another input is unknown. These limits are explicit evaluation bounds, not a
claim of unrestricted symbolic set algebra or whole-lesson compatibility.

Legacy `unique` and `select` accept typed domains and retain their set type.
For genuine vector inputs they retain the established vector behavior. The
explicit third argument of `union`, `intersect` and `setdiff` selects the legacy
multiset API: its result is a vector, preserving requested multiplicities.
Use the two-argument forms for typed set operations and set copy/re-entry.
