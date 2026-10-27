# DEV-07: dynamic wire indexing research

Research 2026-10-26 against application base `bb76a90a` and pinned PyQASM `167cff141b270cae023137971e716d5fec68e9f0`. Source inspection only: no new compiler/executor acceptance is claimed. [DEV-07's checklist](../learning-coverage-checklist.md#dev-07) requires bounded runtime indices, aliases, negative/out-of-range cases, multi-qubit collisions and source-local diagnostics. Whole-notebook acceptance remains separate.

## Primary semantics and an important negative-index caveat

The [OpenQASM types specification](https://openqasm.com/language/types.html#qubits) permits implementations to reject non-constant qubit indices; its qubit definition gives integer positions 0 through size−1. However, the same document's [register slicing section](https://openqasm.com/language/types.html#register-concatenation-and-slicing) explicitly demonstrates negative alias/register indices, runtime index sets, inclusive stepped ranges and nonempty selections. Thus rejecting negative quantum indices is a documented product subset, not a blanket statement that all such syntax is invalid OpenQASM. Aliases/slices reference existing qubits; quantum concatenation cannot overlap itself. The prose and some examples are inconsistent about negative-range cardinality; derive cardinality from the stated inclusive range rule, not an example comment.

The pinned [validator](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/src/pyqasm/validator.py#L46) accepts only 0≤index<size. It is compatibility evidence for rejecting negative indices, not an independent oracle for all specification indexing forms.

[Gate broadcasting](https://openqasm.com/language/gates.html#broadcasting) pairs equal-length register operands lane by lane and permits scalar operands shared across lanes. The rule does not authorize reusing one physical qubit in two roles within a single gate. Pinned PyQASM [duplicate-qubit validation](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/src/pyqasm/analyzer.py#L285) supplies direct implementation evidence for rejecting collisions. Check resolved identities, not syntactic expressions: q[i] and q[j] may collide even if i and j have different names.

[Subroutine specification](https://openqasm.com/language/subroutines.html) passes quantum arguments by reference and prohibits overlap between any quantum actuals in one call. A scalar runtime-index actual must select one qubit at call entry; changing the caller index during the activation must not retarget the bound formal. Validate actuals and overlap even if formals are unused. Formal shape/width remains fixed at compile time.

[Built-in instructions](https://openqasm.com/language/insts.html) define reset as discarding the chosen subsystem and preparing zero; measurement is Z-basis projection and leaves the selected qubit usable. Whole-register measurement preserves source/target index correspondence. Dynamic source selection should reuse these operations, not approximate reset with a unitary or defer target resolution until after measurement has changed state.

## Recommended finite contract

1. Accept scalar integer expressions selecting a qubit from a fixed declared register or fixed-length alias. Reuse typed integer arithmetic and its errors, including undefined reads. Accept explicit integer casts; reject implicit fractional/Boolean indexing rather than silently truncating. Evaluate anew at each instruction so runtime loop mutation and measured-bit-derived selection work.
2. Choose zero-based nonnegative indices for the initial product contract, matching current compiler behavior. Reject negative and ≥size indices with original source span plus register/index/size, consistently in import, JSON load validation where possible, and execution. Clearly state that negative alias forms shown by the language are outside this subset. A later negative-index implementation must normalize relative to the selected register/alias length before bounds/collision checks, not the global wire count.
3. Resolve all operands and parameters before applying any effects of one instruction. Then check all ranges and per-gate distinctness. A failing later operand must not leave a partially applied gate, reset group or measurement broadcast. Preserve ordered operands and control polarity. In unexecuted branches, do not evaluate unreachable bad indices.
4. Support indexing existing static aliases, including reordered static slices/sets; alias-relative index j resolves through its stored ordered wire list. To satisfy alias creation from dynamic scalars, bind `let a=q[i]` at declaration execution and retain that qubit for the alias's scope. Reentering a loop recreates the alias. Do not retain a live textual expression that follows later i mutations. The specification describes references but does not explicitly spell out this mutation example; declaration-time binding is the recommended model, corroborated by pinned [alias visitor](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/src/pyqasm/visitor.py#L2850), which stores resolved identities.
5. Admit static-length slice/set aliases with each resolved element validated and preserved order. Keep arbitrary runtime-changing-length slices/sets explicitly unsupported unless a bounded runtime register-list model is implemented. A scalar-selection alias is a one-qubit reference/register shape as required by the current parser; do not drop shape distinctions merely to pass a `qubit[1]` formal.
6. Apply scalar dynamic selection to gates (including DEV-06 forms), measurement source, reset and subroutine actuals. Retain fixed classical measurement destinations initially; dynamic classical indices are a different capability and should not be implied. Whole-register subroutine actuals may use a fixed ordered alias of matching width; reject overlap after full resolution.
7. Keep current qubit, expression-depth/node, call/loop and execution budgets. No allocation proportional to an untrusted index; no state-vector enumeration just to dispatch an index. Include cancellation and original source locations in exported/reloaded operation metadata. These are proposed product requirements, not observed implemented features.

This finite contract covers every DEV-07 acceptance category while explicitly deferring dynamic-size register construction, negative-relative indexing, arbitrary alias concatenation and dynamic classical targets. If the intended milestone requires those broader forms too, they must remain open rather than be silently folded into a completion claim.

## Unchanged source fixture candidates

Extract Python AST Constant string values, UTF-8 with Python-normalized LF, preserving whitespace (no strip/dedent). All sources below are at the pinned PyQASM revision. The local source status was clean. Hashes are literal values, not Python file bytes.

| Fixture and source literal | SHA-256 | Independent oracle |
|---|---|---|
| [test_while_loop_with_continue, test_while.py lines30–46](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_while.py#L30) | `4922eeaddcdba52dc1edb274a7baf618dd77c03d811f44a7c73849f749362ef6` | H on q0 and q2; terminal measurement c2c1c0 gives 000,001,100,101 each 1/4 under the application's zero-initialized simulation convention. Mutation/continue skips q1. |
| [test_while_loop_with_break, lines55–69](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_while.py#L55) | `4e87fd48982690460b076dc929d376b89b652a17376056c97fb65286dcb727d8` | H only on q0; c2c1c0 is 000 or001, each1/2. |
| [test_while_loop_unroll_qasm_output, lines79–89](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/test_while.py#L79) | `1b6f6359b61e450df819cc3c166520bcb0c2786f2fa312095f0cc7876cabda1f` | Ordered H0,CX01,H1,CX12,H2,CX23. State amplitude on q3q2q1q0=`ccba` is (-1)^(ab+bc)/sqrt(8), a,b,c∈{0,1}; all other amplitudes zero. No measurements in original; compare full state. No stdgates include in upstream literal: preserve that fact and report if importer requires it. |
| [test_alias_arg_from_loop_validates, subroutines/test_subroutines.py lines203–224](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/subroutines/test_subroutines.py#L203) | `497ec30f4e7d7c608909b2f96d8e50654162d87620663b81006f5e51c2d372e5` | H sequence on wires0,1,2,1,2,3 reduces to H0H3. From zero state, q3q2q1q0 is 0000,0001,1000,1001 with amplitudes1/2. Calls use a local alias to an indexed element as a qubit[1] actual and discard Boolean result. Static loop bounds do not prove measurement-dependent indexing. |

These are actionable blocked candidates by inspection: [qasm-import.py](../../windows/qasm-import.py) base lines954/967 reject runtime register indices/targets; [qasm_runtime_subroutines.py](../../windows/qasm_runtime_subroutines.py) lines138–148 requires literal scalar indices, and register formals currently require whole declared registers. The first two while programs' mutable i is retained as runtime storage. No fresh baseline run is claimed; preserve an actual pre-change diagnostic before implementation to substantiate the blocker.

Independent reference should parse these small originals and implement typed counters plus direct H/CX matrices, not execute the candidate importer output. PyQASM's unrolled gate list is a useful second check but is not an independent execution engine. For strict language initialization, these originals do not explicitly reset the qubits; retain the application's documented zero-state convention in the test harness instead of editing source and calling it unchanged.

## Authored probes needed beyond upstream acceptance

- Measured-bit selector: prepare selector s with H, measure to bit m, set int i=int(m), apply X to q[i], measure q. Expected joint outcomes tie the selected bit to q=01 or10 with probability1/2. This establishes actual feedback rather than compile-time unrolling.
- Alias snapshot: i=0; let a=q[i]; i=1; x a must affect q0. Repeated loop declarations should select successive wires. Test alias-of-alias, reordered static list and local shadow restoration.
- Call snapshot: pass q[i] to a routine that changes a classical index variable available through its own legal binding; subsequent formal operations retain the original qubit. Pass q[i],q[j] with i=j and require overlap rejection even for unused formals. Do not introduce illegal mutable-global captures in this test.
- Check -1,size,very large integers, fractional values, undefined selector, same evaluated wire for CX/control-target/CCX, runtime alias overlap and collision in a later broadcast lane. Include valid distinct aliases referring to different original wires.
- Dynamic reset after entanglement must match partial-trace/reset branch behavior; dynamic measurement must collapse the resolved qubit, leave it usable, and retain the fixed classical output order. Compare exact branches and sampled frequencies.
- Partial/reversed/static stepped slices must keep inclusive selection order. Zero step, empty selection, invalid endpoints and mismatched broadcast lengths must reject without side effects. Unsupported runtime-size slices need explicit diagnostics rather than accidental scalar interpretation.

The preceding are authored probes, not unchanged source fixtures. Add import/model/save/reopen/export/reimport, editor display and source-local error verification; retain all reviewed-head, CI and package evidence requested by the checklist. Neither these probes nor the four upstream literals establish full qBraid notebook or complete OpenQASM indexing coverage.

## Selected implementation boundary

The DEV-07 checklist is satisfied by scalar runtime indices into fixed declared
registers and existing fixed aliases. Dynamic alias creation and runtime-selected
subroutine argument binding are recommendations for the separate DEV-08b work,
not claims about this implementation. The fourth upstream candidate remains a
rejection control. See [the application contract](../runtime-wire-protocol.md).
Actual baseline runs retained for the first three literals reject runtime quantum
targets in REL-22; the alias call rejects a non-whole-register quantum actual.
