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

This releases the fixed-register subset. DEV-08b5 remains open for other parameter forms; constant-expression widths are next. The prior intermittent export file-replacement IOException remains unresolved; this audit passed without reproducing it.
