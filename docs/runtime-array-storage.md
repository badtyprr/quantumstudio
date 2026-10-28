# Runtime array storage

This DEV-08 increment adds native array element storage, expressions, writes,
and worker decoding. Source-language arrays, reference views, editor support,
and export remain separate unfinished DEV-08 work.

An array declaration contains a scalar table (integer or numeric), its element
type, a base slot, and one to seven dimensions. Elements occupy contiguous
row-major slots in the existing runtime storage. Nonempty arrays cannot overlap
another declaration in the same table. Every backing slot must have the declared
element type. The combined integer/numeric allocation and each dimension are
bounded by 4096; there may be at most 4096 declarations. A zero dimension means
zero elements, with no dummy readable slot.

Array selection evaluates one integer index per dimension, in order, before
forming the scalar address. Negative indices count backward within that axis.
Each index is checked independently, including unsigned values above INT64_MAX.
Selection trees share the existing 32-level and 512-node limits. An optional
source label is bounded to 512 bytes and cannot contain NUL.

Reading an element checks its initialization state. A store resolves its
destination before evaluating its right-hand side, then converts to the declared
type before mutation. Float32 rounding and angle conversion use the existing
numeric storage rules. Declaration and reference validation runs even inside
untaken branches; index values and element initialization are evaluated only on
reached paths. Clearing a backing scalar slot clears that element.

Both exact histories and sampled trajectories copy the existing scalar state.
The immutable array metadata is shared; element values and initialization bits
remain independent. Intermediate exact histories cannot merge while their
array values differ. Final records marginalize the private storage as before.

## Worker encoding

QEXACT14 and QSAMPLE15 extend QEXACT13/QSAMPLE14. Older request versions retain
their previous layouts. After numeric slot declarations, the new versions add
an array count followed by each declaration: table (0 integer, 1 numeric), the
existing two-integer element type, base slot, rank, and dimension sizes.
Loop budget and the remaining request fields follow unchanged.

Integer and real expression opcode 10 encode the declared result type followed
by a selection. A selection contains array ID, rank, integer index expressions,
source-label byte count, and each source byte as an LF-terminated integer.
Indexed-store opcodes 21 and 22 contain a selection followed by an integer or
real expression respectively. Bounds, type, allocation, expression-size, and
trailing-data checks apply before or during execution as described above.

`quantum-classical-array-test` exercises storage and both engines, including
measurement-history independence. `quantum-classical-array-request-test.py`
exercises both worker formats, malformed declarations, every truncation of a
valid request, nested array reads, and measurement-dependent indexing.
