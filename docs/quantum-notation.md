# QuantumStudio research and coverage notes

The project goal is broad quantum-computing and quantum-programming notation support, including IBM Quantum Learning and qBraid learning materials. **That goal is not complete.** A working example or a green test suite does not establish whole-course or whole-language compatibility.

This note accompanies the executable. Its build revision is recorded in `build-manifest.json`. The offline `Notation-guide.html` describes implemented operations and their input limits. The source archive contains the corresponding implementation and tests.

## Complex conjugation overlines

The [IBM density-matrix basics lesson](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/density-matrix-basics)
uses an overline for complex conjugation in scalar products and density-matrix
entries. Quantum Notation accepts `\overline{1+2i}`, giving `1-2i`, and nested
overlines. For keyboard entry, `conj(1+2i)` has the same meaning. On a matrix,
conjugation acts on each entry without transposing it; the dagger remains the
conjugate transpose. Existing variable assumptions apply, including explicit
`complexparam(z)` for an unresolved complex parameter. Conjugation inside a
state label is not inferred: apply `conj` to the whole ket or bra.

## Unresolved traces

`Tr(A)` and `Tr(QFT_N)` remain symbolic until their operands are known.
The result display also uses `Tr(...)` inside scalar sums, powers, and comparisons,
for example `Tr(A) + Tr(B)` and `Tr(A) = Tr(B)`. Grouping is preserved;
Copy retains the canonical expression used for calculation.
Kets and bras bound by a symbolic sum use that sum’s displayed index name.
For example, a sum of `alpha_k|k>` displays `|k⟩`, with any index renaming
applied consistently to the coefficient, ket and summation index.
The result panel displays the trace notation, and Copy preserves the expression
for re-entry. Repeated traces can combine as scalar terms. For example,
`replace(Tr(QFT_N),N,4)` evaluates to `1+i`, and
`replace(Tr(A),A,[1,2;3,4])` evaluates to `5`.

A substitution must still produce a square matrix. Known scalar and non-square
operands are rejected, including a trace of another trace. Ordered products
such as `Tr(A*C*B)` remain symbolic; Copy preserves their original multiplication
order for later substitution. This does not infer matrix dimensions or distribute
a trace over arbitrary unknown products; those operations need compatible matrix
domains, which bare symbol names do not establish.

## Sources and audit method

