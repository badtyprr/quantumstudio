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

Use a flat comma-separated list of at most 512 transformations. The initial value and every result must be a vector of at most 1024 scalar entries or a matrix with at most 1024 rows, 1024 columns and 262144 scalar entries. These are shape limits, not a guarantee of a normalized or physical quantum state; individual operations perform their own validation. Direct native callers use `qsequence(vector(step1,step2),initial,placeholder)`; explicit `vector(step)` preserves a one-step list.

The quantum parser permits up to 4096 atoms after encountering a sequence call. Its nesting limit remains 256 and its input limit remains 32768 bytes; translated-size and TeX limits also remain in force. These bounds can reject a complex expression with fewer than 512 steps. Cancellation is checked between transformations, in addition to checks within the evaluated operations. The GUI circuit editor and OpenQASM importer accept up to 512 steps. Circuits longer than 64 steps use the flat sequence form. Parameter complexity and the expression byte limit can still prevent evaluation of a circuit within the step limit.

A development audit generated four-qubit QFT and inverse-QFT OpenQASM with `qbraid-algorithms` 0.1.3, then unrolled it with pyqasm. The resulting programs have 108 and 112 steps respectively. Their unitary portions were adapted to sequence expressions and checked on all 16 computational basis inputs each against an independent NumPy gate-by-gate calculation: 32 checks, maximum vector-norm residual 2.20e-15. The complete inverse-QFT sequence, including four nonselective measurements, was checked on the same 16 inputs against the uniform diagonal density matrix: maximum residual 1.46e-16. This audit does not establish arbitrary notebook execution, ideal inverse-QFT wire-order equivalence, or arbitrary qBraid program compatibility.

## Numerical conventions

Exact scalar arithmetic and exact matrix identities are retained where implemented. Some matrix algorithms use double precision even when the calculator precision is higher.

The numerical fractional-power and matrix-logarithm path supports Hermitian or unitary matrices up to dimension 64. It uses the principal phase in (-pi,pi], with +pi at the negative real axis. In `libqalculate/QuantumMatrixPower.cc`, normalized Hermiticity is checked at 1e-12, unitarity at 1e-11, and eigenvector residuals at 1e-10. Near-zero scaled Hermitian eigenvalues below 1e-13 are rejected for logarithms and negative powers. Positive powers also reject unresolved small eigenvalues. These are numerical acceptance thresholds, not error guarantees for arbitrary inputs; general nonnormal matrices are unsupported.

Entropy uses numerical state validation with tolerance 1e-12 and reports about 12 significant digits. Its default base is two. The authoritative implementation is `libqalculate/QuantumStateMetrics.cc`; increasing calculator precision does not make that numerical eigensolver arbitrary precision.

## Remaining coverage

- Finish the lesson-by-lesson IBM audit and the qBraid generated-program and learning-content audits. Account-only qBook contents have not been inspected.
- Resolve implicit register dimensions, general symbolic bit strings and sets, ensembles, general instruments, and automatic POVM/Naimark constructions.
- Extend programming support beyond the current bounded static OpenQASM importer. The app does not execute arbitrary Python, Qiskit or qBraid SDK programs, QIR, runtime classical feedback, cloud jobs, or pulse/timing programs.
- Address scale separately from syntax. The current circuit editor is limited to eight qubits and 512 steps; dense mathematical operations have their own limits. Accepting a notation does not make utility-scale simulation feasible.

The released executable can lag newly merged source changes until the next reviewed packaging run. Use the manifest revision to identify the actual build, rather than assuming that the latest repository feature is already installed.
