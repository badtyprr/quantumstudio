# Runtime array storage

DEV-08 now has native array element storage, expressions, writes, worker
decoding, version-15 saved documents, indexed editor expressions, and basic
global source arrays with export/reimport. Reference views, array parameters,
bulk/slice operations and array iteration remain unfinished DEV-08 work.

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

## Application and source integration

Version 15 adds `Arrays` declarations (name, base, dimensions, element type and
width), `Selection` on integer/real array-element expressions, and `ArrayTarget`
on stores. Selections carry array ID, integer index expressions and source
context. Existing versions retain their layouts. The adapter validates shape,
allocation, element type, expression depth and target fields before execution.
Both worker boundaries pass these declarations explicitly.

The expression editor uses `array(0, index)` (additional comma-separated indices
for additional axes) for reads and store targets. Imported allocations survive
editing, invalid edits, undo/redo and save/reopen. Array allocation itself is
authored in source or in the validated document. Export emits global OpenQASM
array declarations and maps backing-slot reads/writes to the corresponding
elements. Clearing an array backing slot as a local lifetime or using it as a
range binding has no supported export representation and is rejected.

The source adapter retains the established compile-time path for static arrays.
It selects runtime storage for measurement/scalar-dependent indexing,
initialization and writes, writes in runtime control flow, negative indices and
zero dimensions. All accesses to a selected allocation use the same runtime
storage. The runtime budget is 4096 combined scalar/array slots; the older
compile-time-only path retains its 65536-element budget. Supported runtime
elements are int/uint/bool, float32/64 and angles of widths 1–64. Constant shape
and width expressions currently accept integer literals, named integer
constants, unary minus and addition/subtraction/multiplication. Complex and
duration elements are rejected.

`test-runtime-array-model.py` exercises saved documents through both workers.
`test-qasm-runtime-arrays.py` checks source, exported/reimported source and frozen
compiler equivalence. Existing compile-time array fixtures, including the
unchanged ripple-carry program, remain covered by `test-qasm-arrays.py`.
