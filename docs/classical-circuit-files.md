# Classical circuit files

Version 2 records saved classical bits and structured branches. Version 3 retains
that layout and adds `Assign` and `ExpressionBranch` steps. Files declare their
version explicitly; version 2 rejects non-null classical expressions and the new
step kinds. Saving a version 2 document does not silently upgrade it.

Both new steps have a `ClassicalValue` expression object. An assignment also has
`Wires`, containing distinct classical targets in least-significant-first order.
An expression branch has `WhenTrue` and `WhenFalse` arrays and a one-bit condition.
It must not contain matrix expressions, target wires, masks or mask values.

Expression objects have the following fields:

| Kind | Required fields besides `Kind` |
| --- | --- |
| `Constant` | Integer `Width`, unsigned decimal string `Value` |
| `Read` | Integer array `Bits`, least-significant first |
| `Complement` | Expression object `Left` |
| `Binary` | Operator name `Operator`, expression objects `Left` and `Right` |

Operator names are `And`, `Or`, `Xor`, `ShiftLeft`, `ShiftRight`, `Equal`,
`NotEqual`, `Less`, `LessEqual`, `Greater`, and `GreaterEqual`. They use the
unsigned width rules documented in [the worker protocol](classical-expression-protocol.md).
Unused known fields may be null, as emitted by the Windows serializer; non-null
irrelevant fields and all unknown fields are rejected.

For example, a one-bit assignment uses:

```json
{"Kind":"Assign","Wires":[0],"ClassicalValue":{"Kind":"Constant","Width":1,"Value":"1"}}
```

The existing 256 KiB file limit and 512-step, 32-branch-level bounds apply.
Each expression allows at most 512 nodes and 32 levels. All expression trees,
including untaken branches, are validated before a file or edit becomes the
current program. Snapshots and undo/redo preserve the complete trees. This schema
does not itself provide textual expression entry.

The classical OpenQASM importer preserves bit-register initializers, assignments,
bitwise compound assignments, comparisons and logical conditions in this schema.
Indices and slice bounds must resolve at compile time. Assignments inside static
loops retain their runtime position. Existing simple mask conditions can remain
version 2; expressions and assignments require version 3. Unsupported runtime
loops, switches, register indices/sizes, classical aliases, function arguments
and gate parameters are rejected rather than
evaluated using placeholder bit values. Signed, floating-point and general
arithmetic state remain separate work.

Assignment copy and bit-width behavior follow the
[OpenQASM 3 classical instruction specification](https://openqasm.com/versions/3.0/language/classical.html).
The pinned PyQASM 1.0.4 visitor is adapted only during unrolling; all replaced
methods are restored even when compilation fails.
