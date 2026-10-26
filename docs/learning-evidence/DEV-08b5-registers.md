# DEV-08b5: fixed quantum-register parameters

This bounded implementation accepts whole declared quantum registers for runtime
subroutine parameters with literal widths from 1 to 25. Widths must match exactly;
underlying qubits may not overlap across actual arguments. References preserve
caller state and register order. Existing lowering handles single-register gates,
literal element access, measurement/reset, and nested forwarding.

The unchanged `windows/fixtures/runtime-subroutines/qbraid-register-return.qasm`
is the QASM literal from PyQASM's `test_function_call_in_expression` at
[167cff141b270cae023137971e716d5fec68e9f0](https://github.com/qBraid/pyqasm/blob/167cff141b270cae023137971e716d5fec68e9f0/tests/qasm3/subroutines/test_subroutines.py).
Its SHA-256 is `c3457c8d542db65c834bb8f3fbdba09b816499bfb692bc2b155a70116eb61367`.
The baseline return/concatenation compilers reject classical import because the
parameter is nonscalar. The new source test checks four H gates on wires 0–3,
matching the upstream oracle. This is compiler acceptance, not whole-notebook
execution. Separate authored drivers test state mutation, ordering, nested calls,
repeated calls, collisions, measurement/reset and one-element registers against
the published worker's exact and sampled results.

The [OpenQASM subroutine specification](https://openqasm.com/language/subroutines.html)
defines quantum arguments as references and prohibits duplicate underlying qubits
in a call. [Scope rules](https://openqasm.com/language/scope.html) separate formal
bindings from caller variables. Keeping whole-register AST references allows the
existing unroller to own index expansion without another interpreter or protocol.
The width bound matches the circuit editor's existing 25-qubit limit.

Constant-expression widths, alias/slice actuals, dynamic quantum indices,
array-reference parameters and runtime float/angle values remain outside this
slice. Mixed scalar/register multi-qubit gate broadcasting is an existing unroller
limitation and rejects; this change does not claim the full
[broadcasting rules](https://openqasm.com/language/gates.html#broadcasting).
The two other unchanged qBraid controls retain their dynamic-index/float gaps.
DEV-08b5 and the whole notebook checklist rows remain open.

Validation after the first review fix: 518 source checks passed. The seven new authored execution
drivers passed exact and sampled checks using the already published return worker;
the source suite also checks width/overlap/index errors and unsupported forms.
The release evidence below records the subsequent frozen validation, review, CI, merge and publication.

The first independent Spec review found one medium caller-scope validation bug:
an unused quantum formal could erase an invalid call with a same-named local
integer actual. Lexical caller-binding checks now reject that case, including
loop-variable and scalar-qubit variants, and restore register visibility after
leaving the shadowing block. The regression covers an unused formal so downstream
gate validation cannot mask the error.

## Published fixed-register subset (REL-20)

PR [#370](https://github.com/badtyprr/quantumstudio/pull/370), exact reviewed head `f79ed62fe35d7b6fc84f311e8b60e92988fbe486`, merged as `266febf0fbb5e39ffc3b96a7e78020f2351e7e15`. Two independent Standards/Spec review rounds completed; the caller-shadowing finding above was fixed and both final reviews had no outstanding findings. Source/frozen comparison passed 1,024 checks. All three required Native/GUI/OpenQASM checks passed on the reviewed head. Native CI also verified 261 source-archive inputs byte for byte.

The [published Windows checkpoint](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-b4cc7ee0) was built from `b4cc7ee04dcac71cc307420499e5bad171414c52`, which additionally includes the separately self-reviewed concatenation release documentation in #371. All three merged-tip CI checks passed. The clean package passed 1,992 worker and 1,710 compiler checks; native tests had 56 passes, one existing thread skip and zero failures/errors.

Three packaged GUI export/save/reopen checks passed. Six exact results, covering both input and exported source, matched probability one for nested forwarding (`100`), measurement/reset (`0001`) and caller-scope restoration (`10`). Nine normal, deliberate-rejection and minimum-window captures were inspected. The six unchanged-source controls retained the expected numerical outputs and classical diagnostics: the four-H Boolean-return fixture now also passes classical import; the other two classical controls still reject dynamic indexing and float parameters. This is bounded compiler acceptance, not whole-notebook or provider execution.

All 340 payload hashes and 341 ZIP entries matched the tested package. The uploaded asset size, digest and tag revision were verified. ZIP SHA-256: `f439732f52a4b9f1331a932123e4ced564b7c95edea5ea1fd9f27def5e8148fc`.

REL-20 releases the fixed-register subset. DEV-08b5 remains open; the subsequent constant-expression and bounded-loop implementations and their verified release are recorded below. At REL-20, the intermittent export file-replacement IOException remained unresolved; that audit passed without reproducing it. REL-21 recovery is recorded below.

## Constant quantum-register widths: implementation and initial package attempts

The runtime call binder now resolves quantum-formal widths against earlier global integer constants at the subroutine definition. Actual register sizes resolve against constants visible at their declaration. A caller's same-named local does not change either size; an earlier classical formal shadows a same-named global constant and cannot supply a compile-time width. Whole-register references, exact size matching, overlap rejection and scalar/register distinctions remain in force.

The supported width expression subset is integer literals (at most 64 bits), earlier integer constants, integer casts with omitted size or a literal size from 1 to 64, unary minus, addition, subtraction and multiplication. The pinned evaluator retains integer cast/range validation. Before evaluation, the expanded expression is checked against 512 expression nodes and 32 nesting levels; existing constant-binding expansion also retains its 65,536-node budget. Powers, shifts, division/remainder, calls, indexing, Boolean/float expressions and computed cast sizes are unsupported in this subset. The final supported size remains 1–25; zero-sized registers are outside this product subset, though the language permits non-negative sizes.

This validation is applied to widths needed by lowered runtime quantum calls. Unrelated static-only programs retain the compiler's existing evaluator. It adds no runtime register allocation, array references, dynamic indices or protocol change.

The [OpenQASM qubit examples](https://openqasm.com/language/types.html#qubits) supply `const uint SIZE = 4; qubit[SIZE] q2;`. The `computed-qwidth-spec` test preserves that declaration example and adds a Boolean-returning flip subroutine, call and output measurement as an authored driver. It is not an unchanged full source program. The [scope rules](https://openqasm.com/language/scope.html#subroutine-and-gate-scope) require definition-visible constants and source-order visibility.

Source regressions cover constants/dependencies, arithmetic, casts, nested forwarding, caller shadowing, scalar element references, width boundaries, mismatches/overlaps, nonconstant/forward names and bounded-expression failures. Evaluator tripwires ensure expensive powers, shifts and cast sizes reject before arithmetic. Nine authored drivers have independently specified exact and sampled worker outcomes. Frozen compilation, final review and CI passed as recorded below. Publication history and the completed release audit are recorded below.


### Implementation validation and historical package blocker

PR [#373](https://github.com/badtyprr/quantumstudio/pull/373), exact reviewed head `ab5abae367c47a34ef666d5f861aa08672f09003`, merged as `0eba610564b0d4fdd783a209aa1a6cf4cf2a0e5d` with tree `4cec98159e44b28a92c40783198f1c230ff5b9d5`. Independent Standards review: zero breaches/actionable heuristics. Independent Spec review: zero findings. Both reviewers confirmed the rebase preserved the reviewed tree and diff. Required Native, Windows GUI and Windows OpenQASM CI passed on both the reviewed head and merged tip.

Local source validation passed 588 checks. Source/frozen comparison passed 1,159 checks, and the frozen compiler passed 46 array checks. Nine new authored drivers passed exact and sampled outcomes using the previously published worker. An explicitly marked integration candidate combined that worker/GUI with the reviewed frozen compiler; three GUI exports, six original/exported exact results and nine inspected captures passed. These results do not replace an audit of the eventual clean release payload.

The clean local native build passed 56 tests, with one existing thread skip and zero failures/errors. The retained source archive matched all 261 checked inputs byte for byte. The package stopped at the existing circuit-layout GUI test's 120-second timeout. An isolated current-app run and the previous published app both reproduced the timeout. A subsequent isolated current-app run passed every layout assertion in about 94 seconds. Resuming from the unchanged GUI suite, with the original deadline and every remaining package gate retained, hit the same layout timeout again. No source or test-deadline changes were made. This is an unresolved intermittent timeout, not a diagnosed root-cause fix.

At that point REL-21 was not published: final importer/package tests, actual release-payload GUI/exact audit, archive hashing and upload were pending. REL-20 remained the last verified downloadable checkpoint. The completed release is recorded below. At that point the previous export file-replacement IOException also remained unresolved.

The next source-led candidate identified during that package investigation was bounded literal-range loop specialization for quantum-call indices. Preserve lexical loop bindings, mutation/transfer restrictions and aggregate expansion budgets; general dynamic indices and runtime float/array parameters remain separate work. That candidate was subsequently implemented as recorded below.

### Subsequent local GUI verification

The unchanged isolated circuit-layout test subsequently passed in 60.1 seconds, within its original 120-second deadline. The complete unchanged GUI suite then passed, including that layout test. No application source or deadline was changed for these runs. This completes the failed test's rerun, but does not establish the intermittent timeout's root cause or complete release packaging/publication.

## Next increment: bounded quantum-call loop indices

Literal-range integer loops whose binding is needed in a quantum-call argument are specialized before runtime subroutine binding. Each iteration retains a lexical block; classical call arguments still use the existing value snapshots, and quantum arguments retain their reference/overlap checks. The unchanged pinned `test_classical_quantum_function` fixture now passes source classical import as well as its existing numerical path. See the [fixture provenance](../../windows/fixtures/runtime-subroutines/README.md).

The initial subset accepts signed integer literal endpoints and a nonzero literal step, with at most 64-bit literal magnitude. Loop types are int/uint with omitted size or literal widths 1–64; emitted values must fit the declared type. Ranges include the final reachable value and support descending, non-divisible and empty ranges. Only literal indices after substitution are accepted; arithmetic indices and runtime bounds remain outside this subset. Loops not needed by runtime quantum calls retain their existing path.

The selected binding may not be assigned or shadowed anywhere in its body. Break, continue and return statements anywhere in the specialized body are rejected, including transfers belonging to nested loops; this conservative restriction is narrower than the language. Calls to subroutines with returns remain supported. Expanded loops are limited to 4,096 iterations each and share the existing aggregate 65,536-node expansion budget with calls. Existing call-count, call-depth and binding-copy budgets remain active across iterations.

Source checks cover ascending/descending/non-divisible/empty ranges, caller shadowing, nested indices and activation-local loops. Rejections cover mutation, body shadowing, transfers, runtime bounds, zero steps, type/index overflow, arithmetic indices, huge ranges and overlapping quantum actuals. The upstream program is kept byte-for-byte; an authored measurement/assertion extension separately checks all eight `1abc0` results at probability 1/8. These probabilities follow from H twice on q[0], one H on each remaining qubit, X preserving the plus state, and the last return value equalling four.

Local validation after review fixes: 614 source checks and 47 focused execution/control checks passed using the previous published worker. The Spec review found that implicit-return void calls using body-local classical arguments were detected too late; preflight now accounts for those declarations, with a per-iteration local initialization/execution regression. A second review found that collecting all body-local names ignored declaration order and nested scope; detection now follows both, with a static-path compatibility regression using a global constant and a later nested local of the same name. A final target-binding check distinguishes writing a bit indexed by the loop variable from assigning the loop variable itself; both indexed assignment and measurement have execution coverage. Subsequent verification passed 1,210 source/standalone comparisons and 46 frozen array checks. Independent Standards and Spec reviews cleared exact head `f7537ce4624f60444476fa9ebbe85bb4b35b5e3a`; all three required CI jobs passed. [PR #375](https://github.com/badtyprr/quantumstudio/pull/375) merged as `53fdfccc04233bb163f489bb753f8265132e0e09`. Release verification is recorded below.

## REL-21: verified package

Published [e9e01c5a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e9e01c5a) from reviewed merged revision `e9e01c5a68703f822775fee6bed2f9d786cb0670`, including the constant-width and bounded-loop implementations. The clean native suite passed 56 tests with one existing thread skip and no failures/errors. All required CI and package gates passed, including the unchanged GUI/layout suite, worker, compiler and export checks.

The actual immutable package passed three width reference circuits and three bounded-loop reference circuits through GUI import/export; all twelve original/exported exact distributions matched their independent expectations. Eighteen circuit captures and two basis-editor captures were visually inspected. All manifest payload hashes and ZIP entries matched before publication. ZIP SHA-256: `4dc6ab77e5b551efc7d3721d93a5a39bf9776a6f9e64bc5260f33c30db066419`.

This clears the prior publication gate for these bounded subsets. DEV-08b5 remains open for its other parameter/index forms. The historical layout timeout has no established root-cause fix. [PR #377](https://github.com/badtyprr/quantumstudio/pull/377) adds bounded recovery for documented transient export replacement errors; the underlying filesystem cause remains unidentified.
