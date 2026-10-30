# Runtime discrete collection loops

DEV-08 increment: scalar discrete collections (`for int i in {a, 1, a}`) use the existing range execution engine. Whole one-dimensional arrays and bit registers, plus constant slices, now use the same entry snapshots. Dynamic slices, classical aliases, array-reference parameters and quantum-reference binding remain unfinished DEV-08 work.

A collection contains at most 64 values, in source order, including duplicates. Each expression is evaluated and converted to the declared loop type before the next expression. The resulting sequence is captured at entry; changes to source variables inside the loop do not change later iteration values. The loop binding is independent of the cursor, may be assigned, and is scoped to each iteration. Integer/Boolean, float32/64 and angle types retain their existing conversion rules. The pinned parser rejects empty discrete-set syntax; zero-length arrays execute zero iterations.

Break, continue, nested loops and subroutine returns use existing cleanup and execution budgets. A balanced dispatch tree selects the captured value without nesting proportional to the sequence length. Existing 512-step, 32-level, variable and 256 KiB canonical-document limits still apply to the complete lowered program. Export emits equivalent scalar snapshots and a runtime range, retaining those semantics after reimport.

Export lifetime recovery combines only synthetic unconditional scopes whose slots have already passed the complete-reference interval proof. Entry/exit clears can move within that containing scope, never across a real branch or loop. The temporary DTO serialization bound is 4 MiB because absent fields expand to null; public input and canonical saved documents remain limited to 256 KiB.

The unchanged pinned PyQASM `test_convert_qasm3_for_loop_discrete_set` string is retained in `windows/fixtures/dev08-collection-upstream.json`, with revision, line, SHA-256 and license. H on four zero-initialized qubits followed by CNOT permutations and the original measurements gives all 16 outputs with probability 1/16. This is source fixture coverage, not whole-notebook acceptance. Authored tests separately cover measured runtime values, snapshots, ordering, precision types, shadows, transfers, the 64/65-value boundary and model/save/export/reimport behavior.

## Array and bit-register sources

Array and bit-register iteration visits indices in order and captures the selected
values before the body starts. Modifying a loop variable never writes through to
its source. Mutating the source during the body does not change the captured
sequence. Constant inclusive slices preserve stride and direction; classical
array endpoints accept negative indices. Whole zero-length arrays and their
full omitted-endpoint slices execute no iterations.

The selected sequence is limited to 64 values; a small slice may come from a
larger array within the 4096-slot runtime allocation budget. Snapshots also count
against normal storage limits. Bit snapshots and bit bindings use the existing
64-bit classical-record budget, so large bit collections can exhaust it. Array
iteration retains element type, including float32 rounding and angle wrapping.
Declared dimensions are captured in their declaration scope; loop-variable
shadowing must not change the source shape. Bit-register parameters can be
iterated inside runtime subroutines.

This increment supports constant slice geometry. Runtime slice bounds, iterating
classical aliases, multidimensional views and array-reference parameters remain
separate, unfinished requirements. No release or parent DEV-08 closure is claimed.
