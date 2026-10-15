# QuantumStudio research and coverage notes

The project goal is broad quantum-computing and quantum-programming notation support, including IBM Quantum Learning and qBraid learning materials. **That goal is not complete.** A working example or a green test suite does not establish whole-course or whole-language compatibility.

This note accompanies the executable. Its build revision is recorded in `build-manifest.json`. The offline `Notation-guide.html` describes implemented operations and their input limits. The source archive contains the corresponding implementation and tests.

## Sources and audit method

The [IBM course catalog](https://quantum.cloud.ibm.com/learning/en/courses), checked on 2026-10-15, lists 15 courses. Discovering those courses is only an inventory step. Each lesson still needs its mathematical expressions, assumptions, register conventions, and executable code classified separately. The public qBraid notebook audit uses [qbraid-lab-demo revision 86787e1](https://github.com/qBraid/qbraid-lab-demo/tree/86787e1ba372facc224f925189755e69c479828b); it does not imply that the app executes the notebooks or their SDK calls.

For a formula, record the source, choose explicit finite dimensions and parameter values, and compare its result against an independently derived vector or matrix. Preserve the source syntax where possible. Record adaptations such as replacing an unspecified register dimension, rather than calling an adapted expression an exact paste. Keep malformed-input and convention checks alongside successful examples.

## Selected verified notation

The [IBM phase-estimation procedure](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure) motivates these regression cases:

- Subscripted summation indices such as `a_0`, including nested binders and reused index names. See `src/quantum-parser-integration-test.cc`.
- Unbraced finite sums and products use multiplicative-term scope. For example, `\sum_{k=0}^{2} k+1` gives 4, while grouping `(k+1)` gives 6. Nested phase-estimation sums are covered by the integration tests.
- Space-separated computational bits such as `|a_1 a_0>`: with phase parameter 1/4, the tested intermediate state after the first controlled operation is `[1;i;1;i]/2`. Each bit must evaluate to 0 or 1.
- TeX matrix row spacing such as `\\[1mm]`: the spacing is ignored, and the lesson's four-dimensional Fourier matrix is checked against `qfourier(4)`.
- The probability `|⟨101|(H⊗H⊗H)|000⟩|^2` equals 1/8. The packaged keyboard check verifies that Enter displays 0.125 once without inserting a newline.

These are selected finite examples, not certification of the entire phase-estimation lesson. In particular, source formulas can rely on implicit dimensions, named states, or mathematical definitions supplied earlier in the text.

## Numerical conventions

Exact scalar arithmetic and exact matrix identities are retained where implemented. Some matrix algorithms use double precision even when the calculator precision is higher.

The numerical fractional-power and matrix-logarithm path supports Hermitian or unitary matrices up to dimension 64. It uses the principal phase in (-pi,pi], with +pi at the negative real axis. In `libqalculate/QuantumMatrixPower.cc`, normalized Hermiticity is checked at 1e-12, unitarity at 1e-11, and eigenvector residuals at 1e-10. Near-zero scaled Hermitian eigenvalues below 1e-13 are rejected for logarithms and negative powers. Positive powers also reject unresolved small eigenvalues. These are numerical acceptance thresholds, not error guarantees for arbitrary inputs; general nonnormal matrices are unsupported.

Entropy uses numerical state validation with tolerance 1e-12 and reports about 12 significant digits. Its default base is two. The authoritative implementation is `libqalculate/QuantumStateMetrics.cc`; increasing calculator precision does not make that numerical eigensolver arbitrary precision.

## Remaining coverage

- Finish the lesson-by-lesson IBM audit and the qBraid generated-program and learning-content audits. Account-only qBook contents have not been inspected.
- Resolve implicit register dimensions, general symbolic bit strings and sets, ensembles, general instruments, and automatic POVM/Naimark constructions.
- Extend programming support beyond the current bounded static OpenQASM importer. The app does not execute arbitrary Python, Qiskit or qBraid SDK programs, QIR, runtime classical feedback, cloud jobs, or pulse/timing programs.
- Address scale separately from syntax. The current circuit editor is limited to eight qubits and 64 steps; dense mathematical operations have their own limits. Accepting a notation does not make utility-scale simulation feasible.

The released executable can lag newly merged source changes until the next reviewed packaging run. Use the manifest revision to identify the actual build, rather than assuming that the latest repository feature is already installed.