The [IBM course catalog](https://quantum.cloud.ibm.com/learning/en/courses), checked on 2026-10-15, lists 15 courses. Discovering those courses is only an inventory step. Each lesson still needs its mathematical expressions, assumptions, register conventions, and executable code classified separately. The public qBraid notebook audit uses [qbraid-lab-demo revision 86787e1](https://github.com/qBraid/qbraid-lab-demo/tree/86787e1ba372facc224f925189755e69c479828b); it does not imply that the app executes the notebooks or their SDK calls.

For a formula, record the source, choose explicit finite dimensions and parameter values, and compare its result against an independently derived vector or matrix. Preserve the source syntax where possible. Record adaptations such as replacing an unspecified register dimension, rather than calling an adapted expression an exact paste. Keep malformed-input and convention checks alongside successful examples.

The source archive also contains `docs/learning-source-inventory.json`: 137 discovered IBM course sections, 12 modules, and 35 pinned qBraid notebooks. This is a work queue, not a compatibility certificate. The notebook hashes were rechecked against the pinned primary repository on 2026-10-15. Overview pages, exams, videos, linked material, and account-only content still require discovery and audit.

## Selected verified notation

Selected printed symbolic results can be pasted back into quantum input, including quoted names in `qfourier('N')`, named kets, and column matrices of Greek coefficients. Matching single or double quotes protect their contents from operator, superscript, and whitespace normalization. Unclosed quotes reject. Finite and set sums may rename their internal bound index when read again; substituting numerical dimensions or finite domains preserves their evaluated result. This is input round-trip support, not mathematical typesetting or a general symbolic simplifier.

**Copy result** uses a separate expression for matrices and vectors, retaining dimensions and explicit element separators while leaving the displayed grid unchanged. This avoids interpreting space-separated columns as multiplication. A one-element matrix retains its matrix shape, and copying includes elements beyond the 128-cell grid preview. The worker JSON exposes this as `copy_text`; `text` remains the display string. Existing input-size and complexity limits still apply. General symbolic output containing angle-unit names such as `rad` is not yet guaranteed to round-trip in quantum mode.

The [IBM phase-estimation procedure](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure) motivates these regression cases:

- Subscripted summation indices such as `a_0`, including nested binders and reused index names. See `src/quantum-parser-integration-test.cc`.
- Unbraced finite sums and products use multiplicative-term scope. For example, `\sum_{k=0}^{2} k+1` gives 4, while grouping `(k+1)` gives 6. Nested phase-estimation sums are covered by the integration tests.
- Finite sums with unresolved endpoints stay symbolic as `qsum` expressions. For example, `\sum_{k=0}^{N-1}{k}` is retained, and `replace(\sum_{k=0}^{N-1}{k},N,4)` evaluates to 6. Once numerical, bounds must be ascending integers; nested indices retain their scope. This does not yet derive general closed-form sums or support infinite ranges.
- Space-separated computational bits such as `|a_1 a_0>`: with phase parameter 1/4, the tested intermediate state after the first controlled operation is `[1;i;1;i]/2`. Each bit must evaluate to 0 or 1.
- TeX matrix row spacing such as `\\[1mm]`: the spacing is ignored, and the lesson's four-dimensional Fourier matrix is checked against `qfourier(4)`.
- The probability `|⟨101|(H⊗H⊗H)|000⟩|^2` equals 1/8. The packaged keyboard check verifies that Enter displays 0.125 once without inserting a newline.

These are selected finite examples, not certification of the entire phase-estimation lesson. In particular, source formulas can rely on implicit dimensions, named states, or mathematical definitions supplied earlier in the text.

## Sequential state evaluation

### Numerical circuit sampling

`QuantumNumericalState` provides the double-precision pure-state kernel used by the circuit editor's **Sample circuit** command. It stores up to 25 qubits under an explicit caller-supplied memory budget and applies one-, two-, or three-wire unitary matrices without constructing full-register operators. Wire 0 is the most significant bit; the first wire in a gate's ordered wire list is its local matrix's most significant bit. Matrices must be finite and unitary within a `1e-12` absolute column-inner-product tolerance. Cancellation during an update invalidates the partial state so it cannot be read or reused.

The editor accepts up to 25 qubits and 512 steps, including circuits loaded through the bounded OpenQASM importer. Sampling accepts unitary circuits with optional terminal measurements; noise, reset, mid-circuit measurement and feedback are rejected by this path. The sampling window accepts 1–100,000 shots and an explicit 64-bit seed. It displays the 128 most frequent outcomes and exports all counts through **Save counts**. Exact state and density-matrix inspection remains limited to ten qubits. A 25-qubit numerical state uses 512 MiB, with additional memory needed for sampling and results. This does not provide arbitrary notebook execution.

The GUI samples every qubit in register order, including when an imported circuit's terminal measurements select fewer wires. It does not reconstruct the imported program's classical-register output mapping. Direct worker callers can select and order measured wires as described below.

The design follows the state-vector and terminal-sampling distinction described by [qsim](https://quantumai.google/qsim/overview) and [IBM Statevector](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Statevector). The native regression suite compares local evolution with independently constructed full-register operators on small circuits. Original-scale audits belong in later validation stages rather than every commit's tests.

The internal `sampleCounts` operation draws terminal computational-basis outcomes without changing the state. It accepts an explicit ordered subset of wires and a 64-bit seed, returning counts keyed by integers whose most significant bit corresponds to the first listed wire. An empty subset yields outcome zero; zero shots yields no counts. The kernel's shot limit is 1,000,000 (the GUI uses the lower limit above), and temporary sample storage and returned counts are additional to the state memory budget. Sampling checks cancellation and rejects normalization error above `1e-8`; it does not implement mid-circuit collapse or classical feedback.

### Symbolic sequence expressions

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

## Selected qBraid Deutsch–Jozsa audit

The pinned [PyQASM Deutsch–Jozsa notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/deutsch_josza_unroll.ipynb) contains a five-qubit OpenQASM 3 program using custom gates, a subroutine, loops, an ancilla and measurement. Its notebook SHA-256 is `a91a11fbe445b73631fecf42ea4d2aebba35f2eeeb6691898373dec514528f14`; the extracted `qasm` literal, encoded as UTF-8 with LF newlines, hashes to `6bcc0b2452e4bfb56f1b8124d8156b5cb173e20728db1be84d87b958ebc02b08`.

Release `482ef2f3390ceb1967224f1acfbc95636a26e797` imported the original program into 18 editor steps. The packaged editor loaded, saved and reloaded it, and the packaged worker matched the complete expected 32-by-32 density matrix. Seventeen explicitly adapted cases also passed: the other 15 four-bit linear oracles and two affine variants with an additional oracle X on the ancilla. All 18 reported zero residual in approximate mode. For an oracle `f(x)=a·x ⊕ b`, the independently specified expected state has data register `|a>` and ancilla `|->`; measuring the data register preserves this density matrix.

The first audit harness used literal 32-by-32 expected matrices and all 18 comparisons exceeded the expression complexity limit. Replacing each expected matrix with the density of its explicitly specified 32-entry state retained the full-matrix comparison and passed. The parser limit was not changed. These are selected released-program observations, not maintained CI replay cases or certification of notebook Python execution, all subroutines, or every Deutsch–Jozsa oracle.

## Large density-matrix comparisons

`frobeniusnorm(A)` and Schatten order 2 support finite numeric matrices up to 1024 by 1024, including ten-qubit density matrices. This path sums squared entry magnitudes directly and checks cancellation during the scan; it does not allocate a vectorized copy or compute singular values. Other Schatten orders, trace norms and spectral norms retain the 1024-entry bound. `vec` retains its own 1024-entry limit, so use `frobeniusnorm(A-B)` to compare large density matrices. Numerical precision and finite-entry validation still apply.

### Frobenius uncertainty

Frobenius norms propagate finite real and complex interval entries through squared magnitudes and the square root. This preserves bounds for cancellation residuals near zero and for explicitly uncertain entries, instead of requiring 12 significant digits in each entry. The resulting value may be an interval. Other Schatten orders retain their existing broad-uncertainty rejection.

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

Quantum mode recognizes `Hz` and its library-defined prefixes, including `kHz`, `MHz`, `GHz`, and `mHz`. For example, `sqrt(8*25GHz*0.5GHz)-0.5GHz` gives `9.5 GHz`. Prefixes are case-sensitive. Quoted `'GHz'` remains a symbolic name, and gate symbols such as `H` retain their quantum meanings. This adds frequency units; arbitrary physical-unit expressions should still use ordinary calculator mode.

In quantum mode, `sin`, `cos` and `tan` take radians, regardless of the ordinary calculator's angle setting. The suffixes `rad` and `deg` mean factors of `1` and `pi/180`, respectively: `cos(pi rad)` gives `-1`, `sin(30 deg)` gives `1/2`, and `Rz(180 deg)` equals `Rz(pi)`. Quoted identifiers such as `'rad'` retain their literal meaning. Symbolic trigonometric results retain explicit radian units, so later substitution uses the same convention. Ordinary calculator-mode angle settings remain unchanged.

`\sin^{-1}(x)`, `\cos^{-1}(x)` and `\tan^{-1}(x)` mean the inverse trigonometric functions, matching the notation used in IBM's Grover analysis. The explicit commands `\arcsin`, `\arccos` and `\arctan` are also accepted. In quantum mode these commands and `asin`, `acos`, `atan` return dimensionless radian values, preserving the library's principal branches. For example, `asin(1/2)` gives `pi/6`. The internal functions are `qasin`, `qacos`, and `qatan`; unresolved calls retain the radian convention when evaluated after substitution. Ordinary calculator-mode inverse trig behavior is unchanged.

Other superscripts apply to the function result: `\sin^2(pi/6)` gives `1/4`, and `\sin^{-2}(pi/6)` gives `4`. The inverse interpretation applies to the literal exponent `-1`; write `(\sin(x))^{-1}` for a reciprocal. Powered functions require a parenthesized or braced argument, optionally with TeX delimiter-sizing commands such as `\left` or `\biggl`. Unbraced powered-function arguments remain unfinished.

## Quantum addition and subtraction

In quantum mode, addition and subtraction require matching matrix dimensions. A ket cannot be added to an operator, and a row vector cannot be added to a column vector by broadcasting. Nonzero scalar additions to matrices also reject: write an explicit identity or constant matrix for the intended operation. Scalar zero remains an additive identity, and ordinary symbolic scalar arithmetic is preserved. These checks apply to the quantum notation parser; ordinary libqalculate expressions retain their existing behavior. Unresolved non-scalar expressions remain deferred until their dimensions can be evaluated.

## Finite set-indexed sums

Finite membership uses `x ∈ S` or `x \in S`, with `∉` / `\notin` for nonmembership. The function spelling is `member(x,S)`. Collections may contain scalar values or typed binary labels, with at most 1024 entries; bare scalars and matrices are rejected as collections. Binary labels compare by width and value, so `bitstring(1,3)` is not a member of `bitstrings(2)`. Exact scalar equality is used, and undecidable symbolic equality reports an error rather than a false result. Membership predicates can also appear inside set filters. Infinite and general symbolic domains remain unfinished.

`union(A,B)`, `intersect(A,B)` and `setdiff(A,B)` accept finite collections of binary-string labels, including empty and singleton collections. Labels compare by width and value. The optional third argument `1` uses multiset multiplicities: maximum for union, minimum for intersection, and nonnegative subtraction for difference. Each input and output is limited to 1024 entries. Use `vector(...)` for explicit label collections. The operators `\cup` / `∪`, `\cap` / `∩` and `\setminus` / `∖` call union, intersection and difference. Intersection and difference bind more tightly than union; repeated intersection/difference operators associate left to right. Use parentheses to override this grouping. `\emptyset`, `\varnothing` and `∅` denote an empty vector set. For example, `cardinality(\{0,1\}\cup\{1,2\})` gives `3`. Cardinality bars accept compound expressions that begin with an explicit set or a `vector(...)` call, for example `|\{0,1\}\cup\{1,2\}|` gives `3`, and `|∅|` gives `0`. Nested predicates may contain bra–ket bars. Bars also accept named finite collections and parenthesized set expressions: |S| counts distinct members, while |S> remains a ket. Scalar bars evaluate absolute value, so |-3| is 3 and |3+4i| is 5. Flat collections use cardinality rather than a vector norm; use norm(...) for the latter. Matrix bars (including determinants), general symbolic set algebra, and infinite sets remain unfinished.

A named nonempty collection of binary-string labels can be used as a set ket, following the uniform-state convention in [IBM's Grover analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/analysis). `|S>` normalizes the sum of the distinct basis states in `S`; `<S|` is its adjoint. The function spelling is `qketstate(S)`. For example, `qketstate(vector(bitstring(0,2),bitstring(3,2),bitstring(0,2)))` gives `[1;0;0;1]/sqrt(2)`. Repeated labels do not increase amplitudes. All labels must have the same width, and the collection is limited to 1024 entries. Empty sets and mixed-width sets reject. Existing column-vector kets retain their amplitudes. Arbitrary symbolic alphabets and sets of nonbinary labels remain unfinished.

The explicit binary Cartesian domain `\{0,1\}^n` enumerates bit strings of width `n`, preserving leading zeros. Widths must evaluate to integers from 0 through 10; width zero contains the empty string. `bitstrings(n)` is the function spelling. These domains work in finite sums: `\sum_{x\in\{0,1\}^2}{|x>}` yields `[1;1;1;1]`, and the corresponding sum of `|x><x|` is `identity(4)`. A typed label supplies its own ket dimension. Reversing or repeating the alphabet's entries does not change the domain.

Internally, `bitstring(value,width)` constructs a width-carrying label, rather than an integer or state vector. `bitvalue`, `bitdot` and `bitxor` accept these labels. XOR of two labels preserves their width; mixing a label with an existing bit vector returns a bit vector. Dot products return parity, and binary operations require equal widths. The empty string has integer value zero and dot product zero with itself; its XOR with itself is the empty string. For example, `qketstate(bitxor(bitstring(5,4),bitstring(6,4)))` produces `|0011>`. Filtered binary domains work with concrete predicates, including empty and singleton results: `|\{x\in\{0,1\}^3:bitvalue(x)<3\}|` gives `3`. Duplicate labels compare by both width and value; `01` and `001` remain distinct strings. Label sets contain at most 1024 entries and are ordered first by width, then integer value. For an explicit list of labels, use `vector(bitstring(1,2),bitstring(1,3))`; square brackets currently route these non-scalar entries through matrix concatenation and reject them. General arithmetic on descriptors, arbitrary Cartesian alphabets, implicit definitions of `Sigma`, and unbounded materialization remain unfinished. Unsupported literal alphabets reject instead of being interpreted as vector powers. This does not establish whole-lesson compatibility.

Symbolic values and widths in `bitstring(x,n)` stay as typed labels until supplied. `bitvalue`, `bitxor`, `bitdot`, and `qketstate` preserve unresolved labels, including finite sets of labels. Set cardinality, finite sums and membership also remain unresolved until the typed labels are concrete, so later duplicate labels are not counted twice. Copy retains the constraints: substituting a negative/fractional value, a width outside integer 0 through 10, an overflowing value, or incompatible concrete widths rejects. For example, `replace(replace(qketstate(bitstring(x,n)),x,1),n,3)` gives `|001>`. This keeps the existing finite width limit; it does not implement arbitrary symbolic Cartesian domains, symbolic union/intersection/difference, literal-set deduplication of unresolved labels, or indexed-register concatenation.

Cardinality bars around an explicit finite set, such as `|\{0,1,1\}|` or `\lvert\{0,1,1\}\rvert`, give `2`. Empty sets count as zero. Ranges and filtering comprehensions also work: `|\{k\in\{0,\ldots,7\}:k>3\}|` gives `4`. Use `cardinality(S)` for a named finite flat scalar collection.

An unspecified domain in `\sum_{a\in\Sigma}{|a>}` remains symbolic as `qsumset`. Bars around a bare unknown remain `qbars`, so substitution can select scalar magnitude or distinct-member cardinality. For example, `replace(|S|,S,-3)` gives `3`, while `replace(|S|,S,vector(2,3,3))` gives `2`. IBM's uniform-state expression `1/sqrt(|\Sigma|)\sum_{a\in\Sigma}{|a>}` stays symbolic; substituting `bitstrings(1)` for `\Sigma` gives `|+>`. Concrete domains still require at most 1024 scalar or typed binary-string entries. This does not infer dimensions for arbitrary scalar basis labels or implement arbitrary symbolic set operations.

Counting uses the existing finite-set sum evaluator with summand `1`, including its 1024-entry limit, exact evaluation and structural duplicate comparison. This is not a new typed symbolic set system: general equality of unresolved symbolic members, Cartesian powers, infinite sets and sets of vectors remain unfinished. Column states and operators must not be treated as finite scalar collections.

A finite sum over the complete integer range `k=0,...,d-1`, with `1 <= d <= 1024`, supplies dimension `d` to bare `|k>` and `<k|` in its body. Thus IBM's decimal-digit state `\frac{1}{\sqrt{385}}\sum_{k=0}^9 (k+1)\vert k\rangle` evaluates directly to `[1;2;3;4;5;6;7;8;9;10]/sqrt(385)`. Explicit dimensions take precedence, and nested binders retain their own index scope. Symbolic bounds remain unevaluated until supplied. Partial ranges, transformed indices such as `|f(k)>`, arbitrary alphabets, and context outside the sum still require a dimension or typed basis labels. The basis constructor accepts dimensions 1 through 1024. A one-dimensional basis is the 1-by-1 column matrix `[1]`, consistent with a zero-width binary label; it remains a matrix in the worker result. `QFT_1|0>_1` and a complete sum with only index zero therefore work.

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
- Extend programming support beyond the bounded OpenQASM importer. Runtime bit-register operations, typed integer arithmetic, scoped integer/Boolean storage, integer `switch` selection, bounded runtime `while` loops and integer `for` ranges are implemented. Loop transfers and whole-program `end` are preserved. Dynamic wire indexing, runtime gate parameters, runtime iteration over sets or arrays, and subroutine-local storage remain unsupported. The app does not execute arbitrary Python, Qiskit or qBraid SDK programs, QIR, cloud jobs, or pulse/timing programs.
- Address scale separately from syntax. The circuit editor supports up to 25 qubits and 512 steps for numerical sampling, with exact state and density-matrix inspection limited to ten qubits; dense mathematical operations have their own limits. Accepting a notation does not make utility-scale simulation feasible.

The released executable can lag newly merged source changes until the next reviewed packaging run. Use the manifest revision to identify the actual build, rather than assuming that the latest repository feature is already installed.

`complexparam(x)` represents an explicitly general complex scalar parameter,
including possible real values. Use it for amplitudes whose imaginary parts
are unknown, for example `density(complexparam(α)|0>+complexparam(β)|1>)`.
The wrapper preserves conjugation and remains in printed expressions. A
numeric substitution such as `replace(complexparam(α),α,i/sqrt(2))` evaluates
to that number. Its argument must be one unknown symbol or a finite numeric
expression; wrap separate symbols individually rather than a compound
unknown expression. Ordinary unwrapped symbols retain the calculator's
existing assumptions. This helper does not yet provide a symbol-declaration
editor or automatically infer domains from lesson notation.

### Products of summation indices

In TeX or Unicode sums, adjacent letters multiply when every letter names an active single-letter index: `∑_{x=0}^{2}{∑_{y=0}^{3}{xy}}` evaluates to `18`. This also supports the `xy` exponent in IBM's double-sum Fourier definition, braced and unbraced bodies, finite set sums, and products. Nested index declarations retain their own scope, including a multi-letter index named `xy`.

Use a quoted name such as `"xy"` for one named variable inside these sums. Ordinary `sum(...)` input retains its existing identifier rules. Function names, gates, `pi`, frequency units, subscripts, and quoted state labels are not split. A token containing a letter that is not an active index remains a named variable; use `x*y` when the intended multiplication is otherwise ambiguous.

## Symbolic Fourier operators

`QFT_N` and `fourier(N)` use dimension N, following [IBM's definition](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure). `qft(n)` and `QFT(n)` instead take a qubit count. Unknown scalar dimensions remain symbolic in exact and approximate modes; substituting a numeric dimension evaluates the matrix and applies the existing numeric limits. Explicitly dimensioned symbolic basis actions expand as described below; general symbolic operator identities remain unfinished.


### Symbolic states and application

An unknown named ket such as `|x>` remains a state expression until its name is assigned a column vector. An integer index requires an explicit dimension: `|x>_N`, `|x>_{N}` or `basis(x,N)`. A single identifier (including a subscripted name or Greek letter) can be written without braces; compound dimensions still require grouping, such as `|x>_{N+1}`. Bare Greek scalar letters (including TeX spellings) denote symbolic parameters in quantum mode, so `\alpha|0>+\beta|1>` retains both amplitudes and `\theta` remains a phase parameter. The exception is `π`/`\pi`, which remains the numerical constant. Use the Latin name `alpha` for the physical constant formerly reached through `α`; explicit function calls such as `δ(x)` and `θ(x)` retain their meanings. Ordinary calculator mode is unchanged. Bound Greek indices still take their summation values, and `replace(\alpha,\alpha,1/2)` supplies a numerical value to a symbolic parameter. Numeric dimensions must satisfy the integer-dimension checks. This suffix explicitly denotes a basis dimension. A following power or adjoint applies to the state, so `|x>_N^2` means `(|x>_{N})^2`. Unknown scalar indices or dimensions remain symbolic; already-known invalid numeric arguments still reject. Products and adjoints involving unevaluated operators or states retain their operation structure and operand order. After values are substituted, the existing matrix evaluation and shape checks run. `QFT_N|x>` can therefore remain symbolic, but does not yet expand into the Fourier sum or infer that x is a numeric basis index.


### Repeated adjoints, conjugations and transposes

The transpose suffix `^T` requires a complete `T` token. A trace function in
an exponent remains a function: `2^Tr(I)` evaluates to `4`. Use a separator
when multiplying after a transpose, for example `A^T*B`.

Applying an adjoint twice, conjugation twice, or transpose twice cancels symbolically, including for unresolved state and operator expressions. For example, `dagger(dagger(QFT_N))` reduces to `QFT_N`, and `dagger(dagger(|x>))` reduces to `|x>`. These identities do not assume normalization, reality or unitarity; they do not replace a single adjoint with an inverse.

## Named state labels

`|GHZ>` (or `|GHZ⟩`) is built in: it means the normalized three-qubit state
`(|000>+|111>)/sqrt(2)`. No entry in **States** is required. `<GHZ|` is its
bra, `<GHZ|GHZ>` gives `1`, and measuring all three qubits gives `000` or
`111` with probability one half each. The name is case-sensitive and reserved;
use a different name for a custom state or a GHZ state with another qubit count.

Multi-character ket and bra labels are preserved as single names, including `|Bell>`, `|psi>` and `|after CZ>`. An undefined label stays symbolic; it is not interpreted as multiplied letters or a calculator function. Names with internal spaces remain distinct from names without spaces. Explicit variables registered through the library API are resolved as states and must satisfy the existing column-vector or binary-label-set checks. In the GUI, choose **States** beside Calculate to define named column vectors.

`Bell` is not a predefined alias or a normalization assumption. Use `<Phi+|Phi+>` for the built-in normalized Bell-state overlap (1), and `<Phi+|CZ|Phi+>` for its overlap after CZ (0).

### Worker state definitions

State families use a declaration such as `psi(alpha)` with the
expression `cos(alpha)|0>+sin(alpha)|1>`. Enter it in **States**, then evaluate
`|psi(pi/8)>`, `<psi(0)|psi(pi/2)>`, or `|psi(t)>`. The parameter is local to the
definition; Greek parameters such as `α` and subscripted identifiers such as
`theta_1` are supported. A symbolic argument retains symbolic amplitudes. Families share the
existing definition order, finite column-vector limits and session storage.
An undeclared family stays symbolic, without an assumed normalization or
orthogonality. Families take 1 to 16 distinct scalar parameters. For example, declare
`psi(theta,phi)` as `cos(theta/2)|0>+exp(i*phi)*sin(theta/2)|1>` and evaluate
`|psi(pi/2,pi/2)>` for the positive Y state. Arguments substitute simultaneously,
so `pair(y,x)` does not overwrite one argument with the other. Subscript calls include
`|psi_{pi/8}>` and `|psi_t>` and work inside Dirac macros such as
`\ket{\psi_{\pi/8}}` when the corresponding family is declared. Compound
subscripts require braces. Simple subscript labels retain their existing
symbolic meaning without a declared family; explicitly defined fixed states
such as `psi_t` take precedence over a family call.

Declare complex amplitudes in a family name with `:complex`, for example
`psi(a:complex,b:complex)` with body `a|0>+b|1>`. Calls use ordinary values:
`|psi(1,i)>`. Symbolic calls such as `density(|psi(x,y)>)` retain conjugation
when values are substituted later. Parameters without a domain keep the
calculator's default real assumption; `psi(a:complex,theta)` can mix a complex
amplitude with a real angle. The declaration applies only to free occurrences
in the body, not to a nested sum's bound index. Existing `complexparam(a)`
annotations remain valid. A family is not automatically normalized.

The worker's `--states` option accepts definitions alongside one expression. Define
`Bell` as `|Phi+>` and then `after CZ` as `CZ|Bell>` to evaluate `<Bell|Bell>`
to 1 and `<Bell|after CZ>` to 0. Definitions are evaluated exactly, in order,
and may refer to earlier definitions. Each must resolve to a column vector with
1–1024 rows and scalar amplitudes. Symbolic amplitudes are allowed. Vectors are
not automatically normalized, and names cannot override existing variables or
built-in ket labels. Unknown references, forward references and cycles reject.
Definitions last for one worker request. Version 2 GUI session files store exact
state definitions in a `States` array of `Name` and `Expression` objects, both
for the current workspace and for each history entry. Opening a session restores
its definitions; reusing a history entry restores the definitions from that
calculation. Version 1 files still load with no definitions. Invalid files leave
the current workspace unchanged. The GUI sends the restored definitions with
each calculation. Choose **States** beside Calculate to edit definitions, reorder
dependencies, or add the Bell example. **Apply states** updates the workspace;
**Cancel** discards the private draft. Use **Save session** to keep definitions.
The editor checks names and size limits; Calculate checks whether the expressions
resolve to valid vectors. Errors leave the definitions available for correction.

The UTF-8 stdin protocol begins with `QSTATES1\n`, then a decimal definition
count and newline. For each definition, send its name's byte length and newline,
its expression's byte length and newline, then the raw name and expression bytes
without separators. The remaining bytes are the calculation expression, including
the `quantum:` prefix when using quantum notation. Definition expressions use
quantum notation automatically and do not include that prefix. Limits are 32
definitions, 128 bytes per name, 32768 bytes per definition or final expression,
and 1100000 bytes for the entire request. Names may contain internal spaces;
definition expressions may contain newlines. NUL is rejected in names and
expressions. Empty fields, invalid lengths and incomplete records reject without
producing a result. Without `--states`, the existing expression-only protocol and
32768-byte limit are unchanged.


### Numerical sampling worker protocol

`quantum-worker --sample` accepts one `QSAMPLE1` request on binary UTF-8 stdin
and returns JSON. It is a separate numerical mode; ordinary symbolic calculation
is unchanged. The circuit editor's sampling window uses this protocol, including
for supported imported OpenQASM circuits.

The request begins with `QSAMPLE1\n`. Unsigned decimal integers terminated by LF
follow: qubits (0–25), shots (0–1,000,000), 64-bit seed, measured wire count, each
measured wire, and gate count (0–4096). Each gate contains its target count
(1–3), each target wire, its expression's UTF-8 byte length (1–4096), and exactly
that many expression bytes. No separator follows expression bytes. Total input
is limited to 1,100,000 bytes. Trailing data, duplicate or out-of-range wires,
NUL expressions, and combined CLI flags fail. Wire 0 is the most significant
state bit; the first gate target is the local matrix's most significant bit.
The first measured wire is the leftmost output bit, regardless of wire order.

The initial state is all-zero. Each local gate is evaluated through libqalculate
and must be a finite numerical unitary of matching dimensions. Unknown
parameters, broad intervals, and nonunitaries are rejected. Narrow rounding
intervals around zero use an absolute width tolerance of 1e-14; the kernel still
checks unitarity. State storage is capped at 512 MiB; gates, samples, and output
counts require additional memory. Only terminal computational-basis sampling is
supported here, without collapse, mid-circuit measurement, reset, or classical
feedback. Callers cancel by terminating the one-request worker process.

The response contains `qubits`, `shots`, `seed` (a decimal string preserving all
64 bits), `wires`, and `counts` (bit strings mapped to integers). Leading zeros
are preserved. An empty measured subset has outcome `""`; zero shots returns
empty counts. Failures write stderr diagnostics and exit nonzero without partial
JSON. Native CI tests this protocol; packaging repeats those tests against the
bundled executable.


#### Dynamic trajectory requests

The same `--sample` entry point also accepts `QSAMPLE2\n`. The circuit sampling window
uses QSAMPLE2 for mid-circuit measurement, reset and feedback, and QSAMPLE1 for
unitary circuits with optional terminal measurements. QSAMPLE2 follows
with LF-terminated unsigned integers: qubits, shots, seed, classical bit count
(0-64), output bit count, each output classical bit, and step count. The size,
shot, qubit, expression, gate-target and step limits match QSAMPLE1.

Each step begins with an integer kind and then these fields:

| Kind | Following fields |
| --- | --- |
| 0: gate | The QSAMPLE1 gate payload (target count, targets, byte length, expression) |
| 1: measurement | Quantum wire, destination classical bit |
| 2: reset | Quantum wire |
| 3: conditional gate | 64-bit mask, 64-bit value, then the gate payload |
| 4: channel | Target count, targets, byte length, Kraus-vector expression |
| 5: readout assignment | Classical target count, targets, byte length, probability-matrix expression |
| 6: branch | Mask, value, true-body count and operations, false-body count and operations |

Every shot starts with all-zero quantum state and classical memory. A measurement
collapses its wire and overwrites the destination bit. Reset returns its wire
to zero without changing classical memory. A conditional gate runs when
`(classical_memory & mask) == value`; masks must fit the classical register and
values must be subsets of the mask. Even unreachable gates must be valid
numerical unitaries. Classical bit 0 has weight 1 in masks, independently of
quantum wire order. No implicit final measurements occur. A channel expression, such as
`amplitude_damping(0.5)`, must evaluate to a vector of 1-256 finite square Kraus
matrices matching its one to three target wires. Their completeness relation
must hold within the numerical tolerance. Each shot samples and normalizes one
Kraus branch without changing classical memory. The GUI uses this operation for AD, GAD, PD, PAD, Depol and Thermal noise controls.

A readout assignment changes only the recorded
bits, without measuring or changing the quantum state. It accepts one to eight
distinct classical targets and a real square matrix with row `m` containing
`P(recorded n | true m)`. The first target is the most significant bit in each
matrix index. Entries must be in `[0,1]` and each row must sum to one within
`1e-12`. Subsequent conditions use the changed records. For example,
`[0.9,0.1;0.2,0.8]` records a true zero as one with probability 0.1, and a true
one as zero with probability 0.2. The classical editor exposes mid-circuit
readout assignment as **Readout error**. The legacy sampling window offers an
optional final readout assignment over up to eight selected bits. This runs
after final measurements and does not alter earlier feedback. JSON exports
include the captured model, seed and counts. CSV exports include the model as
JSON in `run_final_readout` on the first data row only; it applies to the entire
run. Later rows leave that cell empty to avoid repeating large matrices.

The response adds `classical_bits`; `wires` now identifies the requested classical
bits in left-to-right output order. The explicit ordering avoids relying on a
SDK's display convention. The GUI maps measurement records to the corresponding
wire index, then appends final measurements for the displayed output wires.
Its feedback operations measure their control wires at that step, matching
exact `feedforward()` semantics; they do not refer to an earlier measurement.
Noise sampling uses the same channel expressions as exact density evolution. Identical requests reproduce counts using the same
backend version. Errors return no partial counts; process termination cancels.

### Library ABI compatibility

One-dimensional quantum states and operators retain their 1-by-1 matrix shape. The new `MathFunction::preservesSingletonMatrix()` virtual hook changes the C++ ABI; the libtool interface version is 27:0:0. Rebuild clients and derived function classes against this library rather than loading them from a previous ABI. Ordinary singleton-vector evaluation retains its existing behavior.

### Named basis labels in IBM examples

The card-suit commands `\clubsuit`, `\diamondsuit`, `\heartsuit`, and `\spadesuit` map to `♣`, `♢`, `♡`, and `♠`. The [IBM single-system lesson](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/quantum-information) uses these as classical basis labels. Undeclared labels remain named symbolic states; the parser does not assume that arbitrary named vectors are orthogonal.

Supply the chosen coordinates by replacing whole kets, for example `replace(|\clubsuit>,|\clubsuit>,|0>_4)`. Replacing the four suit kets with `|0>_4`, `|1>_4`, `|2>_4`, and `|3>_4` evaluates the lesson's superposition to `[1;i;-1;-i]/2`, with norm 1. This declares the basis ordering explicitly; it is not automatic inference from a sum's domain. The same whole-ket substitution works for multi-letter names such as `|high>`. General symbolic basis declarations and automatic orthogonality remain unfinished.

### Symbolic adjoint composition

Transpose, entrywise conjugation and adjoint compose symbolically: transpose followed by conjugation is adjoint, adjoint followed by conjugation is transpose, and adjoint followed by transpose is conjugation. These pairs commute, and applying any one operation twice returns its operand. For example, `(QFT_N^*)^T` reduces to the adjoint of `QFT_N` without supplying N. The underlying expression remains present, so substituting an invalid Fourier dimension still rejects it. General symbolic unitary-product simplification remains unfinished; explicitly dimensioned Fourier basis actions expand as described below.


The native trajectory API additionally supports `TrajectoryStep::branch(mask,
value, whenTrue, whenFalse)`. It snapshots both bodies and selects exactly one
body at entry using the saved classical bits. Measurements or readout errors
inside that body can change later conditions without changing the already
selected body. Validation checks both bodies even at zero shots, counts all
nested operations toward the 4096-step limit, and allows at most 32 nested
branches. The worker exposes these blocks as QSAMPLE2 operation 6. Body counts include
only their immediate operations; all nested operations in both bodies count
toward the shared 4096-operation limit. Every field and body is required even
when it would not execute. The classical OpenQASM importer preserves nested
branches; its expression-capable requests use QSAMPLE3.

The Windows sampling adapter also exposes `RequestClassical` / `RunClassical`
for callers that need saved classical records. These accept an independent
0–64-bit classical register and an explicit output-bit order (first bit most
significant), and require a `ClassicalBit` destination on every measurement.
They do not append final measurements. Conditions and readout assignments use
classical bit indices; gate and reset targets use quantum wire indices.
`ReadClassicalResult` validates the independent classical register size.
The existing editor sampling API retains its final-quantum-measurement behavior.
The classical editor and circuit files preserve named registers, runtime
branches and their saved measurement destinations.

The explicit classical-output Windows adapter accepts `Operation.Branch` with
`Mask`, `Value`, `WhenTrue` and `WhenFalse`. Both bodies are required, including
an empty body for an omitted else clause. The adapter serializes nested bodies
before starting the worker, validates every body, limits nesting to 32 levels,
and shares the 4096-operation limit across the whole request. Cyclic mutable
input graphs fail the nesting check. Branches require the branch-capable worker
protocol; they are not available through the legacy final-measurement API.
Runtime OpenQASM branch lowering remains separate from this adapter support.

`ClassicalCircuit` provides a version-2 storage model for the forthcoming
classical circuit editor. `Registers` lists distinct named registers in bit
allocation order: the first register starts at bit zero, and subsequent
registers follow it. `OutputBits` specifies the displayed bit order. `Steps`
stores operation names, expressions, wires, measurement destinations and nested
branch bodies. Condition masks and values are unsigned decimal strings, so bit
63 survives JSON consumers that cannot represent every 64-bit integer exactly.
Documents are limited to 256 KiB, 64 classical bits, 512 total steps and 32
branch levels. Loading validates both branch bodies and rejects unknown fields
and incorrectly typed values before returning a program. Snapshots and sampling
operations are copies; editing them cannot mutate the validated program.
Matrix expressions are evaluated and checked by the worker when run.
The classical editor uses this model for Save, Open and OpenQASM import;
existing version-1 circuit files keep their current behavior.

The sampling window also accepts a captured `ClassicalCircuit`. It displays
register names in the selected output order and samples the saved classical
record without appending final quantum measurements. An empty output selection
is displayed as `(empty)`. Readout operations are part of the stored program;
the legacy final-readout controls are not shown for this mode. JSON sampling
exports use `QuantumStudio.sampling.v2` and include the captured circuit. CSV
exports include that circuit once in `run_classical_circuit`, on the first data
row. Open this mode from Circuit composer → Classical circuit → Sample.

The classical editor supports named register settings, explicit output order,
gates, measurement destinations, resets, noise channels, readout assignments and
nested Then/Else bodies. Select a body to append an operation, or an operation
to replace/delete it. Replacing a branch preserves its children; changing it to
another operation requires empty bodies. Invalid edits leave the program and
undo history unchanged. Undo retains the latest 64 edits. Opening a validated
file resets history, and opening or closing asks before discarding unsaved work.
Save replaces an existing file atomically. Use **Sample** for sampled classical
records or **Exact probabilities** for
exact classical-record evaluation with fractions and symbolic parameters.
**Import OpenQASM** preserves the supported runtime operations described below.

The classical importer uses the compiler's `preserve_branches` unrolling path.
It preserves whole branches, including both bodies and saved measurement
destinations, and lowers supported bit expressions without evaluating them
at import time. This avoids the pinned compiler's reversed indexing
when expanding register comparisons: OpenQASM uses little-endian register to
integer conversion ([types specification](https://openqasm.com/versions/3.0/language/types.html)).
Runtime-register comparisons and ordered unsigned comparisons are supported
in this path. The legacy version-1 importer is unchanged; the classical editor
uses this path for version-2 import.

Choose **Import OpenQASM** in the classical editor, with either the IBM/Qiskit
or published OpenQASM 3 U convention. Import preserves declared bit-register
names, measurement destinations, resets and nested bit-expression branches.
Outputs default to descending global bit indices, with register names displayed
in the sampling window; this order is editable. A discarded measurement is
represented as complete phase damping, preserving its quantum effect without
inventing a saved output. Import is undoable and validates before changing the
current program. The compiler CLI exposes the same conversion as `--classical`.
Current limits are 25 qubits, 64 classical bits, 512 operations and 32 branch
levels. Supported runtime bit operations include assignments (including
overlapping slices), initializers, bitwise operations, shifts, unsigned
comparisons, `popcount`, `rotl` and `rotr`. Assignments evaluate the whole
right-hand side before writing targets. Programs with no qubits can use these
classical operations and both evaluation modes. Typed runtime integer arithmetic
and bounded data-dependent `while` loops and integer `for` ranges are supported as described below.
Shift counts also accept unsigned integer variables and explicit casts, such as
`c << uint[8](distance)`, following the
[OpenQASM unsigned shift-count rule](https://openqasm.com/versions/3.0/language/classical.html#classical-bits-and-registers).
Counts retain their full value; shifting by at least the operand width yields
zero. Signed integer counts require an explicit unsigned conversion.
Dynamic wire indexing and measurement-driven gate angles
remain unsupported and are rejected explicitly.

### Classical-expression export groundwork

`ClassicalExpressionQasm` serializes the immutable bit and integer expression
models to standard OpenQASM 3 syntax. It validates register bounds and integer
slot types before producing text, using canonical storage names `c` and `vN`.
Machine-sized integers are emitted as explicit 64-bit types to preserve
QuantumStudio's semantics across targets. Arithmetic and comparisons retain the
model's promotion rules; bit selections retain their order and repeated indices.

This is an internal component, not a classical-editor export command. Full
program export still needs declarations, control flow, variable lifetimes,
output ordering, and explicit handling of unsupported operations. Tests generate
39 expressions for frozen-compiler validation; packaged tests also check their
exact and sampled outcomes.

`ClassicalQasmStorage` adds an optional logical-to-physical bit mapping for
that serializer. Selected outputs occupy an explicit `output bit` register in
the requested order; working bits occupy separate scratch storage without
duplicating the bit bank. Assignments evaluate their complete right-hand side
before changing any target. Ten generated programs check overlapping writes,
repeated reads, output order, empty results, and the 64-bit boundary in exact
and sampled execution. An undefined-read case verifies that empty results do
not suppress execution errors. This requires the explicit-output and local-scope
importer support.

This component is not yet connected to whole-program export. With working bits
but no selected outputs, it places storage and operations in a local block so
the scratch bits do not become program results. Empty storage is also allowed.
Expanded expressions remain subject to the importer's complexity
limits. Control flow, integer lifetimes, and the editor export command remain
unfinished.


### Native integer value groundwork

`QuantumClassical::Integer` is a native value layer for future runtime integer
expressions. It is not connected to the OpenQASM importer or GUI. Values carry
explicit signedness and a width of 1–64 bits. Operations require matching types;
parsing and register storage belong to the future expression layer.

Unsigned arithmetic wraps modulo the declared width. Signed arithmetic reports
overflow, including the minimum signed value divided by -1 (also for remainder).
Division truncates toward zero and the remainder has the dividend's sign.
Zero divisors report an error. Powers take a nonnegative integer exponent;
a zero exponent produces one if that value fits the result type.

Explicit integer casts preserve low bits when narrowing and sign-extend negative
signed sources when widening. Same-width signed/unsigned casts preserve the bit
pattern. The narrowing behavior is a QuantumStudio policy: OpenQASM leaves
out-of-range standard-type conversions implementation-specific
([casting rules](https://openqasm.com/versions/3.1/language/types.html#casting-specifics)).
The implementation uses unsigned bit patterns and checked signed operations,
without relying on host signed overflow.

`IntegerType` and `TypedInteger` retain explicit versus unspecified width as
separate identities. Their target policy uses 64-bit unspecified integers and
ranks explicit-width integer types below the machine type of equal width.
Integer promotion therefore uses signed machine integers whenever their range
contains the operand type, and unsigned machine integers otherwise. Mixed
arithmetic and comparison first convert both operands to their common type.
For example, `int[8](-1)` compares below `uint[8](255)`, while a signed machine
-1 compares equal to the largest unsigned machine integer after conversion.
This is an explicit target policy, not a claim that OpenQASM mandates 64-bit
unspecified integers. The worker, circuit storage, editor and importer use this
same policy through the interfaces described below.

The native `IntegerExpression` layer retains integer type identity across
constants, packed-register reads, casts and arithmetic expressions. It validates
register references without evaluating an artificial record, so a runtime
divisor is checked only when the expression executes. Expressions are immutable
and limited to 32 levels and 512 expanded nodes. The caller supplies an already
initialized record; declaration and initialization tracking are not supplied by
this layer alone. Worker protocols and circuit formats connect this API to the
editor and OpenQASM importer; the later variable-storage layer tracks declaration
and initialization state.

`Bits::integerCompare` converts one of the six typed integer comparisons into a
single-bit condition usable by native exact and trajectory circuits. Untaken
branches are structurally checked without executing their arithmetic; an
executed zero divisor raises an error. Combined bit/integer expression trees
share the same depth and expanded-node limits. The protocol and importer
encodings described below expose this bridge to imported and edited circuits.

### Typed integer condition wire protocol

`QEXACT3` and `QSAMPLE4` retain the field layout of `QEXACT2` and `QSAMPLE3`
and additionally accept bit-expression node 6: a comparison code followed by
two integer expression trees. Comparison codes 0..5 mean `==`, `!=`, `<`, `<=`,
`>` and `>=`. Node 7 encodes logical And (0) or Or (1), followed by two
one-bit expression children. QuantumStudio evaluates logical operands left to
right and skips the right operand when the left determines the result. Bitwise
And/Or (node 3) continue to evaluate both children. Older protocol versions reject
nodes 6 through 8. Structural checks still inspect skipped logical operands.

Node 8 contains one integer expression child and reinterprets its raw bits as a
bit vector of the same width. The child must have an explicit width; cast a
machine-sized arithmetic result to `int[n]` or `uint[n]` first. Assignment
destinations must match that width. This implements the equal-width integer to
bit-register conversion in the [OpenQASM casting rules](https://openqasm.com/language/types.html#casting-from-int-uint).

An integer type is encoded as signedness (0 signed, 1 unsigned) and width
(1..64 explicit, 0 machine precision). Integer tree nodes are:

- 0: type, then unsigned decimal raw bit pattern.
- 1: type, then one classical bit index per storage bit, least-significant first
  (64 indices for machine precision).
- 2: target type, then one integer child (explicit cast).
- 3: arithmetic code, then two integer children. Codes 0..5 mean addition,
  subtraction, multiplication, division, remainder and power.

Power applies the same common-type conversion as other integer arithmetic.
After conversion, a negative exponent is a domain error. Signed overflow is
checked and unsigned powers wrap; zero to the zeroth power is 1. This is the
worker's integer-domain policy. A skipped branch or short-circuited guard does
not evaluate the power, but still validates its structure and references.

All fields are LF-terminated unsigned decimal integers. Integer and bit nodes
share a 32-level/512-expanded-node budget, checked before descending. References
are checked even in untaken branches, but arithmetic executes only when reached.
A comparison produces one bit usable by the existing assignment and branch
operations. `QEXACT3` and `QSAMPLE4` do not declare integer variables or track
their initialization. Variable-bearing requests use the later protocol versions
described below. Circuit version 4 persists typed expressions, and versions 5
and 6 add variable storage and computed bit-to-integer conversions.

The Windows request adapter now has immutable `ClassicalIntegerType` and
`ClassicalIntegerExpression` objects and the `ClassicalExpression.IntegerCompare`
bridge. Requests containing these expressions select `QEXACT3` or `QSAMPLE4`,
including expressions in nested or untaken branches. Ordinary bit requests
retain their existing protocol versions. Construction and serialization check
combined expression bounds and register references. Circuit-file persistence,
text entry and OpenQASM import use the same typed expression representation.

### Typed conditions in circuit files

Classical circuit version 4 adds `IntegerCompare` bit nodes with integer children
`IntegerConstant`, `IntegerRead`, `IntegerCast` and `IntegerBinary`. Leaf/cast
nodes preserve `Signedness` (`Signed` or `Unsigned`) and `Width` (0 for machine
precision, 1..64 for explicit width). Integer values are raw unsigned decimal
bit-pattern strings. Binary nodes use the named arithmetic operator and inherit
the target promotion policy. The shared 32-level/512-node limit applies across
both node families.

Versions 2 and 3 reject typed expressions. Saving ordinary legacy circuits omits
the new unused type field so older readers can still load them. Snapshots and
undo/redo preserve version 4; ordinary bit-expression edits do not downgrade it.
Typed conditions can be reopened, displayed and edited as expression text in
the editor, and can be imported from OpenQASM.

### Integer conditions in the classical editor

Use `**` for integer powers: `2**3**2 == 512` groups from the right, while
`-2**2 == -4` applies negation after the power. Parentheses override that order.
Typed register operands work too, for example `int[8](c)**3 == 8`.
Power expressions retain this meaning when saved and reopened. Their evaluation
uses the integer promotion, domain and overflow policy documented above.

Enter typed comparisons and arithmetic directly, for example `int[8](c) < 0`
or `int[8](c) != 0 && 6 / int[8](c) == 3`, when `c` contains eight bits.
`int[n](c)` interprets the register as signed two's-complement; `uint[n](c)`
interprets it as unsigned. The width must match the register or slice. `int(x)`
and `uint(x)` use QuantumStudio's 64-bit machine type. Decimal literals inside
integer arithmetic use that machine type; explicit casts narrow to low bits.
Supported arithmetic is `+`, `-`, `*`, `/`, `%`, with parentheses and unary minus.
Compare the result to produce a one-bit condition or assignment value.

`&&` and `||` evaluate from left to right and skip the right operand when the
left determines the result. `&` and `|` retain eager bitwise behavior. Invalid
register references are rejected even in skipped operands. Integer and logical
conditions are saved as circuit version 4 and survive formatting, reopening,
and editing. Existing ordinary bit expressions retain their earlier format.
The editor's variable table declares typed integer storage. Version-6 documents
also accept matching-width casts of computed bit expressions, such as
`uint[3](c ^ "111")`; numeric Boolean conversions preserve zero or positive one.

To store a computed integer in a bit register, use an explicit equal-width cast,
for example `bit[3](int[3](int[3](c) + 1))`. The inner arithmetic uses integer
promotion rules; `int[3](...)` narrows the result before `bit[3](...)` preserves
its three raw bits. The assignment must target three bits. These expressions
are editable and saved in version-4 circuit files as `IntegerBits` nodes with
one typed `Left` child; their width comes from that child. A machine-width
integer needs an explicit-width cast before it can become a bit vector.
OpenQASM imports preserve the same equal-width `bit[n](integer)` casts, including
computed assignments and casts of measurement-dependent values. Cast widths
must be compile-time constants. Entirely static expressions still use the
pinned PyQASM constant evaluator.

OpenQASM import accepts `bit[1](c == "1")` and other Boolean-to-bit casts,
including negation, logical combinations and typed integer comparisons.
False and true become zero and one; a Boolean cannot be cast to a wider bit
vector. This follows the [OpenQASM 3.0 Boolean casting rule](https://openqasm.com/versions/3.0/language/types.html#casting-from-bool).

The classical editor and OpenQASM importer also accept `bool(...)` on bit and
integer expressions. Zero becomes false and any nonzero value, including a
negative integer, becomes true. For example, `bool(c)` tests a whole register,
and `bool(int[3](c))` tests its signed interpretation. The saved expression is
the equivalent comparison with zero, using the existing file and worker
formats. Logical guards such as `bool(c) && 6 / int[3](c) == 3` retain
short-circuit evaluation. Boolean variable declarations and runtime floating
point casts remain separate unsupported features.

OpenQASM import also preserves Boolean `&&` and `||` as version-4 logical
nodes, including assignments and nested branches. Bitwise `&` and `|` retain
bit-vector nodes. Imported runtime conditions also support width-matched signed/unsigned casts,
integer `+`, `-`, `*`, `/`, `%`, `**`, unary minus and comparisons. Powers preserve
OpenQASM's right associativity and precedence above unary minus. Casts and arithmetic
inside runtime conditions retain QuantumStudio's documented integer semantics,
including checked signed overflow and narrowing to low bits. Guards may skip
runtime arithmetic errors, while invalid references and cast widths are always
rejected. Machine-width casts use 64 bits. Fully static expressions still use
the pinned compiler's constant evaluator.

Classical OpenQASM import accepts top-level `output bit result;` and
`output bit[n] result;` declarations. When any explicit outputs exist, only
those registers appear in the result; ordinary bit registers remain available
as working storage. Within the selected registers, results retain the existing
reverse-declaration, most-significant-bit-first display order. Without explicit
outputs, all visible bit registers remain results. This follows the
[OpenQASM 3 input/output selection rule](https://openqasm.com/versions/3.0/language/directives.html#input-output).
Runtime `input` parameters and non-bit outputs still require separate support.
Numerical-composer import rejects explicit input/output declarations rather
than discarding their result semantics.

Top-level `int` and `uint` declarations now import as version-5 runtime variables,
with explicit widths from 1 to 64 or an omitted width for machine-sized integers.
For example, `int[8] counter=3; bit c; counter=counter**2-1; c=counter==8;`
sets `c` to one. Arithmetic compound assignments preserve the same runtime
read/compute/store behavior. Measurement results can enter integer expressions
through width-matched casts such as `int[1](c)`; `bool(counter)` and
`bit[8](counter)` explicitly convert variables back to Boolean or bit values.

An uninitialized variable stays undefined until assigned. Each sampled shot gets
fresh storage, and exact evaluation keeps distinct variable histories until they
can safely merge. The importer preserves these semantics instead of evaluating
mutable values while compiling. This follows the initialization and scope rules
in the [OpenQASM type specification](https://openqasm.com/language/types.html).
Integer declarations also work inside branches, brace-delimited blocks and
unrolled constant-bound loops. A local integer can shadow an outer variable:
`int a=1; bit c; {int a=2; c=a==2;} c=c && a==1;` leaves `c` equal to one.
The imported document gives locals unique names and clears their storage on
entry and exit, so a later loop iteration cannot read a previous local value.
Local constants can specify widths, but non-integer shadowing remains unsupported.

Variable references and integer declarations in subroutines, dynamic indices
and runtime gate parameters still require additional lowering and are rejected
explicitly. Scoped integers work with `break` and `continue`; each transfer clears
the local scopes it exits. Integer variables may be updated inside runtime ranges
or unrolled constant-bound loops. Variable names
are limited to 64 UTF-16 code units, programs to 4096 integer declarations, and
lexical scope nesting to 32 levels.

Computed bit expressions can be cast to matching-width integers during import,
for example `uint[3](c ^ "111")` or `int[3](~c)`. These expressions produce
version-6 circuit documents. Boolean predicates convert numerically, so
`int[8](c == 0)` produces zero or positive one, while reinterpreting a signed
bit vector preserves its two's-complement sign. `uint(popcount(c))` converts the
64-bit population count. Logical guards retain short-circuit evaluation, and
invalid widths or references are rejected even inside an unselected branch.
These rules follow the [OpenQASM casting specification](https://openqasm.com/language/types.html#casting-specifics).

Scalar bits and single indexed bits convert numerically as well:
`bit c=1; int[8] a=int[8](c);` gives `a=1`, and `int[8](c[0])`
converts one bit of a register. Whole `bit[1]` registers and one-element
slices remain bit vectors: `int[1]("1")` reinterprets the sign bit as -1,
and widening a register requires a separate integer cast. This preserves
the specification's distinction between scalar `bit` and register `bit[1]`.

Bit rotations accept runtime integer distances and arithmetic, for example
`int n=1; bit[3] c="001"; c=rotl(c,n+1);` produces `"100"`.
Distances retain their signedness, including negative distances and unsigned
64-bit values. The distance is evaluated when the rotation executes, so
measurement-dependent values and guarded undefined variables retain their
runtime behavior. This extends the [OpenQASM circular-shift operations](https://openqasm.com/language/classical.html#classical-bits-and-registers).

Mutable Boolean variables are preserved during classical import. For example,
`bool ready=false; ready=!ready; if(ready){x q;}` evaluates the condition at
runtime. A Boolean may copy a measured scalar bit, retain that value after the
bit changes, participate in integer arithmetic, and shadow an outer variable
inside a block. Uninitialized reads fail when executed; short-circuit guards
and fresh local storage retain the same behavior as integer variables.

The compiled circuit represents Boolean storage as `uint[1]` variables with
explicit truth-value conversions on writes and reads. Integer assignments use
the nonzero rule; bit registers, bit strings and slices require explicit
`bool(...)` conversion. This follows the [OpenQASM Boolean casting rules](https://openqasm.com/language/types.html#casting-from-bool).
Boolean compound assignments, subroutine-local storage and
floating-point conversions still require further lowering.

Measurement can directly initialize or update a Boolean:
`bool result=measure q;` and `result=measure q;`. The compiler reuses one
temporary classical bit and immediately copies each outcome into Boolean
storage. Later measurements cannot overwrite a saved Boolean value. Original
register indices and output order stay intact; the temporary bit is excluded
from output counts but is visible in the compiled circuit. This requires one
of the circuit's 64 classical bit slots, regardless of measurement count.

Runtime `switch` selection is preserved during classical import. For example,
`switch(int(result)){case 0 {x q;} case 1 {z q;}}` selects one case using the
saved measurement value. Integer variables, explicit integer casts, arithmetic,
and population counts can supply the target; case labels must be integer
constants. Multiple labels, negative values, nested switches, optional defaults,
and case-local integer or Boolean variables are supported. An unmatched switch
without a default does nothing, and changing the target inside a selected case
cannot cause fall-through into another case.

The compiler lowers selection to existing runtime branches, so the existing
32-level branch and expression-size limits apply. Boolean and bit targets need
explicit integer casts. Bounded runtime `while` loops and integer `for` ranges can contain switches.
Subroutine-local storage remains unsupported. These rules follow the
[OpenQASM switch specification](https://openqasm.com/language/classical.html#the-switch-statement).

Constant targets such as `switch(1+1)` and `switch(int(true))` use the same
case validation as runtime targets. Integer arithmetic can promote Boolean
operands, including comparisons: `switch((n==2)+1)` selects an integer case
while preserving short-circuit evaluation inside Boolean operands.
A bare Boolean target such as `switch(n==2)` still needs an integer cast.
This follows the standard-type arithmetic promotion rules in the
[OpenQASM casting specification](https://openqasm.com/language/types.html#casting-specifics).

The editor displays canonical nonzero tests as `bool(...)`, for example
`bool(ready)` or `bool(read(0,1,2))`. This is editable syntax: formatting and
reparsing preserve the stored expression. Comparisons with explicitly sized or
unsigned integer zeros retain their explicit types rather than being shortened.

The native numerical trajectory API now provides `TrajectoryStep::whileLoop`
for measurement-driven repetition. Its one-bit condition is evaluated before
every iteration against current classical bits and typed variables. All loop
bodies are validated even when the condition is false. Branches and loops share
the existing 32-level nesting and 4096-static-step limits. A separate limit of
1,000,000 condition evaluations per shot is shared across all loops; the explicit
budget overload can change it. Budget exhaustion and cancellation throw without
returning partial counts, including for empty loop bodies. This implements the
[OpenQASM while condition semantics](https://openqasm.com/language/classical.html#while-loops)
in the native numerical and exact APIs. Worker transport now exposes loops via
`QSAMPLE7` and `QEXACT6`; version 7 files preserve loops and their budgets.
Editor controls and OpenQASM while import are available; `break`/`continue` still need integration.

`CircuitStep::whileLoop` preserves exact probability weights as histories enter
and leave the loop at different iterations. Only histories with equal classical
bits and equal variable values/initialization states merge at a loop boundary.
The exact evaluator shares a condition budget across the entire evaluation,
including all nested loops and measurement histories (1,000,000 by default,
overridable). It throws on exhaustion without returning or renormalizing partial
probabilities. A repeat-until-success program with infinitely many possible
iteration counts can therefore exceed the exact budget even when individual
sampled runs terminate almost surely. Existing record-memory limits still apply;
empty loop bodies remain cancellable.

The Windows request adapter also accepts `NumericalSampling.Operation.While`,
using `ClassicalExpression` for its one-bit condition and `WhenTrue` for its
single body. `WhenFalse` must be absent. Explicit-output sampling and exact
request methods accept an optional condition budget (0..1,000,000), defaulting
to 1,000,000 when loops are present. They select `QSAMPLE7`/`QEXACT6` and retain
older request versions when neither loops nor an explicit budget are used.
Version 7 saved circuit files preserve this operation and its explicit loop
condition budget. Exact and sampling evaluation forward that saved budget;
the editor can modify loops and their limits, and OpenQASM while import uses this format.


### OpenQASM runtime while import

The classical importer preserves `while (condition) { ... }` as a runtime loop.
For example, `int n=3; bit c; while(n>0){n-=1;c=n==0;}` produces output 1.
Conditions are checked before every iteration, including the first. Measurement
results can control subsequent iterations. Nested loops, if/switch branches,
static for loops, and scoped integer/Boolean variables retain their execution
order. Local variables are cleared on each entry, so an uninitialized local
cannot inherit a value from an earlier iteration.

The imported version-7 file saves a 1,000,000 condition-check limit. Exact and
sampling use the same loop body; exceeding the limit reports an error with no
partial results. Exact evaluation can exhaust the limit for an infinite-support
measurement loop even if that loop terminates with probability one. `break` and
`continue` targeting a while loop are preserved in version 8 files, with explicit
cleanup for every exited local scope. An inner-loop transfer preserves outer-loop
locals. Static for-loop transfers preserve iteration bindings through guarded,
one-pass loops, consuming one condition check per executed iteration.
Whole-program `end;` is preserved in version 9 circuit files, including inside
branches and loops. Runtime integer ranges use version 10 files: their inclusive
start, stop and step are captured at entry, and an independent cursor assigns
each iteration's local binding. Writing the binding does not change the cursor.
Dynamic indices and runtime gate angles remain unsupported. Global declarations inside a loop are rejected, including
inside an unreachable body.


### Native trajectory loop transfers

The numerical trajectory API provides `TrajectoryStep::breakLoop()` and
`TrajectoryStep::continueLoop()`. Both propagate through if branches to the
nearest enclosing while loop. Break resumes after that loop; continue skips the
rest of its body and checks its condition again, consuming the usual condition
budget. Inner-loop transfers never skip the rest of an outer-loop body.
Validation rejects either transfer outside a loop, including in an unreachable
branch and when zero shots are requested. Operations after a transfer still
undergo validation even though execution skips them. Cancellation and errors
continue to throw without partial counts.

Worker transport, saved files, GUI controls and OpenQASM lowering for these
transfers remain unfinished. Exact native support is described below.
Callers that compile scoped variables must emit any required scope-exit clearing
before a transfer. The native API does not infer source-language scopes.

Semantics: [OpenQASM break and continue](https://openqasm.com/language/classical.html#breaking-and-continuing-loops).


### Multi-line mathematical derivations

Pasted `aligned`, `align`, `align*`, `gathered`, `gather`, `gather*`, and
`split` fragments retain independent expressions. An indented row beginning
with `=`, `<=`, `>=`, or `!=` continues the preceding expression in its column
pair; indented arithmetic continuations append to that expression. Multiple
column pairs are read in row order. `gather` variants do not accept `&` columns.
TeX position hints and supported row-spacing annotations affect layout only.

For example, `\begin{aligned}1+1&=2\\2+2&=5\end{aligned}` produces two
results: `1` and `0`. The Windows result panel numbers independent results,
including separate matrix results. Copy preserves the separate expressions
in a `gathered` fragment so they can be evaluated again. An alignment embedded
in another expression remains an ordinary mathematical vector operand.
There are limits of 128 rows, 128 independent expressions, and 32 column pairs.

Braces around a complete state label are accepted, including
`\vert{+i}\rangle`. The easier keyboard form remains `|+i>`.
The exact two-state derivation in IBM's
[density matrix lesson](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/density-matrix-basics)
is covered by a parser integration test; this does not establish coverage of
every derivation in that lesson.

### Exact-history loop transfers

`CircuitStep::breakLoop()` and `CircuitStep::continueLoop()` implement the same
nearest-loop semantics in exact evaluation. Pending transfers are part of the
history identity: histories with identical bits and variable values cannot
merge if one still executes the body and another has already broken or continued.
Only the enclosing loop consumes a transfer, preserving exact fractional and
symbolic probability weights. A pending transfer skips later operations and
nested loops without evaluating their conditions. Static validation still checks
all operations and rejects transfers outside loops.

The shared exact condition budget counts each active history. These factories
extend the native API only; transport, saved-file, editor and import support for
break/continue remain unfinished, along with compiler-managed scope cleanup.

### Contiguous indexed columns

In Quantum Notation, `[alpha_0; alpha_1; ⋮; alpha_(n-1)]` denotes a column with entries from `alpha_0` through `alpha_(n-1)`. The dimension stays symbolic until supplied; replacing `n` with 3 produces a three-row column. Greek coefficient names and the corresponding TeX `pmatrix`/`bmatrix` with `\vdots` are accepted. Group a compound endpoint with parentheses or braces: `alpha_n - 1` means subtraction and is not an indexed endpoint.

The leading entries must be consecutive from zero, the ellipsis must precede the endpoint, and every entry must use the same coefficient family. The retained minimum endpoint is the index of the last explicitly shown leading entry. Thus `[a_0; a_1; ⋮; a_(n-1)]` requires `n >= 2`; a degenerate endpoint equal to the last shown entry does not duplicate it. Expansion preserves column shape, including a permitted singleton, and is limited to 1024 rows. Invalid, fractional, negative, or too-small dimensions are rejected after substitution too. The internal representation is `qindexedcolumn("alpha_",n-1,1)`.

Symbolic results display the bracket-and-ellipsis form when its endpoint can be entered again as simple arithmetic. More complex endpoints or more than 17 explicit leading entries retain the canonical function display; clipboard output always retains the canonical expression.

This supports contiguous column families; arbitrary ellipsis patterns and two-index matrix ellipses remain unfinished.

### Contiguous two-index matrices

Quantum Notation accepts `[a_(0,0), ⋯, a_(0,n-1); ⋮, ⋱, ⋮; a_(m-1,0), ⋯, a_(m-1,n-1)]` and corresponding TeX matrices with grouped paired subscripts, `\cdots`, `\vdots`, and `\ddots`. Rows and columns each begin at index zero. Explicit leading indices must be consecutive, and the penultimate row and column must contain the indicated ellipses. All entries must use one coefficient family and consistent endpoint expressions. Validated optional TeX row spacing is ignored.

The internal form `qindexedmatrix("a_",m-1,n-1,0,0)` retains both endpoints and both minimum endpoints implied by the displayed leading entries. Unknown dimensions remain symbolic. Substitution validates every dimension, including an invalid known dimension alongside an unknown one. Each axis supports 1 through 1024 entries, matching the existing matrix allocation bound of 1,048,576 cells; expansion checks cancellation. A singleton remains a matrix. Generated coefficients have paired labels such as `"a_0,0"`, which can be replaced explicitly using `replace`. Trace and rectangular expansion are covered by worker tests.

Symbolic matrices use a multiline bracket display with horizontal, vertical and diagonal ellipses when both endpoints are simple re-enterable arithmetic and each axis has at most five explicitly shown leading entries. Larger patterns and complex endpoints retain canonical function display. Clipboard output remains canonical in every case.

General noncontiguous sequences, inferred formulas for arbitrary entries, and ellipses without this two-axis pattern remain unfinished.

### Paired coefficient subscripts

Use `a_(0,1)` or TeX `\alpha_{0,1}` for one scalar coefficient with two indices. The grouped comma stays inside the coefficient in finite matrices and function arguments. For example, `replace([a_(0,0),a_(0,1);a_(1,0),a_(1,1)],a_(0,1),7)` remains a 2×2 matrix and changes only the upper-right entry. `2a_(0,1)` is accepted as implicit multiplication.

Unknown indices stay symbolic: `a_(k,l+1)` resolves to the coefficient `"a_2,4"` after replacing `k` with 2 and `l` with 3. Numeric indices must be integers; fractional and vector indices are rejected. Symbolic results use paired-subscript display, while clipboard output retains the canonical representation. The internal function is `qindexedcoefficient("a_",row,column)`.

The reserved imaginary unit `i` still conflicts with its use as an unbound index name; use another index name pending that separate notation fix.

### Constant names as local arithmetic indices

An explicit arithmetic binder can use `i`, `e`, or `pi` as its local index: `sum(i,0,2,i)` gives 3. Typed occurrences in the body refer to that local index; occurrences outside it retain their normal constant meaning. Nested binders keep separate scopes, and bounds may refer to an enclosing index. This also applies to paired coefficients such as `sum(a_(i,0),0,n,i)`, which stays symbolic until `n` is supplied.

Constants introduced by gate expansion remain constants. For example, `sum(i*Y,0,2,i)` is `3*Y`, including the imaginary entries of the Pauli-Y matrix. Likewise, `sum(P(i),0,1,i)` evaluates the phase gates at angles 0 and 1 without changing the imaginary unit in their exponential formulas. The displayed sum may rename its local index to avoid collisions; clipboard output preserves the scoped representation.

Inside an explicit `i`-indexed sum, bare `|i>` and `<i|` refer to the local basis index: `sum(|i>,0,1,i)` gives `|0>+|1>`, and `sum(|i><i|,0,1,i)` gives the two-dimensional identity. Nested binders retain their own scopes. Outside such a binder, `|i>` remains the positive imaginary phase state; write `|+i>` explicitly to keep that phase-state meaning inside an indexed sum. Unbound scalar `i` still denotes the imaginary unit.

### One-dimensional explicit matrices

In quantum notation, `matrix(1,1,[5])` retains its 1×1 matrix shape, including when its dimensions are computed expressions. `Tr(matrix(1,1,[5]))` therefore gives 5, and `Tr(identity(1))` gives 1. Copying a matrix result and evaluating it again preserves its shape. A scalar such as `Tr(5)` remains invalid; the ordinary calculator mode retains its existing singleton behavior.

### Matrix parameter domains

`matrixparam(A,rows,columns)` declares a single unknown symbol as a matrix with the stated dimensions. The declaration remains in canonical copy output until both the matrix and its dimensions are supplied. Dimensions must be positive integers; each known axis is validated even while the other remains symbolic. Substituting a scalar or a matrix with a different shape is rejected. For example, `replace(matrixparam(A,2,2),A,X)` evaluates to the Pauli-X matrix. Symbolic dimensions can be supplied before or after the matrix value.

This expression-level domain is the foundation for dimension-aware symbolic identities. A GUI declaration editor remains unfinished; the supported trace rules are described below.

Declared dimensions also reject provably incompatible additions, subtractions, explicit `*` products, and traces before matrix values are supplied. Shapes propagate through compatible sums, products, scalar scaling, transpose, and adjoint. For example, `Tr(matrixparam(A,2,3))` rejects immediately; a `2×3` parameter multiplied by a `3×2` parameter remains symbolic. Different unknown dimensions are not presumed unequal, so unresolved shape constraints defer until more values are supplied. Trace rewriting additionally requires established matching square shapes, as described below.

### Trace linearity with declared matrices

Trace distributes over sums and differences when declared dimensions establish matching square matrices. It also extracts scalar factors from a declared square matrix, whether multiplication uses `*` or adjacency such as `α A`. Thus, for `U=matrixparam(A,n,n)` and `V=matrixparam(B,n,n)`, the expression `Tr(α*U+β*V)-α*Tr(U)-β*Tr(V)` simplifies to zero after substituting those declarations for U and V. Complex scalar parameters are supported. Unknown or unmatched dimensions retain the original trace expression until resolved; rectangular traces still reject, including when multiplied by zero. These simplifications are under the supplied matrix-domain assumptions.

### Applying matrix declarations to an expression

`matrixassume(expression,A,rows,columns)` annotates free occurrences of A with a matrix domain before evaluating the expression. Text-valued state labels such as `|A>` and local summation indices are preserved. Existing `matrixparam` annotations take precedence, allowing canonical results to be evaluated again without nested annotations. Nested declarations own their bodies; dimensions are still checked, including for an unused declaration. Gates, constants, and already-valued symbols cannot be redefined as matrix names.

For example, `matrixassume(matrixassume(Tr(A+B)-Tr(A)-Tr(B),A,n,n),B,n,n)` gives zero. The Windows Matrices editor applies these declarations without adding function syntax to the input. Declare A and B with rows and columns n, then enter `Tr(A+B)-Tr(A)-Tr(B)` directly. Declarations apply only in Quantum notation. Each history entry keeps its own dimensions; session version 3 saves the workspace and history declarations. Older sessions load with no matrix declarations. The editor checks names and dimension syntax; Calculate checks positive integer dimensions and reserved symbols. Use an underscore for indexed names, such as `M_1`: a declaration such as `M1` is rejected when parsing would simplify it to the different symbol `M`.


### Symbolic Gram-matrix positivity

With M declared as a complex matrix, `M†*M >= 0` and `M*M† >= 0` simplify to true (1), including rectangular M. The reversed comparisons `0 <= M†*M` and `0 <= M*M†` do the same; strict negative-definiteness comparisons return false (0). For example, `matrixassume(M†*M>=0,M,2,3)` returns 1. The Matrices editor supplies this declaration without changing the typed formula.

Strict positivity and equality to zero remain unresolved without rank or value information. Transpose products and products with a different factor do not receive this proof. This follows the positive-semidefinite definition in [IBM Quantum Learning: Density matrix basics](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/density-matrix-basics); it is not a general symbolic inequality solver.


Symbolic dimensioned basis states display as `|x⟩_{N}`, retaining their dimension through adjoints. Exponentials inside Fourier sums display as `exp(...)`; the sum index uses the same displayed name in the exponential and ket. Copy result continues to use the canonical expression, preserving evaluation and binder scope. The Fourier basis-action rule below expands `QFT_N|x⟩_{N}` while retaining its domain.


## Domain-preserving Fourier basis actions

`QFT_N|x>_N`, `QFT_N†|x>_N`, and `QFT_N^(-1)|x>_N` expand into an actual finite sum when the index or dimension is symbolic and the operator and basis dimensions match. The forward sum uses `exp(2*pi*i*x*k/N)/sqrt(N)` and the inverse uses the negative phase, following [IBM's Fourier definition](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure). A fresh sum index avoids capture by surrounding sums or free symbols.

The result displays its integer-index conditions. Copy result retains both the sum and its domain in the canonical `qfourierdomain` expression. Substituting numerical parameters validates the index and dimension before evaluating the sum: dimensions must be integers from 1 through 64, and the index must be an integer from 0 through N−1. For example, supplying N=4 and x=1 gives `[1;i;-1;-i]/2`; x=4 is rejected rather than being accepted through periodicity of the exponential. Dimension one remains a 1-by-1 column matrix. Unknown parameters stay symbolic in both arithmetic modes.

Copy/re-entry may normalize equivalent scalar formatting, such as `1/sqrt(N)` to `1/N^0.5`; it preserves evaluation and domain checks. Use Copy result for re-entry of the full conditional expression. A bare named ket such as `QFT_N|x>` does not declare x to be an integer basis index and is not expanded by this rule. General Fourier identities and unspecified basis declarations remain separate work.

## Finite named orthonormal bases

Use `orthobasis(expression,B,[|red>,|blue>])` to declare the listed named kets as an ordered orthonormal basis named B within that expression. For example, `orthobasis(<red|red>,B,[|red>,|blue>])` gives 1 and `orthobasis(<red|blue>,B,[|red>,|blue>])` gives 0. This implements the explicitly assumed orthogonality discussed in [IBM's inner products lesson](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/inner-products-and-projections).

The declaration carries its basis name and complete ordered label list in each unresolved ket. It does not choose computational coordinates. An overlap between B and a different basis C stays symbolic, even when the displayed state labels match. Conflicting ordered label lists for the same named basis are rejected when contracted. Duplicate labels, empty lists and non-ket list entries are rejected. Existing coordinate-defined states and state families cannot be overridden by an orthonormal declaration. A declaration has expression scope; an inner declaration owns its own expression.

Copy result preserves the declaration through a canonical `qorthoket` expression. Undeclared named kets retain their existing unresolved behavior. Symbolic indexed basis families and dedicated basis editing remain unfinished.

A sum containing each declared basis projector exactly once reduces to the identity in that dimension. For example, `orthobasis(|red><red|+|blue><blue|,B,[|red>,|blue>])` gives `[1,0;0,1]`. The same rule accepts `density(|red>)+density(|blue>)` inside the declaration. A single declared vector in dimension one gives a 1-by-1 identity matrix. This is the completeness condition used in [IBM's projective measurements discussion](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/inner-products-and-projections).

Partial sums, repeated projectors, off-diagonal dyads and mixed-basis sums are not treated as complete bases by this rule; other valid simplifications may still apply. Weighted terms do not receive the completeness proof. Conflicting declarations of the same basis are rejected. The rule uses explicit finite declarations; it does not infer that an undeclared set of vectors is complete.
