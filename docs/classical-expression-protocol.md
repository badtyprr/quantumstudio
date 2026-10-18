# Classical expressions in worker requests

`QEXACT2` and `QSAMPLE3` retain the field layout and operation codes of
`QEXACT1` and `QSAMPLE2`, respectively, and add two operations. Older versions
continue to reject the new operation codes. These are binary UTF-8 worker
requests, not expressions to paste into the calculator input.

| Operation | Fields after its code |
| --- | --- |
| 7: assign | Target count, distinct classical indices, classical expression |
| 8: branch | Classical expression, true-body count and operations, false-body count and operations |

Assignment indices are ordered least-significant first. The whole expression
reads the incoming classical record before any target changes. Other bits and
the quantum state are preserved. Exact execution merges density matrices when
assignments produce the same record. Branch conditions must have width one;
the selected body runs to completion even if it overwrites the condition.

Classical expressions use the following prefix-tree encoding. Every field is
an unsigned decimal integer terminated by LF; these expressions do not use the
length-prefixed mathematical strings used by gate and channel operations.

| Node | Fields after its code |
| --- | --- |
| 0: constant | Width, value |
| 1: read | Index count, classical indices in least-significant-first order |
| 2: complement | Operand node |
| 3: binary | Operator code, left node, right node |
| 4: population count | Operand node |
| 5: rotation | Direction (0 left, 1 right), distance interpretation (0 unsigned, 1 signed), value node, distance node |

Population count returns an unsigned 64-bit internal value, from 0 through 64.
Rotation preserves the value width. Signed distances use two's-complement at
that operand's declared width; negative distances reverse the direction.
Distances wrap modulo the value width. Zero and full-width rotations preserve
the value. These node codes extend QEXACT2 and QSAMPLE3; older workers reject
these new nodes, while all prior node encodings retain their meaning.

Operator codes are 0 AND, 1 OR, 2 XOR, 3 left shift, 4 right shift, 5 equal,
6 unequal, 7 less, 8 less-or-equal, 9 greater, and 10 greater-or-equal.
Bitwise and comparison operands require equal widths. Comparison results have
width one. Shift counts may have any supported width; a shift at least as large
as the left width produces zero. Left shift and complement retain their width.
Read indices may repeat; assignment targets may not.

Widths are 1–64; constants must fit their width. An expression has at most 512
nodes and 32 levels including its root. Decoding enforces those limits before
descending, as well as register bounds, including in untaken bodies. Existing
request byte limits, operation budgets, branch depths and timeout behavior
remain in force. Signed integers, floats, casts and loops are separate features.

For example, `c[1:2] = c[0:1]` uses operation fields
`7, 2, 1, 2, 1, 2, 0, 1` (each followed by LF). From record `001` this yields
`011`, because both source bits are read before either destination is written.


## Typed variable storage: QEXACT4 and QSAMPLE5

These versions insert a declaration table immediately after the classical-bit
count and before the output-bit list. It contains a slot count (0-4096), followed
by each slot's signedness (0 signed, 1 unsigned) and width (0 machine, 1-64 sized).
Names and lexical scopes are resolved by the producer. Slot IDs are zero-based.

Integer node 4 contains signedness, width and slot ID. Its type must exactly match
the declaration. Operation 9 contains a slot ID followed by an integer expression;
it evaluates the RHS before converting and writing to the declared type.
Operation 10 contains a slot ID and clears that slot to undefined. Earlier
protocol versions reject these new nodes and operations.

Every shot or exact evaluation starts with undefined variables. An executed read
of an undefined slot fails the whole request. Structural validation checks both
branch bodies without reading values. Exact histories retain independent slots
until their values and initialization states agree; output probabilities sum
over variable histories. Classical bit outputs and JSON responses are unchanged.
Existing request-size, expression-depth and operation-count limits still apply.
Exact execution also limits the total stored variable slots across histories to
its cell-budget value (1,048,576 for worker requests), independently of matrix cells.

## Computed bit casts: QEXACT5 and QSAMPLE6

