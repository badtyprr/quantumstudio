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
