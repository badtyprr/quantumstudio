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

Version 3 expression trees also support `PopulationCount` with `Left`, returning
an unsigned 64-bit count, and `Rotate` with `Left` (value), `Right` (distance),
`RotationDirection` (`Left` or `Right`), and `DistanceInterpretation` (`Unsigned`
or `Signed`). Signed distances use two's-complement at the distance node's width.
Rotation preserves the value width and wraps the distance modulo that width.
Names are case-sensitive; numeric enum values and irrelevant fields are rejected.
Older readers reject these additional kinds instead of changing their meaning.

Classical imports may contain no qubits. Such programs retain `Qubits: 0` and
execute assignments and conditions against their classical registers in both
exact and sampled modes; no unused quantum register is added.

The OpenQASM importer preserves `popcount`, `rotl`, and `rotr` in assignments
and branch conditions, including nested calls. Rotation distances may be signed
integer constants, population counts, or explicit width-matched `int[n]` and
`uint[n]` casts of bit expressions. A cast retains its signed interpretation;
static casts outside these calls retain the existing constant evaluation path.
Bare bit-register rotation distances are rejected: write the intended integer
cast explicitly. General runtime integer variables and arithmetic remain
separate work. These rules follow the OpenQASM 3.0 built-in functions and
bit-to-integer cast definitions:
https://openqasm.com/versions/3.0/language/types.html

## Version 7: runtime loops

Version 7 requires `Variables` (possibly empty) and an integer
`LoopConditionBudget` in 0..1,000,000. Earlier versions reject non-null budgets
and loop operations, and their canonical JSON omits the new field. A `While`
step uses a one-bit `ClassicalValue` condition and a required `WhenTrue` array
for its body; `WhenFalse` must be absent or null. The body may be empty.
Matrix expressions, quantum targets, masks and variable-write fields are not
allowed on the loop itself. Existing 512-step, 32-level and 256-KiB file limits
still apply, including all bodies and unreachable operations.

Save/reopen and immutable snapshots preserve the budget and complete loop body.
The exact and sampling windows forward that budget to their workers. It counts
every loop-condition evaluation, including false conditions: sampling resets it
per shot, while exact evaluation shares it across all measurement histories.
Exhaustion reports an error, never partial results. A budget of zero can be used
to prohibit executed loop conditions. OpenQASM `while` import preserves runtime conditions and scoped bodies. Imported
loops use a default budget of 1,000,000, editable below. `break`, `continue` and
`end` inside runtime loops are not yet supported.

In the classical circuit editor, select **While expression**, enter a one-bit
condition such as `counter > 0`, and add it to the selected body. Select its
**Loop body** to add operations that run repeatedly. The condition is checked
again after each iteration, so changes to variables and measured bits take
effect immediately. **Apply loop limit** saves the condition-check budget with
the circuit; adding the first loop uses 1,000,000 unless a limit is already saved.

Replacing a loop with an if expression preserves its body. Converting an if to
a loop requires an empty Else body, and changing a populated block into a
non-block operation is rejected. These edits and the limit support undo/redo.
Saving, reopening, Exact probabilities and Sample all use the same loop body
and budget.

## Version 8: loop transfers

Version 8 retains the variable declarations and condition budget required by
version 7. A `Break` or `Continue` step has no payload and must be inside a
`While` body, possibly inside nested branches. Validation checks unreachable
bodies too. Versions 1–7 reject these steps.

`Break` exits the nearest enclosing loop. `Continue` skips the remainder of
that loop's body and rechecks its condition, consuming the ordinary condition
budget. Save/reopen preserves both operations; exact and sampling requests use
`QEXACT7` and `QSAMPLE8`. Editing a loop or its budget preserves version 8.
In the editor, select a Loop body or a Then/Else body inside a loop, choose
**Break loop** or **Continue loop**, and select **Add to selected body**. No
expression or target is needed. The tree identifies the nearest-loop behavior.
Transfers support replacement, deletion, undo/redo and save/reopen. Adding one
outside a loop, discarding a populated body, or converting a loop in a way that
would leave a transfer outside any loop is rejected without changing the circuit.
OpenQASM transfer import remains separate integration work.
