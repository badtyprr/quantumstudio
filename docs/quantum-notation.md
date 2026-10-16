# QuantumStudio research and coverage notes

The project goal is broad quantum-computing and quantum-programming notation support, including IBM Quantum Learning and qBraid learning materials. **That goal is not complete.** A working example or a green test suite does not establish whole-course or whole-language compatibility.

This note accompanies the executable. Its build revision is recorded in `build-manifest.json`. The offline `Notation-guide.html` describes implemented operations and their input limits. The source archive contains the corresponding implementation and tests.

## Sources and audit method

The [IBM course catalog](https://quantum.cloud.ibm.com/learning/en/courses), checked on 2026-10-15, lists 15 courses. Discovering those courses is only an inventory step. Each lesson still needs its mathematical expressions, assumptions, register conventions, and executable code classified separately. The public qBraid notebook audit uses [qbraid-lab-demo revision 86787e1](https://github.com/qBraid/qbraid-lab-demo/tree/86787e1ba372facc224f925189755e69c479828b); it does not imply that the app executes the notebooks or their SDK calls.

For a formula, record the source, choose explicit finite dimensions and parameter values, and compare its result against an independently derived vector or matrix. Preserve the source syntax where possible. Record adaptations such as replacing an unspecified register dimension, rather than calling an adapted expression an exact paste. Keep malformed-input and convention checks alongside successful examples.

The source archive also contains `docs/learning-source-inventory.json`: 137 discovered IBM course sections, 12 modules, and 35 pinned qBraid notebooks. This is a work queue, not a compatibility certificate. The notebook hashes were rechecked against the pinned primary repository on 2026-10-15. Overview pages, exams, videos, linked material, and account-only content still require discovery and audit.

## Selected verified notation

The [IBM phase-estimation procedure](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure) motivates these regression cases:

- Subscripted summation indices such as `a_0`, including nested binders and reused index names. See `src/quantum-parser-integration-test.cc`.
- Unbraced finite sums and products use multiplicative-term scope. For example, `\sum_{k=0}^{2} k+1` gives 4, while grouping `(k+1)` gives 6. Nested phase-estimation sums are covered by the integration tests.
- Space-separated computational bits such as `|a_1 a_0>`: with phase parameter 1/4, the tested intermediate state after the first controlled operation is `[1;i;1;i]/2`. Each bit must evaluate to 0 or 1.
- TeX matrix row spacing such as `\\[1mm]`: the spacing is ignored, and the lesson's four-dimensional Fourier matrix is checked against `qfourier(4)`.
- The probability `|⟨101|(H⊗H⊗H)|000⟩|^2` equals 1/8. The packaged keyboard check verifies that Enter displays 0.125 once without inserting a newline.

These are selected finite examples, not certification of the entire phase-estimation lesson. In particular, source formulas can rely on implicit dimensions, named states, or mathematical definitions supplied earlier in the text.

## Sequential state evaluation

`quantum: sequence([apply(H,s_0,[0]),apply(X,s_0,[0])],|0>,s_0)` applies the two transformations in list order and returns |+>. Each step receives the previous result through the bound placeholder `s_0`. The initial expression is outside that binding; nested sequences may reuse the same placeholder. An empty list returns the evaluated initial state. Steps are evaluated only after substitution, so noise channels, reset, dephasing and feed-forward operations can be mixed with gates.

Use a flat comma-separated list of at most 512 transformations. The initial value and every result must be a vector of at most 1024 scalar entries or a matrix with at most 1024 rows, 1024 columns and 1048576 scalar entries. These are shape limits, not a guarantee of a normalized or physical quantum state; individual operations perform their own validation. Direct native callers use `qsequence(vector(step1,step2),initial,placeholder)`; explicit `vector(step)` preserves a one-step list.

The quantum parser permits up to 4096 atoms after encountering a sequence call. Its nesting limit remains 256 and its input limit remains 32768 bytes; translated-size and TeX limits also remain in force. These bounds can reject a complex expression with fewer than 512 steps. Cancellation is checked between transformations, in addition to checks within the evaluated operations. The GUI circuit editor and OpenQASM importer accept up to 512 steps. Circuits longer than 64 steps use the flat sequence form. Parameter complexity and the expression byte limit can still prevent evaluation of a circuit within the step limit.

A development audit generated four-qubit QFT and inverse-QFT OpenQASM with `qbraid-algorithms` 0.1.3, then unrolled it with pyqasm. The resulting programs have 108 and 112 steps respectively. Their unitary portions were adapted to sequence expressions and checked on all 16 computational basis inputs each against an independent NumPy gate-by-gate calculation: 32 checks, maximum vector-norm residual 2.20e-15. The complete inverse-QFT sequence, including four nonselective measurements, was checked on the same 16 inputs against the uniform diagonal density matrix: maximum residual 1.46e-16. This audit does not establish arbitrary notebook execution, ideal inverse-QFT wire-order equivalence, or arbitrary qBraid program compatibility.

## Selected qBraid generated-program audits

The pinned [QFT](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qft.ipynb), [phase-estimation](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qpe.ipynb) and [Bernstein–Vazirani](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/bernstein_vazirani.ipynb) notebooks received partial generated-program audits on 2026-10-15. Their original bytes match the inventory hashes. The inventory records package versions, generated-program hashes, numerical results and the tested revisions. These development audit observations are separate from the maintained regression cases in `windows/test-qasm-import.py`; a reader should not interpret the latter as replaying every notebook audit.

Generation used `qbraid-algorithms` 0.1.3 and PyQASM 1.3.0 in an isolated environment. QuantumStudio's importer uses its pinned PyQASM 1.0.4 adapter. The packaged 512-step editor at revision `4d27af21` imported the 108-step QFT and 112-step inverse-QFT programs and evaluated their generated expressions successfully.

For phase estimation, the installed generator defines the supplied eigenstate-preparation gate but does not call it. With a Z or P(pi/4) unitary, the unchanged generated program therefore starts the eigenstate wire at zero and reports phase zero. Separately tested adaptations explicitly call `prep_eigenstate psi[0]` before `qpe(q, psi)`. With three counting qubits, these produce displayed counting-register strings `001` for Z and `100` for P(pi/4). Reversing their bit order as described in the notebook gives phases 1/2 and 1/8 respectively. Both compact and unrolled variants were checked. This is an observation about the tested package version, not a promise about every version or a reason to alter imported programs silently.

The compact controlled-T variant originally failed import. The reviewed fix `b0d40148` maps controlled S/T and their adjoints to CP while retaining phase. Both the unchanged and explicitly prepared T programs were then checked. PyQASM 1.3.0 itself rejected the corresponding controlled-T unrolling; using P(pi/4) was recorded as a separate equivalent-unitary case, not an unchanged-input success.

For Bernstein–Vazirani, all eight three-bit secrets plus the notebook's `1011` example were generated in compact and unrolled form. All 18 imported circuits produced the expected measured-register probabilities. Cloud jobs, QIR execution, account setup, SDK statements, custom-include file workflows and notebook visualizations were not executed. None of these three notebooks is certified end to end.

## Selected qBraid adder audit

The pinned [PyQASM unrolling notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_unroll.ipynb) contains a ten-qubit ripple-carry adder. Its `adder_qasm_str` was extracted without executing the notebook. The notebook SHA-256 is `ead11c7785b8996b8386fac69c63a710ef8bb2742533db14ca3bacd21f8536d4`; the extracted UTF-8 source with LF newlines hashes to `503bda0e6df9ad1e0eb858606ef092c4eeab07be73cb1d29b0ee0ccbaa5d12ad`.

At released revision `232ef1b7`, the packaged importer produced 45 editable steps. The packaged GUI loaded, saved and reopened them; its expression produced the independently expected full 1024-outcome distribution. The initialized little-endian operands are 8 and 15, so the result is 23. With QuantumStudio's leftmost-wire convention, the final basis index is 61: the first operand is restored, the low sum is 7, and the carry is 1. Evaluation took 1.36 seconds on the audit machine; this is an observation, not a performance guarantee.

Eight separately adapted inputs also passed full-distribution comparisons: `(0,0)`, `(1,1)`, `(1,15)`, `(7,9)`, `(15,15)`, `(15,0)`, `(0,15)` and `(5,10)`. Eight additional packaged-GUI comparisons checked leading resets followed by unitary gates, measurements, later resets or noise, in short and long circuits. The editor defers density conversion for initial resets of its known zero state, retaining density output semantics and saved steps. The earlier grouped-reset development audit timed out after 120 seconds. Notebook SDK calls, visualizations and arbitrary notebook execution are not certified by these checks.

## Selected Grover analysis audit

Selected identities from [IBM's Grover analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/analysis) were checked on 2026-10-15. At released revision `366f836a`, 36 full-state comparisons passed for dimensions 4, 8 and 16, with 1, half, or all-but-one marked states and 0 through 3 iterations. Finite sums built the uniform state and marked-state projector. Independent reference amplitudes used the lesson's rotation angle `asin(sqrt(M/N))`; maximum residual was 1.57e-15.

At released revision `f1af3559`, ten further checks passed with zero reported residual: uniform-state preparation and the diffusion-reflection identity for one through five qubits. These exercised compact register notation such as `H^{\otimes n}|0^n>` with concrete widths. A reproducible example is `norm(vec(H^{\otimes 2}|0^2>-(1/2)\sum_{x\in\{0,\ldots,3\}}{|x>_4}))`, whose expected value is zero.

These audits replace the symbolic bit-string domain with an explicit integer range and supply ket/identity dimensions. General symbolic alphabets, Cartesian set powers and automatic state-dimension inference remain unfinished at `97e1d120`; that revision adds finite-set cardinality. At `f1af3559`, an unqualified sum of `|x>` over `{0,1,2}` incorrectly returned scalar `3`; this is not a valid quantum-state result. Revision `0dee0478` rejects those scalar ket labels. The explicit form `\sum_{x\in\{0,1,2\}}{|x>_3}` supplies the required dimension. The recorded checks are selected source audits, not full-lesson certification or a claim that CI replays every audit.

## Selected general-measurement audit

On 2026-10-15, selected finite examples from IBM's [measurement formulations](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements) and [Naimark construction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/naimark-theorem) were checked with explicit matrices substituted for lesson variables. This is not a literal-paste or whole-lesson certification.

The released worker at `69f2b383` passed 13 of 15 initial checks. Approximate square roots of two complex tetrahedral effects failed; exact mode passed those same expressions. PR #60 preserves exact algebraic identities before numerical evaluation. Its development worker passed 30 expanded checks: effect probabilities and completeness, matrix roots, Naimark isometries and distributions, conditional states, and partial measurements of a Bell pair. Maximum residual was below 1e-15. The worker linked the changed matrix-power implementation against the earlier release library; these observations do not certify a complete release build.

For a reproducible example, `born([2,1;1,1]/3,|+>)` gives 5/6. A complex-effect root check is `norm(vec(sqrt(density((|0>+sqrt(2)*exp(2*pi*i/3)*|1>)/sqrt(3))/2)-density((|0>+sqrt(2)*exp(2*pi*i/3)*|1>)/sqrt(3))/sqrt(2)))`; its expected value is zero. Maintained native regression cases are in PR #60's `src/quantum-matrix-power-test.cc`. Automatic construction and validation of arbitrary measurements remain unfinished.

## Selected discrimination and tomography audit

The packaged worker at `e5b92d21` passed the 30 general-measurement checks above, with maximum residual 9.55e-16. This verifies those selected examples in the complete release, beyond the earlier development linkage check.

Selected finite examples from IBM's [discrimination and tomography lesson](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/discrimination-and-tomography) received further packaged-worker checks on 2026-10-15:

- At `e5b92d21`, 29 checks passed with zero reported residual: 16 tetrahedral overlaps, six state reconstructions, two empirical-count estimates, four tetrahedral optimality-certificate identities, and the success probability 1/2. The certificate identities compare each matrix with `(I-density(phi_a))/4`, whose positivity follows because `phi_a` is normalized. This is not a general semidefinite-program solver.
- At `3da8f2ca`, 24 checks passed with maximum residual 9.80e-17: five prior probabilities for discriminating `|0>` from `|+>`, each expressed using function, ASCII-bar, Unicode-bar and TeX norms, plus four Pauli-basis reconstructions. The independently derived reference probability is `(1+sqrt(1-2*p*(1-p)))/2`.

These audits substitute explicit vectors for named states and expand finite sums. For example, twelve identical tetrahedral outcomes reconstruct the trace-one matrix `[2,0;0,-1]`; the audit verifies that estimate, without claiming it is a physical density matrix or applying an automatic positivity correction. Sampling, arbitrary ensembles, general optimal-measurement construction and automatic tomography reconstruction remain unverified or unimplemented.

Direct-paste gaps were reproduced at `3da8f2ca`: `\sum_{k\in S_0} |k><k|` and `\sum_{k\in\{0,1\}} |k><k|` reject `\in`; `\{k\in\{0,1\}: k\geq 0\}` rejects the escaped set delimiter. Finite set-indexed sums are now implemented as described below; finite filtering comprehensions are described below. More general set-builder forms remain work items. None of the selected checks establishes whole-lesson compatibility.

## Floor and ceiling

Floor and ceiling brackets accept both TeX (`\lfloor x\rfloor`, `\lceil x\rceil`) and Unicode (`⌊x⌋`, `⌈x⌉`), including nesting and delimiter sizing. They use mathematical floor and ceiling, so `⌊-3/2⌋ = -2` and `⌈-3/2⌉ = -1`. Empty, mismatched and unclosed brackets are rejected.

For example, the approximation in IBM's [Grover iteration-count lesson](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/number-of-iterations), `\Bigl\lfloor\frac{\pi}{4}\sqrt{16}\Bigr\rfloor`, evaluates to `3`. The angle-dependent formula `\lfloor\pi/(4\sin^{-1}(1/2))\rfloor` evaluates to `1`. Quantum inverse trig functions return dimensionless radian values so the ratio is a number. Implicit set cardinalities remain work items; these examples do not certify the entire lesson.

## Named ket validation

A named ket such as `|statevector>` must evaluate to a column matrix with at most 1024 rows. Bras validate the same column state before taking its adjoint. Scalars, row vectors, square operators and unresolved scalar names are not silently accepted as states. Normalization is not imposed.

For a sum over integer basis indices, specify the state dimension: `\sum_{x\in\{0,1,2\}}{|x>_3}` produces the column `[1;1;1]`. Omitting `_3` does not provide enough information to infer a register dimension and now reports an error rather than returning the scalar sum `3`. General symbolic bit-string domains and automatic dimension inference remain unfinished.

## TeX trigonometric powers

`\sin^{-1}(x)`, `\cos^{-1}(x)` and `\tan^{-1}(x)` mean the inverse trigonometric functions, matching the notation used in IBM's Grover analysis. The explicit commands `\arcsin`, `\arccos` and `\arctan` are also accepted. In quantum mode these commands and `asin`, `acos`, `atan` return dimensionless radian values, preserving the library's principal branches. For example, `asin(1/2)` gives `pi/6`. The internal functions are `qasin`, `qacos`, and `qatan`; unresolved calls retain the radian convention when evaluated after substitution. Ordinary calculator-mode inverse trig behavior is unchanged.

Other superscripts apply to the function result: `\sin^2(pi/6)` gives `1/4`, and `\sin^{-2}(pi/6)` gives `4`. The inverse interpretation applies to the literal exponent `-1`; write `(\sin(x))^{-1}` for a reciprocal. Powered functions require a parenthesized or braced argument, optionally with TeX delimiter-sizing commands such as `\left` or `\biggl`. Unbraced powered-function arguments remain unfinished.

## Finite set-indexed sums

Finite membership uses `x ∈ S` or `x \in S`, with `∉` / `\notin` for nonmembership. The function spelling is `member(x,S)`. Collections may contain scalar values or typed binary labels, with at most 1024 entries; bare scalars and matrices are rejected as collections. Binary labels compare by width and value, so `bitstring(1,3)` is not a member of `bitstrings(2)`. Exact scalar equality is used, and undecidable symbolic equality reports an error rather than a false result. Membership predicates can also appear inside set filters. Infinite and general symbolic domains remain unfinished.

`union(A,B)`, `intersect(A,B)` and `setdiff(A,B)` accept finite collections of binary-string labels, including empty and singleton collections. Labels compare by width and value. The optional third argument `1` uses multiset multiplicities: maximum for union, minimum for intersection, and nonnegative subtraction for difference. Each input and output is limited to 1024 entries. Use `vector(...)` for explicit label collections. The operators `\cup` / `∪`, `\cap` / `∩` and `\setminus` / `∖` call union, intersection and difference. Intersection and difference bind more tightly than union; repeated intersection/difference operators associate left to right. Use parentheses to override this grouping. `\emptyset`, `\varnothing` and `∅` denote an empty vector set. For example, `cardinality(\{0,1\}\cup\{1,2\})` gives `3`. Use `cardinality(...)` around compound set expressions; general compound cardinality bars and general symbolic set algebra remain unfinished.

A named nonempty collection of binary-string labels can be used as a set ket, following the uniform-state convention in [IBM's Grover analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/analysis). `|S>` normalizes the sum of the distinct basis states in `S`; `<S|` is its adjoint. The function spelling is `qketstate(S)`. For example, `qketstate(vector(bitstring(0,2),bitstring(3,2),bitstring(0,2)))` gives `[1;0;0;1]/sqrt(2)`. Repeated labels do not increase amplitudes. All labels must have the same width, and the collection is limited to 1024 entries. Empty sets and mixed-width sets reject. Existing column-vector kets retain their amplitudes. Arbitrary symbolic alphabets and sets of nonbinary labels remain unfinished.

The explicit binary Cartesian domain `\{0,1\}^n` enumerates bit strings of width `n`, preserving leading zeros. Widths must evaluate to integers from 0 through 10; width zero contains the empty string. `bitstrings(n)` is the function spelling. These domains work in finite sums: `\sum_{x\in\{0,1\}^2}{|x>}` yields `[1;1;1;1]`, and the corresponding sum of `|x><x|` is `identity(4)`. A typed label supplies its own ket dimension. Reversing or repeating the alphabet's entries does not change the domain.

Internally, `bitstring(value,width)` constructs a width-carrying label, rather than an integer or state vector. `bitvalue`, `bitdot` and `bitxor` accept these labels. XOR of two labels preserves their width; mixing a label with an existing bit vector returns a bit vector. Dot products return parity, and binary operations require equal widths. The empty string has integer value zero and dot product zero with itself; its XOR with itself is the empty string. For example, `qketstate(bitxor(bitstring(5,4),bitstring(6,4)))` produces `|0011>`. Filtered binary domains work with concrete predicates, including empty and singleton results: `|\{x\in\{0,1\}^3:bitvalue(x)<3\}|` gives `3`. Duplicate labels compare by both width and value; `01` and `001` remain distinct strings. Label sets contain at most 1024 entries and are ordered first by width, then integer value. For an explicit list of labels, use `vector(bitstring(1,2),bitstring(1,3))`; square brackets currently route these non-scalar entries through matrix concatenation and reject them. General arithmetic on descriptors, arbitrary Cartesian alphabets, implicit definitions of `Sigma`, and unbounded materialization remain unfinished. Unsupported literal alphabets reject instead of being interpreted as vector powers. This does not establish whole-lesson compatibility.

Cardinality bars around an explicit finite set, such as `|\{0,1,1\}|` or `\lvert\{0,1,1\}\rvert`, give `2`. Empty sets count as zero. Ranges and filtering comprehensions also work: `|\{k\in\{0,\ldots,7\}:k>3\}|` gives `4`. Use `cardinality(S)` for a named finite flat scalar collection; arbitrary named bars are not inferred to denote a set.

Counting uses the existing finite-set sum evaluator with summand `1`, including its 1024-entry limit, exact evaluation and structural duplicate comparison. This is not a new typed symbolic set system: general equality of unresolved symbolic members, Cartesian powers, infinite sets and sets of vectors remain unfinished. Column states and operators must not be treated as finite scalar collections.

Quantum-mode `[7]` preserves a one-element vector. For a named one-element collection defined through the library API, use `vector(7)` or `quantum: [7]`; ordinary calculator parsing can treat `[7]` as grouped scalar input. A bare scalar remains invalid for cardinality.

`\sum_{k\in\{0,2,5\}}{k^2}` evaluates to 29. The equivalent function form is `sumset(k^2,[0,2,5],k)`. A named collection such as `\sum_{k\in S_0}{k}` must evaluate to a finite flat vector. The index is local to the summand; nested sums may reuse it, and the inner collection can refer to the outer index. An unbraced summand uses the existing multiplicative-term scope.

Collections contain at most 1024 scalar entries, before duplicate removal. Entries are evaluated in exact mode and structurally equal results are counted once; this does not prove equality of arbitrary symbolic expressions. The empty sum is scalar zero. Matrix-valued summands are supported. Basis labels still require their dimension when it cannot be inferred: `\sum_{k\in\{0,1\}} |k>_2<k|_2` gives the two-dimensional identity, while bare `|k>` names a state.

Escaped set braces and membership are recognized in summation bounds. Arbitrary set algebra, infinite sets, and set-indexed products remain unfinished. The native function is `qsumset(body,collection,index)`. When directly nesting it inside the library's ordinary `sum` or `product` outside quantum mode, use distinct index names: those existing outer functions perform unscoped replacement. Quantum-mode parsing gives set-sum indices unique names to avoid that capture. Parser byte and node limits can reject an input before the collection-size limit is reached.

## Finite set literals and filtering comprehensions

TeX `\{0,2,0\}` evaluates using the library's `unique(vector(0,2,0))`. A filtering comprehension such as `\{k\in\{-2,0,2,2\}:k\geq0\}` keeps the distinct nonnegative entries, producing the vector `[0,2]`. `\mid` may replace the colon, and `\left`/`\right` sizing is accepted. Named finite collections must have a value, and the predicate must evaluate to a Boolean for each member. This implements the finite filtering shape used to partition indices in IBM's discrimination lesson; it does not infer an unspecified eigenvalue list or register dimension.

Comprehensions compose with set-indexed sums. For example, `\sum_{k\in\{j\in\{-1,0,2\}:j\geq0\}}{k}` gives 2. The predicate's index is local; its collection may refer to an enclosing index. Nested Latin, Greek and subscripted indices use the quantum parser's binding rules.

Sets use the existing `unique`/`select` representation, not a new symbolic set type. The library may display a one-element result as its scalar member; set sums preserve that result as a one-element collection when evaluating these operations. Ordering and symbolic equality follow the existing vector/set functions, so not every unresolved symbolic set can be evaluated. Parser size/nesting limits and the set-sum collection limit still apply. Mapped comprehensions such as `\{k^2:k\in S\}`, general ellipsis expansion, infinite domains, and general membership propositions remain unfinished.

## Finite integer index ranges

Inside a TeX set, `\{a,\ldots,b\}` denotes the ascending integer range from `a` to `b`, inclusive, with step +1. `\dots`, `\cdots`, and literal `...` are also accepted in that three-entry form. Endpoints must evaluate to integers. For example, `\sum_{k\in\{0,\ldots,3\}}{k}` gives 6; the equivalent function input is `sumset(k,indexrange(0,3),k)`.

This convention supports IBM's finite index domains `\{0,\ldots,n-1\}` after supplying `n`. An upper endpoint below the lower endpoint gives the empty range, so `n=0` yields an empty domain; equal endpoints give one member. The native function `qindexrange(first,last)` checks the span before allocating and permits at most 1024 entries. Large integer endpoints are allowed when their span fits that limit, and cancellation is checked during expansion. Range results compose with filtering comprehensions and set-indexed sums.

This is an explicit step +1 convention, not arbitrary sequence inference. Descending or stepped sequences, multiple leading terms such as `\{0,1,\ldots,3\}`, tuples of ensemble entries, and infinite endpoints are not inferred by this form. Existing parser and collection limits still apply.

## Numerical conventions

TeX `\tilde{\rho}` and `\widetilde{\rho}` denote the distinct symbol `ρ_tilde`; they do not evaluate to `ρ`. This supports estimated-state notation in the IBM tomography lesson. Subscripts outside the decoration follow the suffix, so `\tilde{x}_0` names `x_tilde_0`. These symbols can be bound as finite-sum indices. The decoration does not define a state or automatically reconstruct one: supply the symbol's value when a numerical result is needed. Compound operands such as `\tilde{x+y}` are rejected because their meaning is not specified by a symbol decoration.

Exact scalar arithmetic and exact matrix identities are retained where implemented. Some matrix algorithms use double precision even when the calculator precision is higher.

The numerical fractional-power and matrix-logarithm path supports Hermitian or unitary matrices up to dimension 64. It uses the principal phase in (-pi,pi], with +pi at the negative real axis. In `libqalculate/QuantumMatrixPower.cc`, normalized Hermiticity is checked at 1e-12, unitarity at 1e-11, and eigenvector residuals at 1e-10. Near-zero scaled Hermitian eigenvalues below 1e-13 are rejected for logarithms and negative powers. Positive powers also reject unresolved small eigenvalues. These are numerical acceptance thresholds, not error guarantees for arbitrary inputs; general nonnormal matrices are unsupported.

Entropy uses numerical state validation with tolerance 1e-12 and reports about 12 significant digits. Its default base is two. The authoritative implementation is `libqalculate/QuantumStateMetrics.cc`; increasing calculator precision does not make that numerical eigensolver arbitrary precision.

## Remaining coverage

- Finish the lesson-by-lesson IBM audit and the qBraid generated-program and learning-content audits. Account-only qBook contents have not been inspected.
- Resolve implicit register dimensions, general symbolic bit strings and sets, ensembles, general instruments, and automatic POVM/Naimark constructions.
- Extend programming support beyond the current bounded static OpenQASM importer. The app does not execute arbitrary Python, Qiskit or qBraid SDK programs, QIR, runtime classical feedback, cloud jobs, or pulse/timing programs.
- Address scale separately from syntax. The current circuit editor is limited to ten qubits and 512 steps; dense mathematical operations have their own limits. Accepting a notation does not make utility-scale simulation feasible.

The released executable can lag newly merged source changes until the next reviewed packaging run. Use the manifest revision to identify the actual build, rather than assuming that the latest repository feature is already installed.

## Symbolic Fourier operators

`QFT_N` and `fourier(N)` use dimension N, following [IBM's definition](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure). `qft(n)` and `QFT(n)` instead take a qubit count. Unknown scalar dimensions remain symbolic in exact and approximate modes; substituting a numeric dimension evaluates the matrix and applies the existing numeric limits. This does not yet provide symbolic basis kets, Fourier-sum expansion, or general symbolic operator identities.


### Symbolic states and application

An unknown named ket such as `|x>` remains a state expression until its name is assigned a column vector. An integer index requires an explicit dimension: `|x>_{N}` or `basis(x,N)`. Unknown scalar indices or dimensions remain symbolic; already-known invalid numeric arguments still reject. Products and adjoints involving unevaluated operators or states retain their operation structure and operand order. After values are substituted, the existing matrix evaluation and shape checks run. `QFT_N|x>` can therefore remain symbolic, but does not yet expand into the Fourier sum or infer that x is a numeric basis index.