These versions retain the declaration table and operations of QEXACT4/QSAMPLE5.
Integer node 5 contains signedness, width and a complete bit-expression node.
The operand width must match the integer width (64 for machine-sized types).
The bits are reinterpreted, so a signed 8-bit operand `11111111` becomes -1.
To preserve Boolean true as positive one, use unsigned width 1 and then cast to
the desired integer type.

The operand can contain integer comparisons, logical operations or integer-to-bit
casts. One shared 512-node/32-level budget covers the entire alternating tree.
Short-circuit evaluation skips undefined reads in unused operands; structural
validation still rejects invalid references and mismatched variable types.
Earlier protocol versions reject integer node 5. Result JSON is unchanged.

Circuit documents use version 6 for these casts. `IntegerFromBits` has `Signedness`,
`Width`, and a bit-expression `Left` child. Version 6 requires a `Variables` array,
which may be empty. Older document versions reject the new node.

In the classical circuit editor, enter casts directly, for example
`uint[3](c ^ "111")`, `int[3](~c)`, or `uint[1](c == 0)`. Operand widths must match
the cast width; `uint(popcount(c))` uses the 64-bit machine width. Save/reopen,
selection, replacement, and undo/redo preserve these expressions. Editing variable
declarations preserves the document version required by existing expressions.

## Runtime loops

`QSAMPLE7` and `QEXACT6` retain their preceding versions' fields and expression
nodes, adding one LF-terminated unsigned loop-condition budget after the typed
variable declarations and before the output-index count. The budget must be in
0..1,000,000. Zero permits paths that never evaluate a loop condition. Older
headers do not carry this field and continue to reject operation 11.

Operation 11 is encoded as: condition expression, body-operation count, then
that many operations. The condition must have width one. Both readers validate
all bodies, including unreachable bodies, under the existing nesting, byte and
static-operation limits. Each iteration tests the current classical and typed
variable state before running the body. There is no implicit measurement.

Sampling shares the condition budget across all loops in each shot, resetting
it for the next shot. Exact evaluation shares it across the complete run,
including all measurement histories. Each condition check, even a false one,
uses a unit. Exhaustion produces an error with empty stdout, never partial
counts or normalized partial probabilities. The native exact evaluator does
not sum infinite iteration series. Responses retain their existing schemas.
Windows adapters and version 7 circuit files emit these versions. The editor
and OpenQASM importer support runtime while loops.


## Loop transfers

`QSAMPLE8` and `QEXACT7` retain the loop headers' fields, including the condition
budget, and add two payload-free operations: 12 for break and 13 for continue.
Earlier headers reject both opcodes, even inside an unreachable body. The new
headers also accept programs that contain no transfers.

Both engines validate that every transfer has an enclosing loop before any
execution. Branches propagate the transfer; the nearest loop consumes it.
Break resumes after that loop without another condition check. Continue skips
the remainder of its body and checks that loop's condition again, using the
ordinary budget. Exact histories keep pending transfers distinct until the loop
consumes them. Response schemas, byte limits, nesting limits and operation limits
are unchanged; malformed input and budget exhaustion return no partial result.

The Windows request adapter selects these headers when a loop contains a
transfer. It rejects transfers outside loops, including unreachable branches,
and rejects expression, target, condition, variable and body fields on transfers.
Requests without transfers retain their existing header versions. Circuit file
versions 1 through 7 continue to reject transfers; version 8 preserves them.
The editor creates and preserves both transfers. OpenQASM import preserves
transfers targeting runtime while loops and emits scope-exit clears before them.
Static for-loop transfers lower to guarded, one-pass while bodies with explicit
scope cleanup. Runtime for ranges remain unsupported. Whole-program termination uses the newer headers below.
These transport versions do not infer or perform source-level
scope cleanup; a compiler must emit the required clearing before a transfer.

## Program termination

`QSAMPLE9` and `QEXACT8` retain the preceding fields and add operation `14`
with no payload. It terminates the current shot or exact history at any nesting
depth. Saved classical output and probability mass are retained; later operations
are skipped. Termination does not consume a loop-condition check, but entering a
loop still does. Unreachable operations remain structurally validated. Earlier
headers reject operation 14. Version 9 circuit files, the End program editor operation, and OpenQASM `end;`
import expose this transport operation.
