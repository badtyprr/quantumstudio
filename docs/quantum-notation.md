# Quantum notation: research, implementation, and boundaries

This extension adds an explicit `quantum:` prefix to libqalculate's parser. The
Windows Quantum Studio application adds that prefix in Quantum notation mode.
Standard calculator mode retains libqalculate's existing syntax and units.

## Research basis

Reviewed on 2026-10-13. The sources below are primary documentation. There is no
closed, universal grammar for **all** quantum mathematics: quantum circuits,
continuous-variable systems, many-body physics, and programming languages have
different conventions. This implementation is a finite-dimensional matrix
calculator, not a quantum programming-language compiler or a theorem prover.

* [IBM: quantum circuits](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/introduction)
  motivates state vectors, inner products, projections, and gate composition.
  Kets are column matrices; bras conjugate and transpose their ket. Thus a bra
  times a ket yields a scalar, while the reverse order yields an operator.
* [IBM: reduced states](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/multiple-systems)
  supplies the density-matrix and partial-trace reference model. The Bell state
  `( |00> + |11> ) / sqrt(2)` has a rank-one density matrix, but either single
  subsystem is maximally mixed. This is a central regression test.
* [IBM: Kraus channels](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Kraus)
  defines channel application by summing `K rho K†`. Our `channel` calculates
  that algebraic sum. It does not certify positivity, trace preservation, or
  validity of an arbitrary supplied state or channel.
* [IBM: bit ordering](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering)
  distinguishes displayed bitstrings from SDK qubit indices. Here the first
  tensor factor is the leftmost subsystem and has index 0. In `|01>` the
  amplitude at zero-based matrix index 1 is one. Qiskit's qubit 0 convention
  differs: users translating indexed operations must reverse subsystem indices.
* [IBM: RZ](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RZGate)
  and [rotation formulas](https://learning.quantum.ibm.com/course/utility-scale-quantum-computing/lesson-02-bits-gates-and-circuits)
  ground rotations in `Rj(theta) = exp(-i theta sigma_j / 2)`. Rotation angles
  are radians. Global phases are retained; `Rx(pi)` equals `-i X`, not `X`.
* [Microsoft: Q# functors](https://learn.microsoft.com/en-us/azure/quantum/user-guide/language/expressions/functorapplication)
  motivates adjoint and controlled operations. Our matrix `controlled(U)` is
  `diag(I,U)` with the leftmost control on 1. Q# source programs, callable
  specializations, and language type judgments are not parsed.
* [PennyLane: fermionic operators](https://pennylane.ai/demos/tutorial_fermionic_operators)
  and [bosonic operators](https://docs.pennylane.ai/en/stable/code/qml_bose.html)
  demonstrate why ladder-operator algebras need separate semantics. Unspecified
  symbols are not silently assumed to obey canonical (anti)commutation rules.
* [CTAN: braket](https://ctan.org/pkg/braket) provides the fixed-size and
  expanding bra/ket macro conventions. Both `\ket`/`\Ket` and
  `\bra`/`\Bra` are accepted; braket input accepts bar-separated arguments
  or two braced labels. This is a mathematical input reader, not TeX execution.
* [AMS: amsmath guide](https://mirrors.ctan.org/macros/latex/required/amsmath/amsldoc.pdf)
  supplies the notation for fractions, roots, matrix environments, and indexed
  sums/products. The parser reads nested groups structurally so their extent is
  preserved; it rejects unsupported control sequences instead of partially
  replacing their names. Matrix row-spacing options are currently rejected.

## Supported notation

| Concept | Input in quantum mode | Meaning |
|---|---|---|
| Computational ket | `|0>`, `|01⟩` | Binary labels, preserving leading zeroes |
| Pauli eigenstates | `|+>`, `|->`, `|i>`, `|-i>` | X and Y eigenstates |
| Bra | `<0|`, `⟨i|` | Conjugate transpose |
| Inner product | `⟨+|0⟩` | Scalar amplitude |
| Outer product | `|0⟩⟨1|` | Rank-one operator |
| Matrix element | `⟨0|H|1⟩` | Bra/operator/ket multiplication |
| Superposition | `(|00⟩+|11⟩)/sqrt(2)` | Ordinary vector addition |
| Tensor product | `H ⊗ I`, `tensor(H,I)`, `H @ I` | Ordered Kronecker product |
| Direct sum | `X ⊕ Z`, `directsum(X,Z)` | Block diagonal matrix |
| Dagger | `S†`, `(H S)†`, `dagger(S)` | Hermitian conjugate |
| Gates | `I X Y Z H S T CNOT CX CZ SWAP` | Standard matrices; S = diag(1,i) |
| Pauli aliases | `σ_x σ_y σ_z` | X, Y, Z |
| Rotations | `Rx(pi) Ry(pi/2) Rz(pi/4) P(pi/4)` | Radians; P = diag(1,exp(i theta)) |
| Controlled matrix | `controlled(X)` | Control precedes target |
| Commutators | `comm(X,Y)`, `anticomm(X,Y)` | AB−BA and AB+BA |
| Norm | `norm(|0⟩+|1⟩)` | Euclidean ket norm |
| Normalization | `normalize(|0⟩+|1⟩)` | Zero ket rejected |
| Density | `density(|+⟩)` | Unnormalized outer product; no implicit normalization |
| Trace | `tr(density(|+⟩))` | Square matrix trace |
| Partial trace | `ptrace(density(|01⟩),0)`, `ptrace(ρ,[0,2])` | Trace out distinct indexed qubits, leftmost = 0; index order does not matter |
| Subscripted trace | `Tr_{0,2}(ρ)`, `\operatorname{Tr}_{0,2}(ρ)` | The same partial trace; numeric indices, not implicit subsystem names |
| Expectation | `expect(Z,|0⟩)` | Unnormalized bra/operator/ket form |
| Kraus channel | `channel(density(|0⟩),vector(X))` | Sum of Ki rho Ki†; brackets concatenate matrices, so use vector() |
| Repeated tensor | `H^⊗3`, `tensorpow(H,3)` | Tensor power, exponent 0–10 |
| Algorithm gates | `CCX`, `Toffoli`, `CSWAP` | Multi-qubit controlled gates |
| Indexed application | `apply(CNOT,|100⟩,[0,2])` | Gate wires map to the supplied subsystem indices in order |
| Fourier transform | `QFT(2)` | Positive-exponent Fourier matrix on 2 qubits; dagger gives inverse |
| Measurement distribution | `probs(ψ)` | Normalized squared amplitudes, ascending binary basis order |
| Explicit matrix | `[1,0;0,1]` | Commas separate columns, semicolons rows |
| Basis column | `basis(k,d)` | Zero-based component k in dimension d (2–1024), including qudits |
| TeX fragments | `\frac{1}{\sqrt{2}}`, `\ket{0}`, `\braket{i|Y|i}` | Nested groups, bra/ket macros, roots, fractions and Greek symbols |
| TeX matrices | `\begin{bmatrix}0&1\\1&0\end{bmatrix}` | matrix, pmatrix, bmatrix, Bmatrix; vmatrix means determinant |
| Norm delimiters | `‖ψ‖`, `\lVert ψ\rVert` | Euclidean column-ket norm |
| Finite sums/products | `\sum_{k=0}^{3}{basis(k,4)}`, `\prod_{k=1}^{4}{k}` | Integer bounds and a braced body; uses native sum/product functions |
| TeX aliases | `\langle`, `\rangle`, `\vert`, `\otimes`, `\oplus`, `\dagger` | Also `^{\dagger}`, `^{\otimes 2}`, optional sizing commands, and paired math wrappers |

Named ket labels refer to existing column-matrix variables; they are not new
abstract Hilbert-space basis declarations. The GUI starts a fresh backend for
each expression, so definitions do not persist between calculations.

Operator order: parentheses and calls, postfix dagger, right-associative powers,
unary signs, products/division/tensor/direct sum (left-associative), addition and
subtraction. Use parentheses around tensor products before applying gates.
`H ⊗ I |00>` means `(H ⊗ I) |00>`. Ordinary juxtaposition multiplies
matrices. A consecutive run of Dirac kets or bras instead forms their tensor
product before surrounding multiplication, so `CNOT|0>|1>` acts on |01>.
Use explicit tensor products for grouped or transformed expressions.

The existing `adj()` retains its ordinary adjugate meaning. `dagger()` and `†`
are the quantum conjugate transpose. `⊕` means direct sum outside basis labels. Inside literal binary basis labels it means bitwise XOR, for example `|001 ⊕ 101⟩ = |100⟩`.
Quantum mode preserves unknown symbols and disables unit interpretation so
summation indices and gate parameters have mathematical rather than unit
semantics. Standard calculator mode is unaffected. Finite products multiply
terms in increasing-index order from left to right; the rightmost matrix acts
first on a following ket. Use `basis(k,d)` for indexed basis families: a free
named ket label alone does not declare a dimension or an orthonormal basis.

## Boundaries and remaining work

Not supported as new surface syntax: arbitrary LaTeX documents/macros,
unbraced summation bodies, infinite or symbolic-bound sums, named-subsystem
partial traces, imported circuit diagrams, ZX diagrams,
Einstein summation, OpenQASM/Q#/Qiskit programs, arbitrary abstract noncommuting
operator algebra, distributions, infinite Hilbert spaces, fermionic/bosonic
ladder algebras, symbolic channel equivalence, or automatic physical validation.
Existing libqalculate functions remain available where their syntax fits; use
standard mode for its full ordinary grammar, calculus, unit conversions, and
other legacy notation. Matrix exponentials must not be confused with entrywise
scalar `exp`.

Computational basis labels are capped at 10 qubits; tensor/direct-sum outputs
at 262144 elements; density construction at 512 amplitudes. Parsing caps nesting
and complexity. The GUI defaults to 15 seconds per calculation, with selectable 1-minute, 3-minute, and 10-minute allowances and a Cancel button. Interrupted calculations do not enter history; the allowance is a view setting and is not saved in sessions. Dense matrix
storage makes this a small-system exploration tool, not a scalable simulator.

These boundaries mean the literal request for **all mathematical notation** is
not complete. This file is an explicit coverage contract for the implemented
subset, not a claim of universality.

## Hamiltonian evolution and measurement

`A >= B` (and `A ≥ B`, `A ≽ B`, `A ⪰ B`, or TeX `A \succeq B`)
uses Hermitian matrix order in quantum mode: A − B must be positive
semidefinite. Reversed forms `<=`, `≤`, `≼`, `⪯`, `\preceq` work too.
Strict `>`, `<`, `≻`, `≺`, `\succ`, `\prec` require positive definiteness.
The curly TeX aliases `\succcurlyeq` and `\preccurlyeq` are supported.
This follows the positive-semidefinite meaning of matrix inequalities in
[IBM's density-matrix definition](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/density-matrix-basics).

Examples: `[1,-1;-1,1] >= 0` is true, `[1,2;2,1] >= 0` is false,
and `0 <= density(|i>) <= I` is true. Scalars are promoted to a matching
scalar identity; matrix dimensions must agree and be at most 64. Ordinary
scalar comparisons and equality keep their previous semantics.

The implementation evaluates exact Schur complements. A zero pivot requires
a zero remaining row for semidefiniteness; any zero pivot rules out strict
positive definiteness. Unknown signs and unprovable Hermiticity are rejected.
No small-eigenvalue tolerance is used: exact rational perturbations such as
`[1,1;1,1-1e-80]` remain detectably indefinite. Approximate input expressions
retain their own accuracy limitations. This is an inequality check, not an
SDP solver or a general symbolic theorem prover. `windows/test-matrix-order.py`
uses integer congruences with known inertia, singular matrices, complex
entries, tiny pivots and notation aliases as independent regression evidence.

`expm(A)` and quantum-mode `exp(A)` evaluate the matrix exponential for square
matrices; `e^(A)` is an alias. Scalars retain ordinary exponential semantics.
`evolution(H,t)` evaluates `exp(-i t H)` with hbar = 1 and checks Hermiticity.
For example, `evolution(X,pi/2)|0>` is `-i|1>`. The factor of two relative to
`Rx(t)` follows the [IBM Pauli evolution convention](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.PauliEvolutionGate).

Diagonal matrices and centered quadratic matrices (including every 2 by 2
matrix and Pauli combinations) use exact algebraic formulas where possible.
General finite numeric matrices up to 64 by 64 use arbitrary-precision scaling,
a Taylor series, and squaring. Results from this fallback are explicitly marked
approximate. This is not SciPy's Pade implementation; see
[SciPy's algorithm reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html)
for that alternative. The numerical implementation limits precision to 1000
digits, 64 scaling steps, and 4096 series terms. It rejects unsupported symbolic
matrices and broad interval inputs. It does not provide certified error bounds
for arbitrarily ill-conditioned matrices.

`probs(ρ)` returns the computational-basis diagonal divided by trace, while
`expect(A,ρ)` returns the unnormalized `tr(Aρ)`. `born(E,state)` divides the
expectation by the ket norm squared or density trace. `postselect(P,state)`
returns the normalized projected ket or density matrix, checks that P is a
Hermitian idempotent, and rejects a zero-probability outcome. These operations
follow the [IBM measurement framework](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/introduction).
They assume physically valid states/effects: they do not certify positivity,
POVM completeness, or probability bounds for arbitrary inputs.

The two-argument `channel(ρ,vector(K0,K1,...))` now permits rectangular
Kraus matrices, computing Σ KρK†. Every operator has n columns and a common
m rows; input ρ is n × n and the output is m × m. Both dimensions are
limited to 512, with 1–256 operators. A one-dimensional output simplifies
to a scalar; `channel(density(|i>),vector(<0|,<1|))` returns 1.
Scalar inputs represent one-dimensional systems: `channel(1,vector(|i>))`
prepares `density(|i>)`. Scalar Kraus entries are accepted for scalar inputs.
The wire-indexed form still requires square local operators. No automatic
normalization or trace-preservation certification is performed.

This supports dimension-changing finite measurement channels described in
[IBM's formulations of measurements](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements).
Effects P determine probabilities with `born(P,state)`; feeding effects directly
as Kraus operators generally describes a different operation. A single Kraus
branch retains its unnormalized probability weight. General nondestructive
measurements need additional operator information, as explained in
[IBM's Naimark section](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/naimark-theorem).
Automatic dilation construction and general quantum instruments remain open.
`windows/test-rectangular-channels.py` independently checks random complex
maps, preparations, discards, a trine measurement, Choi matrices and
superoperator agreement (189 checks, six invalid inputs). The conversion
tests also cover an existing column-Kraus conjugation defect, now fixed:
`superop(vector([1;2]))` must be `[1;2;2;4]`, and its Choi matrix must be
`[1,2;2,4]`.

`A^T`, `A^{\top}`, and `transpose(A)` transpose without conjugating;
`A^*` and `conjugate(A)` conjugate without transposing. `ptranspose(ρ,[0,2])`
and `ρ^{T_{0,2}}` partially transpose the indicated qubits. Indices follow the
same leftmost-zero convention as partial trace. Dagger remains conjugate transpose.

## Multiple and open circuit controls

`controlled(U,n,s)` (alias `C(U,n,s)`) uses n leading control qubits and activates
U only on the control basis state with decimal index s. Omitting n means one
control; omitting s means all controls are 1. For example,
`controlled(X,2,1)|010>` returns `|011>`, whereas `controlled(X,2)` is Toffoli.
This implements the projector expression `(I-|s><s|) tensor I + |s><s| tensor U`.
See [IBM ControlledGate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.3/qiskit.circuit.ControlledGate)
for the control-state parameterization. Here the leftmost control is the most
significant bit, consistently with the rest of this calculator. Decimal indices
are accepted; quoted bitstring parameters are not yet parsed. Control counts
are 1–8, target dimensions must be powers of two, and the resulting matrix is
limited to 512 by 512. This constructs the algebraic operator without certifying
unitarity. Use `apply` for nonadjacent or reordered circuit wires.

The named gates now include CY, CH, and CCZ. `Rxx(t)`, `Ryy(t)`, `Rzz(t)`, and
`Rzx(t)` compute `exp(-i t (A tensor B)/2)` with letters in left-to-right tensor
order. The [IBM RXX reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RXXGate)
provides the half-angle convention and maximally entangling pi/2 example.
For asymmetric ZX rotations, explicitly map tensor factors when translating
from an SDK with a different wire-order convention.

## Indexed mixed-state circuits

`apply(U,state,indices)` accepts either a column ket or a square density matrix.
For a ket it applies U; for a density matrix it applies U rho U-dagger on the
selected subsystem wires. This agrees with the operator/subsystem model in
[IBM DensityMatrix.evolve](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.DensityMatrix),
with this app's leftmost-zero indexing convention. The ordered indices map the
operator's tensor factors to system wires, including reversed and nonadjacent
wires. For example, `apply(S,density(|+>),0)` produces `density(|i>)`.

The density implementation uses two local multiplication passes, avoiding a
full-system gate allocation. Inputs are limited to 1024 rows and 262144 matrix
elements (so a square density matrix has at most 512 rows). Like `channel`, this
is an algebraic operation: nonunitary operators are allowed, no normalization
is implicit, and positivity/unitarity are not certified. A projector therefore
returns an unnormalized branch; use `postselect` when normalization is wanted.

## Noise on selected circuit wires

`channel(ρ,vector(K0,K1,...),indices)` applies a Kraus sum to the selected
qubits, embedding each operator with the same ordered wire mapping as `apply`.
The two-argument form continues to operate on the whole state. The mathematical
map is the sum of Ki rho Ki-dagger, following the
[IBM Kraus representation](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Kraus).
For complete amplitude damping on the second qubit of a Bell state, use:

```
channel(density((|00>+|11>)/sqrt(2)),vector([1,0;0,0],[0,1;0,0]),1)
```

This yields the equal mixture of |00> and |10>. For partial damping with
probability 1/4, the local operators are `[1,0;0,sqrt(3)/2]` and `[0,1/2;0,0]`.
For complete dephasing use `vector(I/sqrt(2),Z/sqrt(2))`.
The indexed form allows 1–256 square qubit Kraus matrices and a density matrix
of at most 512 rows. Operator dimensions and wire indices are validated.
Completeness (sum Ki-dagger Ki = I) is not assumed or certified, and trace is
not renormalized: individual measurement branches remain expressible.

## Textbook circuit aliases

Rotation subscripts are accepted directly: `R_x(t)`, `R_{Y}(t)`,
`R_{XX}(t)`, `R_{YY}(t)`, `R_{ZZ}(t)`, and `R_{ZX}(t)` use the same semantics
as Rx, Ry, Rxx, Ryy, Rzz, and Rzx. Axis names are case insensitive after the
R_ prefix. These accept TeX angle expressions such as `R_{XX}(\pi/2)`.
The RXX spelling follows the mathematical notation in the IBM reference cited
above. ZX retains this calculator's explicit left-to-right tensor convention.

`C^2(X)` and `C^{2}(X)` are shorthand for `controlled(X,2)`. More generally,
`C^n(U)` with a literal integer n, or a grouped evaluated integer count, adds
that many all-ones controls. It does not mean the nth matrix power of a
single-control gate. Use `(C(U))^n` for the latter. The operand must be enclosed
in parentheses. Existing control-count and allocation limits apply.

## Measuring an output register

`probs(state,indices)` marginalizes the computational-basis distribution onto
selected qubits. A scalar selects one wire; a vector selects several in the
specified order, with its first wire becoming the most significant output bit.
For example, `probs(|100>,[2,0])` is `[0;1;0;0]`, meaning outcome 01 has
probability one. Both pure kets and density matrices are supported. Norm or
trace normalization follows the one-argument `probs` form. Duplicate indices,
noninteger/out-of-range indices, zero states, and non-qubit dimensions are
rejected. The indexed form supports 2–1024 state rows.

The operation is a marginal probability calculation; it neither samples nor
collapses the input state. The subsystem-probability and reordering model is
also documented by [IBM Statevector.probabilities](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Statevector).
Our leftmost-zero indexing and first-selected-most-significant convention must
be taken into account when translating SDK examples.

## Explicit qudit subsystem dimensions

`ptrace(ρ,indices,dimensions)` and `ptranspose(ρ,indices,dimensions)` accept a
left-to-right tensor factorization such as `[2,3]` for a qubit and a qutrit.
The dimensions must multiply to the square input matrix's row count. Indices
identify subsystems to trace out or transpose, with leftmost index zero.
The two-argument forms retain their inferred-qubit behavior.

For instance, `ptrace(density(|1> ⊗ basis(2,3)),0,[2,3])` keeps the qutrit in
its third basis state. A maximally entangled qutrit pair is
`(basis(0,9)+basis(4,9)+basis(8,9))/sqrt(3)`; tracing either subsystem leaves
`identity(3)/3`. Tracing all subsystems returns the scalar trace. This is the
finite-dimensional subsystem model described in
[IBM quantum information](https://quantum.cloud.ibm.com/docs/en/api/qiskit/quantum_info)
and [DensityMatrix dimensions](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.0/qiskit.quantum_info.DensityMatrix),
using this calculator's explicitly left-to-right dimension order.

The explicit form permits 1–32 subsystem factors, positive integer dimensions
(including trivial dimension 1), and a total dimension up to 512. It preserves
surviving factor order; listing trace indices in a different order does not
reorder the output. Partial transpose swaps selected row/column subsystem
coordinates without conjugating the entries. Other indexed circuit operations
still use qubit dimensions; this extension does not imply qudit gate synthesis.

## Finite-dimensional Weyl operators

`shift(d)`, `clock(d)`, and `fourier(d)` return d by d matrices for integer
dimensions 2–64. With omega = exp(2 pi i/d), their conventions are:

* shift(d) basis(j,d) = basis((j+1) mod d,d).
* clock(d) basis(j,d) = omega^j basis(j,d).
* fourier(d)[r,c] = omega^(r c)/sqrt(d), with zero-based r,c.

These shift/clock definitions follow the
[True-Q qudit mathematics reference](https://trueq.quantumbenchmark.com/guides/fundamentals/qudit_math.html).
Consequently Z X = omega X Z and F X F-dagger = Z. The positive-exponent
Fourier convention matches the existing QFT function: `fourier(2^n)` is
`QFT(n)`. At d=2 the three operators are X, Z, and H. Matrix powers and daggers
remain available for inverses and generalized Pauli products.

Numeric subscripts on X and Z are deliberately not assigned dimension semantics:
X_3 can denote a wire in circuit notation. Use explicit dimension calls to avoid
that ambiguity. Qudit operators work with ordinary tensor/matrix products and
the explicit-dimension partial traces; indexed `apply` still selects qubit wires.

## Windows circuit composer

The editor allocates its remaining window height to the diagram. Measurement
help and the equivalent expression are collapsible; circuit persistence and
export commands are in the preview's File menu, with presets in Examples.
A 25–150% zoom slider changes the diagram's layout transform. Fit wires
fits the register vertically and rechecks its scale after horizontal scrollbar
appearance. Long circuits remain horizontally scrollable. When the window is
too small for editing controls plus a usable diagram, the outer editor scrolls,
keeping both the gate action and calculator action reachable. View controls
do not mutate expressions or the saved circuit schema.

The `--circuit-layout-test <report-path>` GUI diagnostic checks three- and
eight-qubit, 64-step circuits at 1040x780, 800x550, and 1360x960. It exercises
editing, expanded details, zoom, fit from a reduced scale, viewport extents,
action visibility, and expression preservation. The default three-wire layout
must fit at 100% even when a horizontal scrollbar is needed. Rendered three-
and eight-wire examples were also inspected. `--circuit-preview <image-path>
<circuit-path> --fit` renders a fitted overview for visual verification.

The native GUI includes a visual circuit editor for 1–8 qubits and up to 24
steps, starting from the all-zero computational basis state. It draws supported
single-qubit gates, rotations, controlled X/Z, SWAP, and Toffoli with ordered
wire placement. It exports sequential indexed `apply` calls into the ordinary
calculator input. Expressions preserve gate order, global phase, and the
leftmost-zero wire convention. Rotation parameters are evaluated by the backend
when the generated expression is calculated. This is circuit construction, not
recognition of arbitrary diagrams or a quantum programming-language importer.
The composer saves and opens versioned JSON `.qcircuit` files containing the
register size and ordered gate/wire/angle data. Loading validates the complete
file before modifying the current circuit. Unsaved edits are temporary; changing
the qubit count clears the circuit.

## Compact Pauli strings

`pauli("XYZ")` (also `Pauli(XYZ)`) means X tensor Y tensor Z. Optional
prefixes +, -, i, +i, and -i carry the global phase. Whitespace within a label
is ignored, but the operator letters must be uppercase I, X, Y, Z. Labels
contain 1–9 operators; the dense matrix allocation limit still applies.

The [IBM Pauli reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.0/qiskit.quantum_info.Pauli)
uses this tensor-label convention and phase prefixes. The matrix ordering agrees,
while subsystem numbering here starts at the leftmost character rather than
Qiskit's rightmost character. Explicit pauli() calls distinguish tensor labels
from ordinary operator multiplication: `X Y` remains the matrix product XY.

Weighted sums can express Hamiltonians directly, for example
`expect(pauli("XX")+pauli("YY")+pauli("ZZ"),(|01>-|10>)/sqrt(2))` returns -3.
Labels also work with dagger, indexed gate application, and evolution. They
currently expand to dense matrices; they do not imply a sparse-Pauli simulator.

## General single-qubit U gates

`U(theta,phi,lambda)` and `U3(theta,phi,lambda)` use the matrix
`[cos(theta/2), -exp(i lambda) sin(theta/2); exp(i phi) sin(theta/2), exp(i(phi+lambda)) cos(theta/2)]`.
This follows the [IBM UGate reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.UGate)
using the explicitly stated Qiskit matrix. In particular it equals
`exp(i(phi+lambda)/2) Rz(phi) Ry(theta) Rz(lambda)`, with the phase retained.
The phase must not be discarded when constructing a controlled gate.

`U2(phi,lambda)` fixes theta to pi/2; `U1(lambda)` fixes theta and phi to zero,
so U1 equals P. TeX forms `U_{1}`, `U_{2}`, and `U_{3}` are also accepted.
Angles are in radians. Real parameters produce a unitary gate; complex or
symbolic inputs are evaluated algebraically without a physical-unitarity check.
For examples, U2(0,pi) is H and U1(pi/2) is S. These names denote matrices,
not OpenQASM programs, and do not change the parser's programming-language limits.

The composer offers U3 with three comma-separated angles. Its OpenQASM export
uses P(lambda), Ry(theta), P(phi) in that execution order, preserving the exact
matrix. This avoids depending on a built-in U definition's phase convention:
the [OpenQASM 3.0 gate specification](https://openqasm.com/versions/3.0/language/gates.html)
currently presents an exponential-form U with an additional theta-dependent
phase. The calculator's U/U3 matrix remains the explicit one above.

Exact evaluation can retain unsimplified complex roots for some rational-pi
Euler angles (for example pi/4 combined with pi/6). In such cases even an
algebraically unitary product may display a formal expression rather than an
identity. This is a simplification limit of the underlying exact engine, not
a physical-unitarity certificate; the U matrix formula above defines the gate.

## Numerical evaluation in the Windows app

The evaluation selector offers exact (default) and numerical modes. Numerical
mode uses libqalculate's APPROXIMATION_APPROXIMATE policy at 30-digit working
precision and significant-digit interval formatting. It can evaluate the formal
complex-root expressions noted above without changing their underlying formulas.
The result's approximate metadata drives the GUI badge; operations that remain
exact may still receive the exact badge. Working precision does not certify a
30-digit result for ill-conditioned expressions. History restores the selected
mode. The worker exposes the same option with `--approx`, optionally combined
with `--json`; the ordinary libqalculate API evaluation policies are unchanged.

## State purity and observable variance

`purity(state)` accepts a ket or density matrix. Nonzero kets have purity one;
density inputs return `tr(ρ²)/tr(ρ)²`. This normalizes scaled inputs explicitly,
so a maximally mixed d-dimensional state has purity 1/d. For normalized states,
this is the [IBM purity definition](https://quantum.cloud.ibm.com/docs/api/qiskit/1.0/quantum_info).
A Bell pair has purity one, but either reduced qubit has purity one half.

`variance(A,state)` computes the normalized second moment minus the square of
the normalized first moment, following the observable-variance formula in
[PennyLane's device reference](https://docs.pennylane.ai/en/stable/_modules/pennylane/devices/_legacy_device.html).
It checks that A is Hermitian and rejects incompatible dimensions and zero
norm/trace. For example, `variance(Z,|+>)` is one while `variance(Z,|0>)` is zero.
Adding a scalar identity to A does not change variance; scaling A by c scales
variance by c². Existing `expect` remains an unnormalized expectation.

These routines assume valid physical states and do not certify positivity.
Purity accepts up to 1024 rows and 262144 elements. Numerical cancellation may
leave small residuals near zero; outputs are not silently clipped to a physical
range. This is observable variance, not statistical sample variance.

## OpenQASM circuit export

The Windows circuit composer exports OpenQASM 3.0 with `stdgates.inc`, following
[the OpenQASM specification](https://openqasm.com/versions/3.0/index.html) and its
[standard gates](https://openqasm.com/language/standard_library.html).
Composer gates map to lowercase standard names (CNOT becomes `cx`). The register
is reset to zero before the original gate sequence. Wire q0 maps to q[0]; other
tools may display statevectors and bitstrings with a different endian convention.
No measurements are inserted.

Export angles accept numeric literals, pi or π, unary signs, + - * /, and
parentheses. Multiplication must be explicit. Numeric literals become floating
point so `1/2` retains calculator division semantics. Unsupported functions,
variables, and syntax are rejected before saving. The calculator accepts a
broader expression language than this exporter.

The independent openqasm3 1.0.1 reference parser checks GUI-generated fixtures
for every composer gate, ordered nonadjacent wires, and floating division.
Run `windows/test-qasm-export.py` after the GUI smoke test with the optional
development dependency `openqasm3[parser]`. These checks validate syntax and the
inspected AST, not hardware execution. General QASM import, classical control
flow, and arbitrary quantum program interpretation remain unsupported.

The composer also supports CY, CH, CCZ, and CSWAP. CY/CH place a control dot
on the first selected wire and a Y/H box on the second. CCZ uses three dots;
CSWAP uses one control dot and two crossed swap targets. The ordered wire list
defines these roles even when wires are nonadjacent or reversed. OpenQASM export
uses `cy`, `ch`, and `cswap` from the standard library; CCZ uses `ctrl(2) @ z`
with the first two arguments as controls. These are the specification's
[gate modifier semantics](https://openqasm.com/language/gates.html).

## Square-root X and adjoint gate aliases

`SX` is the conventional square root of X, with matrix
`[1+i,1-i;1-i,1+i]/2`, following the
[IBM SX definition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.2/qiskit.circuit.library.SXGate).
Its exact phase matters when controlled: SX squared equals X, whereas Rx(pi/2)
squared equals -iX. `SXdg` is its adjoint; `Sdg` and `Tdg` are aliases for
S† and T†. Unicode daggers and TeX dagger superscripts remain available.
Names are case-sensitive. `SX` denotes one gate; write `S X` or `S*X` for
the product of S and X. This does not implement arbitrary matrix square roots.

All four gates are available in the composer. OpenQASM exports Sdg/Tdg/SX as
`sdg`/`tdg`/`sx`; SXdg uses `inv @ sx`, since the standard library does not
define an `sxdg` gate. Tests check matrix action, adjoints, square identities,
controlled phase, saved-circuit preservation, and the exported inverse modifier.

## Qubit reset

`reset(state,indices)` reinitializes selected qubits to zero, leaving the other
subsystems in their reduced state. A scalar index or list is accepted; indices
are distinct, zero-based, and counted from the left. `reset(state)` resets all
qubits. The result is always a density matrix, including for ket inputs: reset
can destroy entanglement and leave a mixed state. A list of no indices returns
the input density matrix (or the ket's outer product).

The map is the trace-preserving channel with Kraus operators |0><0| and |0><1|
on each selected wire. This follows the deterministic-zero special case of
[PennyLane's reset channel](https://docs.pennylane.ai/en/stable/code/api/pennylane.ResetError.html)
and the subsystem operation described by
[IBM DensityMatrix.reset](https://docs.quantum.ibm.com/api/qiskit/qiskit.quantum_info.DensityMatrix).
Implementation traces the reset indices and reinserts zero projectors without
constructing full-system Kraus matrices. It preserves the supplied trace/norm
weight rather than normalizing. Inputs must have a power-of-two dimension from
2 through 512; positivity is assumed, not certified.

For example, resetting wire 0 of (|00>+|11>)/sqrt(2) produces
diag(1/2,1/2,0,0), with purity 1/2. This is deterministic ensemble evolution,
not sampled measurement or postselection. Subsequent `apply` operations act on
the resulting density matrix. The composer offers a one-wire Reset step and
exports it as an OpenQASM `reset` instruction in its original position.

## Measurement with discarded outcomes

`dephase(state,indices)` implements complete computational-basis dephasing on
selected qubits. `dephase(state)` selects all qubits. It returns the density
matrix sum over measurement outcomes, retaining entries whose selected row and
column bits agree and removing the other entries. The map is equivalently the
sum of the projector branches P_j ρ P_j. This follows the completely dephasing
channel in [IBM's noise and errors course](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/noise-and-errors).

For a Bell state, the result is the equally weighted mixture of |00><00| and
|11><11|: Z correlations survive, X correlations do not. Coherence on unmeasured
wires is preserved. Index rules, input bounds, conversion of kets to density
matrices, and trace preservation match `reset`; an empty index list is the
identity channel. This is complete dephasing, not a parameterized noise strength.

The composer calls this operation Measure (shown as M), with an explicit note
that the Z-basis outcome is discarded. It exports `measure q[index];` using the
[OpenQASM measurement statement grammar](https://openqasm.com/grammar/index.html).
A hardware execution yields a random branch; the calculator computes the
ensemble state with the classical result forgotten. This does not provide
sampling, classical result registers, or conditional feed-forward.

## Measurement-conditioned operations

`feedforward(state,measured,outcome,U,targets)` measures the selected qubits in
the computational basis and applies U to the target wires only in the specified
outcome branch. It returns the sum of all branches as a density matrix; no branch
is discarded or renormalized. Both wire lists use zero-based indices counted from
the left. The first listed measured wire is the most significant outcome bit.
For example, on |100>, measured=[2,0] has outcome 1, whereas [0,2] has outcome 2.
The outcome must be an integer in [0,2^k); each list must have distinct indices.
Target wires may overlap measured wires, allowing `feedforward(|+>,0,1,X,0)`
to reset a qubit by measurement and correction. An empty measured vector with
outcome zero gives an unconditional operation.

Mathematically this is the sum over projectors P_j of P_j ρ P_j, with the chosen
branch replaced by U P_j ρ P_j U†. U is applied using the ordered target list,
as in `apply`. The input bounds match `dephase` (up to 512 rows). As with `apply`,
U is assumed physically valid; no unitary certificate is attempted, and a
nonunitary operator need not preserve trace. A zero-probability selected outcome
leaves the other branches intact. A later call performs a new measurement, not
a lookup of an earlier classical register. Thus this is an ensemble operation,
not an interpreter for general classical programs.

The bundled teleportation example follows the conditional X then Z correction
in [IBM's teleportation lesson](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/quantum-teleportation).
It prepares an entangled resource on wires 1 and 2, applies CNOT(0,1) and H(0),
measures wire 1 with an X correction on wire 2, then measures wire 0 with a Z
correction on wire 2. Tracing out wires 0 and 1 recovers the input state on wire 2.
Tests compare complete output density matrices for six Pauli eigenstates, an
unequal complex superposition, and a maximally mixed input. The example library
offers editable calculator notation. The composer also offers a teleportation
preset with measurement-conditioned Pauli corrections, as described below.

Quantum-prefixed expressions bypass ordinary unit-conversion suffix detection,
so the ASCII minus ket `|->` is not split at its closing arrow. Use Standard
calculator mode for unit conversions such as `1 m -> cm`; that path is unchanged.

## Visual measurement feedback

The composer provides M0-X, M1-X, M0-Z, and M1-Z steps. Each measures the first
wire and applies X or Z to the second wire if the result matches the indicated
bit. These two wires must be distinct in the editor. Dashed connections link
the M box to the correction box, whose label states the gate and required bit.
Every such step performs a new measurement; it does not reuse a stored result.
The Teleport example prepares |i> on q0 and transfers it to q2 using a Bell
resource and two conditional corrections. Inspect Bob with `ptrace(result,[0,1])`.

Export declares a fresh classical bit for each feedback step, assigns the
measurement result, and emits a conditional gate block following
[OpenQASM 3 branching rules](https://openqasm.com/versions/3.0/language/classical.html).
The calculator evaluates the ensemble density matrix; a QASM backend executes
individual measurement outcomes. Export tests inspect the AST connections among
bit declarations, measurements, conditions, and target gates. This supports the
listed feedback steps, not general classical programs or QASM import.

## Controlled phase and rotations

`CP(theta)`, `CRx(theta)`, `CRy(theta)`, and `CRz(theta)` are the controlled
forms of P, Rx, Ry, and Rz, with the first tensor factor as control. Their matrices
are block diagonal diag(I,U). The uppercase aliases CRX/CRY/CRZ and textbook
subscripts such as `CR_{z}(theta)` are accepted. Angles are in radians; symbolic
angles are retained. CP is diag(1,1,1,exp(i theta)); CRz is
diag(1,1,exp(-i theta/2),exp(i theta/2)). They are distinct even after allowing
a global phase on the whole two-qubit register. The definitions follow
[the OpenQASM standard gates](https://github.com/openqasm/openqasm/blob/main/examples/stdgates.inc).

The visual composer provides all four gates, with the control wire listed first,
an axis/phase label on the target, and the angle below the step. Saved circuits
preserve the angle expression and ordered wires; exports use cp/crx/cry/crz.
Tests check exact matrix action, the relative phase on a superposed control,
nonadjacent reversed wires, and a complete two-qubit QFT decomposition on all
four basis states. The example library demonstrates H, CP(pi/2), H, SWAP giving
the positive-exponent QFT(2) convention, including the final bit reversal.

## Dimension-qualified basis notation

A d-level computational basis has indices 0 through d−1, as described in
[Criteria for Exact Qudit Universality](https://arxiv.org/abs/quant-ph/0407223).
The parser accepts an explicit dimension suffix: `|2>_3`, `|2⟩_{3}`, and
`\ket{2}_{3}` all mean `basis(2,3)`. Bras use `<2|_3`; compact inner products
such as `<1|2>_3` apply the dimension to both labels. For a matrix element,
qualify each side: `<0|_3 shift(3)|2>_3`. Outer products and mixed-dimensional
tensor products also work, for example `|2>_3 <2|_3` and `|1> ⊗ |2>_3`.

In this syntax, numeric subscripts on bras/kets explicitly mean dimension,
not a circuit wire label. Dimensions evaluate to integers from 2 through 1024;
qualified labels evaluate to decimal integer indices smaller than that dimension.
For example, `|k+1>_4` works inside an indexed expression. Use braces or parentheses for dimension expressions, such as `|k>_{2^3}`
or `|k>_(2^3)`. Unresolved dimensions and named-state subscripts remain
unsupported. `basis(k,d)` is the equivalent function form. With no suffix, binary strings retain
their qubit interpretation, including leading zeros. Thus `|10>` has four
entries and selects index 2, while `|10>_16` has sixteen entries and selects
index 10. Bare nonbinary numeric labels are rejected instead of becoming scalars.

Tests cover orthogonality, bras, outer products, TeX macros, a qutrit cyclic
shift, mixed qubit–qutrit partial trace, the 1024-dimensional boundary, invalid
labels, and mismatched dimensions. The visual circuit composer remains a qubit
editor; the calculator accepts these qudit expressions directly.

## Modular SUM gates

`SUM(d)` or `SUM_{d}` for a literal d constructs the qudit controlled-addition
gate: |c> ⊗ |t> maps to |c> ⊗ |(t+c) mod d>. The first factor is the control;
the second is the target. `CADD(d)` is an alias. This follows the modular SUM
operation demonstrated in
[High-dimensional optical quantum logic in large operational spaces](https://www.nature.com/articles/s41534-019-0173-8).
At d=2 it equals CNOT. For d>2 it generally differs from its own inverse; use
`SUM(d)†` for modular subtraction.

`SUM(dc,dt)` and `CADD(dc,dt)` allow different control and target dimensions,
with addition modulo dt. Such hybrid gates are discussed in
[Quantum gates on hybrid qudits](https://arxiv.org/abs/quant-ph/0211185).
Dimensions must evaluate to integers from 2 through 64 and their product must
not exceed 512. Output is an exact dense permutation matrix, ordered with the
control as the most significant tensor factor. Use matrix multiplication on
explicit tensor states; indexed `apply` remains specific to qubit wires.

The qutrit example prepares Fourier(3)|0> on the control and zero on the target,
then applies SUM(3). The output is (|00>+|11>+|22>)/sqrt(3), expressed with
explicit qutrit tensor factors. Either reduced state is I/3. Tests verify all
nine qutrit basis transitions, inverse action, the CNOT limit, the order-three
identity, mixed dimensions, and the reduced-state purity.

## Subsystem permutations

`permute(state,order)` reorders qubit tensor factors. The list states the new
order of the old factors: [1,2,0] changes a⊗b⊗c to b⊗c⊗a. This follows the
convention of [QuTiP's tensor permutation](https://qutip.readthedocs.io/en/stable/_modules/qutip/core/qobj.html).
For example, `permute(|01>,[1,0])` is |10> and is equivalent to applying SWAP.
Bras and square operators are supported too; operators permute both row and
column indices, equivalent to P A P†. Flat vectors are treated as bras, matching
libqalculate's representation of a one-row matrix.

`permute(state,order,dimensions)` specifies mixed subsystem dimensions. For
example, `permute(|+> ⊗ |2>_3,[1,0],[2,3])` is |2>_3⊗|+>. Its output dimensions
are [3,2]; use these dimensions for later mixed-dimension operations. Results
are ordinary matrices and do not carry hidden subsystem metadata. Omitting
dimensions infers qubits from a power-of-two total dimension.

The order must contain every subsystem exactly once. Explicit dimensions are
positive integers, with at most 32 factors and product at most 1024; square
matrices remain limited to 262144 elements. Unit-dimensional factors are allowed.
This is exact index rearrangement: amplitudes, phases, and coherences are copied
without approximation or normalization. Tests compare against SWAP, inverse and
cyclic permutations, complex density matrices, and qubit–qutrit tensor products.

## Operator vectorization and double kets

`vec(A)` stacks the columns of a matrix into one column vector. For example,
vec([1,2;3,4]) is [1;3;2;4]. `unvec(v,r)` reconstructs a matrix with r rows by
unstacking its columns; r must divide the vector length. Rectangular matrices
are supported. The limit is 1024 entries; flat input vectors to vec are treated
as single-row matrices, matching libqalculate's matrix representation.

`|A>>` and `|A⟩⟩` denote vec(A), and `<<A|` denotes vec(A)†. Compact inner
products such as `<<A|B>>` evaluate the Hilbert–Schmidt product tr(A†B), without
normalization. Unicode ⟪ and ⟫ and repeated TeX angle commands are accepted.
Labels inside double brackets may be built-in gate names, names of defined
matrix variables, or parenthesized expressions such as `|(X+iY)>>` and
`<<(density(|i>))|`. Grouping is required for expression labels; `vec(expression)`
is equivalent. Spaces between operators and inside quoted strings are preserved.
The same parser depth and node limits apply inside labels. Thus
`|Y⟩⟩` is [0;i;−i;0] and `⟪Y|Y⟫` is 2. Double-ket numeric state labels are not
an alternative to ordinary basis kets.

The convention follows
[QuTiP's column-stacked operator representation](https://qutip.readthedocs.io/en/qutip-5.0.x/guide/guide-states.html).
Other publications use row stacking; their formulas must be converted explicitly.
Here vec(AXB) = (Bᵀ⊗A)vec(X), so conjugation by U is represented by U*⊗U.
Tests check both identities with complex matrices, rectangular round trips,
operator inner products, notation variants, and rejected dimensions. Results
are ordinary matrices without hidden operator-space metadata. Kraus conversion
to channel matrices is described below.

## Kraus, superoperator, and Choi representations

`superop(vector(K0,K1,...))` returns the column-vectorized channel matrix
S = Σ conjugate(Kj) ⊗ Kj, satisfying vec(E(ρ)) = S vec(ρ).
This agrees with [IBM's SuperOp convention](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.SuperOp).
`choi(vector(K0,K1,...))` returns J = Σ vec(Kj)vec(Kj)†, ordered as input ⊗ output.
J is not divided by input dimension: a trace-preserving channel has trace(J)
equal to its input dimension and partial trace over output equal to the input
identity. See [IBM's representation equivalence lesson](https://eu-de.quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/representation-equivalence).

All Kraus matrices must have the same shape. Rectangular input/output mappings
are accepted, with rows giving output dimension and columns giving input
dimension. Each dimension is at most 32, each Kraus matrix has at most 512
entries, and a list contains 1–256 matrices. Channel matrices have at most
262144 entries. Flat vector Kraus entries are treated as row matrices, permitting
trace channels. Use `vector(...)` explicitly to retain the list of operators.

The conversions preserve the supplied map and do not normalize or certify Kraus
completeness. For square channels, `unvec(superop(Ks)vec(rho),rows)` agrees with
`channel(rho,Ks)`. Superoperator multiplication composes channels right to left.
Tests verify this with phase gates and amplitude damping, Choi partial traces,
a 2-to-3-dimensional isometry, a trace channel, and Kraus phase invariance.
No inverse Choi-to-Kraus factorization or automatic subsystem metadata is provided.

### Excitation exchange: iSWAP and fSim

#### Fractional matrix powers and square-root gates

`X^(1/2)`, `sqrt(X)`, and `\sqrt{X}` now evaluate to SX. Likewise
`sqrt(Z)=S`, `sqrt(S)=T`, `sqrt(CNOT)=controlled(SX)`, and `sqrt(SWAP)`
has its central 2x2 block `[(1+i)/2,(1-i)/2;(1-i)/2,(1+i)/2]`.
These are matrix functions, not elementwise square roots. Parenthesize powers:
`(X^(1/3))^3` is X, while `X^(1/2)^2` means X^(1/4), following ordinary
right-associative exponentiation. Standard calculator mode is unchanged.

Unicode radicals √ (U+221A), ∛ (U+221B), and ∜ (U+221C) are recognized as
prefix operators, following the character names in the
[Unicode mathematical operators chart](https://www.unicode.org/charts/PDF/U2200.pdf).
Their operands are the following signed power expression. Consequently
`√X²` means `sqrt(X²)`, `(√X)²` squares the root, `√9*4` is 12, and
`√(9*4)` is 6. A dagger belongs to the operand unless the root is grouped:
`√X†` means `sqrt(X†)` and `(√X)†` is the adjoint of the root. Use explicit
parentheses to express the intended extent of a printed radical's vinculum.

Radicals can be nested or multiplied implicitly: `√√16=2`, `H√X=H*SX`,
and `√SWAP|01>` applies a square-root SWAP gate. They use the same principal
complex branch as fractional powers, including for scalars: `∛(-8)` is
`1+i*sqrt(3)`. No real-only odd-root convention is implied in quantum mode.
Radicals inside quoted labels are not rewritten. Prefix nesting shares the
parser's 256-frame depth bound. Regression checks cover grouping, adjoints,
matrix literals, negative scalars, Unicode powers, nested roots, multiplication,
matrix elements, grouped operator labels, and malformed or excessive nesting.
The Windows notation palette includes a square-root insertion button.

#### Matrix logarithms and Hamiltonian generators

`logm(A)` computes the natural matrix logarithm. The defining reconstruction
is `expm(logm(A)) = A`, as described in the
[SciPy matrix logarithm documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.logm.html).
For a gate U and evolution convention exp(-iHt), `H=i*logm(U)` is a
unit-time generator. For example `evolution(i*logm(X),1)|0>` is |1>.
Global phase is retained.

The branch uses eigenvalue arguments in (-pi,pi], choosing +pi at -1.
Strictly, the analytic principal logarithm is uniquely defined away from the
negative real axis; our explicit boundary choice extends it to common gates
with eigenvalue -1. [Higham's discussion of the matrix logarithm](https://nhigham.com/2020/11/17/what-is-the-matrix-logarithm/)
explains this branch restriction and nonuniqueness. Accordingly
`logm(-I)=i*pi*I`, and `logm(X)=i*pi*(I-X)/2`.
`logm(expm(A))` need not equal A, and `logm(U†)=-logm(U)` can fail on the
branch boundary. Recovering a gate does not determine its original physical
Hamiltonian or elapsed time uniquely.

The supported domain is square matrices up to 64x64: diagonal matrices and
involutions up to 16x16 have exact formulas; general finite numeric nonsingular
unitary or Hermitian matrices use the same spectral decomposition as fractional
powers. Diagonal symbolic entries retain scalar logarithms and their usual
nonzero-domain conditions. Exact scalar logarithms may remain unevaluated.
General nonnormal matrices are not supported. Zero eigenvalues are rejected.

On the numerical path, the matrix-power validation, precision limits, branch
tolerance (1e-12 near the negative real axis), Hermiticity tolerance (1e-12
relative), unitarity tolerance (1e-11), and scaled near-zero cutoff (1e-13)
apply. The scalar spectral function is ln|lambda|+i arg(lambda). Scaling is
handled by adding logarithms, avoiding overflow from intermediate eigenvalue
products. Unitary logarithms are projected onto the skew-Hermitian part to
remove floating-point asymmetry; the unitary classification uses the same
1e-11 magnitude tolerance. The result is an approximate matrix with 12-digit
display precision, without a certified error bound.

`windows/test-logm.py` constructs independent dense complex matrices with
known spectra at dimensions 2, 3, 4, 8, and 16. It checks unitary phase pairs,
the +pi branch, positive and indefinite Hermitian matrices, and scales 1e-200
and 1e200. Reconstruction checks include a 64x64 Fourier gate and direct
Hamiltonian evolution. Fractional-power tests are retained because both
operations share spectral machinery. GUI tests cover exact and approximate
matrix-logarithm results.
The 64x64 exponential/logarithm round trip exceeded its initial 30-second test
limit and passed with a 180-second allowance. Large composed expressions can
exceed the GUI's default 15-second allowance; select 3 or 10 minutes for those
calculations. Cancel terminates the worker and keeps interrupted results out of
history. GUI control tests exercise immediate cancellation, cancellation during
work, timeout cleanup, and successful reuse with all four time allowances.

#### Pasted multiplication and division

Multiplication signs `×`, `⋅`, `·`, `∙`, and `∗` are normalized to `*` before
quantum tokenization; division signs `÷`, `∕`, and `⁄` become `/`. These
characters and their mathematical use are covered by
[Unicode's mathematical-symbol chapter](https://www.unicode.org/versions/Unicode16.0.0/core-spec/chapter-22/).
The normalization is necessary before gate-name recognition: leaving X×Y
to the underlying scalar parser loses the intended gate bindings.

In quantum mode these are ordinary scalar/matrix products and divisions,
with the same precedence and left associativity as their ASCII forms. Thus
`X×Y=iZ`, `Y×X=-iZ`, `8÷2÷2=2`, and `Rx(π∕2)` denotes the usual rotation.
Tensor products still use ⊗ or @; a multiplication sign does not select a
vector cross product or Hilbert-space tensor product. Prefix radicals keep
their documented scope, so `√9×4=12` and `√(9×4)=6`.

Double-quoted labels are preserved byte for byte by this normalization.
Mathematical asterisk after a caret follows the existing conjugation syntax:
`Y^∗` is `conj(Y)`, while `X∗Y` is a matrix product. Tests cover each spelling,
noncommuting gates, scalar coefficients, bra/ket products, matrix elements,
TeX arguments, Unicode roots, quoted-label rejection, and missing or repeated
operators. The GUI evaluates copied multiplication and rotation expressions.

Fractional powers use principal eigenvalue arguments in (-pi,pi], including
the +pi choice at -1. The global phase is retained. This distinction is
discussed in [Cirq's gate conventions](https://quantumai.google/cirq/gatezoo),
while [Qiskit's Operator.power documentation](https://quantum.cloud.ibm.com/docs/en/api/qiskit/1.4/qiskit.quantum_info.Operator)
describes branch-cut sensitivity near -1. In particular X^(1/2) is SX, not
Rx(pi/2); the two differ by a global phase that matters under control.

All fractional matrix inputs must be square and at most 64x64. Diagonal
matrices use scalar powers on the diagonal and can retain symbolic entries
or exponents. For dimension at most 16, an exact A²=I check enables the
projector formula `(I+A)/2 + (-1)^t*(I-A)/2`. This also works for non-Hermitian
involutions. Integer matrix powers retain the existing engine's behavior.

Other finite numeric unitary and Hermitian matrices use a double-precision
spectral method. Real exponents must have magnitude at most 1,000,000; broad
uncertainty intervals and symbolic exponents are rejected on this path.
Unitary matrices must satisfy U†U=I within 1e-11 per entry. For general
unitaries, the real and imaginary Hermitian parts commute. The implementation
diagonalizes the real part's real symmetric embedding, then the imaginary
part within each cosine eigenspace (cluster tolerance 1e-10). This resolves
opposite eigenphases with identical cosines. Each eigenvector's residual is
checked against 1e-10 before its spectral projector contributes to the result.
The embedding duplicates complex eigenvectors, so the projector sum is halved.

Hermitian inputs are checked to relative tolerance 1e-12 and scaled before
diagonalization. Positive eigenvalues use real scalar powers; negative ones
use argument +pi. Eigenvalues below 1e-13 in the scaled matrix are treated as
zero; negative powers involving those eigenvalues are rejected. For unitary
eigenvalues on the negative real axis, imaginary components below 1e-12 use
argument +pi consistently. These numerical tolerances deliberately resolve
rounding-scale ambiguity and cannot distinguish states arbitrarily close to
the branch cut or a singular matrix. Results are approximate with up to 12
displayed significant digits, reduced for large exponents; this is not a
certified error bound or an arbitrary-precision matrix-power algorithm.
General nonnormal matrices (for example a Jordan block) remain unsupported.

`windows/test-gate-powers.py` independently constructs dense complex matrices
from prescribed spectra and Fourier bases. It covers positive and negative
fractional exponents, repeated cosine eigenvalues, the negative real axis,
Hermitian matrices with positive/negative/zero eigenvalues, and matrices up
to 16x16. Separate 32x32 and 64x64 Fourier checks verify squaring a numerical
root recovers the original matrix. Exact regression checks cover square-root
gates, scalar compatibility, TeX roots, symbolic diagonal powers, controlled
roots, and invalid inputs. The GUI tests exact and approximate result display.

#### Echoed cross-resonance

`ECR` follows the physical operand ordering of [IBM's ECRGate definition
(Qiskit 2.3)](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.3/qiskit.circuit.library.ECRGate).
This app writes the first operand on the left in tensor products; Qiskit's
matrix for operands (q0,q1) uses the opposite significance. Consequently our
matrix is `(X @ I - Y @ X)/sqrt(2)`, the bit-reversed version of that matrix.
It maps |00> to (|10>-i|11>)/sqrt(2), is Hermitian, and squares to identity.

The exact decomposition is
`exp(-i*pi/4)*(X @ I)*CNOT*(S @ SX)` (rightmost acts first).
Equivalently it is `Rzx(-pi/4)*(X @ I)*Rzx(pi/4)` under this app's Rzx
convention. OpenQASM export uses `gphase(-pi/4.0)`, S on operand zero, SX on
operand one, CNOT in that order, then X on operand zero. Keeping global phase
preserves exact amplitudes and allows coherent controlled use of the matrix.

The composer accepts two distinct ordered wires, shows their operand numbers,
and supports editing and save/open. Tests check all matrix columns, unitarity,
Hermiticity, both decompositions, controlled action, and a reversed nonadjacent
wire pair with an idle qubit. An independent Python complex-amplitude simulator
checks every basis input against the actual exported OpenQASM sequence.

#### Exchange gates

`iSWAP` (alias `ISWAP`) exchanges |01> and |10> with a factor of i,
leaving |00> and |11> unchanged. `fSim(theta,phi)` (alias `FSim`)
has the central block `[cos(theta),-i sin(theta);-i sin(theta),cos(theta)]`
and phases |11> by exp(-i phi). Both angles are radians. This follows
[Cirq's fSim convention](https://quantumai.google/reference/python/cirq/FSimGate)
and [IBM's iSWAP matrix](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.iSwapGate).
In particular, fSim(-pi/2,0) = iSWAP, while fSim(0,phi) = CP(-phi).
The exchange sign is significant; iSWAP is not SWAP times a global phase.

The circuit composer supports iSWAP on any two distinct wires. Its OpenQASM
export uses SWAP, S on each wire, then CZ, preserving the full matrix including
the |11> phase. The two-parameter fSim gate is also available in the composer:
enter `theta, phi` in its angle field. Its export implements Rxx(theta),
Ryy(theta), and CP(-phi), using H/Rx basis changes and CX–Rz–CX parity
rotations. The commuting XX and YY generators give the stated central block
without an extra global phase. Export tests parse the generated program and
compare its action on every three-qubit basis vector with fSim on wires 2,0.

### Grover search and amplitude amplification

`phaseoracle(n,marked)` constructs the diagonal reflection I − 2Πmarked.
The second argument is one decimal basis index or a vector of distinct indices,
for example `phaseoracle(3,[1,6])` marks |001> and |110>. Bit zero is the
leftmost, most significant tensor factor. This is a phase oracle, not a
Boolean-function oracle with an ancillary output qubit. It does not synthesize
an unknown search predicate: the marked set is supplied explicitly.

`diffusion(n)` constructs D = 2|s><s| − I for the uniform n-qubit state |s>.
Thus each matrix entry starts at 2/2^n and each diagonal subtracts 1. It has
eigenvalue +1 on |s> and −1 on orthogonal states. This sign is retained exactly,
including when used in controlled operations. A Grover iteration is the ordered
product `diffusion(n)phaseoracle(n,marked)`; the oracle acts first.

Both functions accept integer qubit counts 1–9 and return dense matrices.
Marked sets must contain 1–2^n distinct integer indices in range; an all-marked
oracle is −I. The dense representation is intended for finite examples and
does not provide a scalable search implementation. They compose with `apply`,
tensor products, daggers, powers and density-matrix operations.

The [IBM Grover tutorial](https://learning.quantum.ibm.com/tutorial/grovers-algorithm)
describes phase marking followed by diffusion. The bundled examples verify
that a single marked item among four is found after one iteration, one among
eight has success probability 121/128 after two iterations, and two among eight
are found with certainty after one iteration. Tests also check the reflection
eigenvalues and involution identities, not just output probabilities.

### Reversible function queries

`oracle(table,m)` implements Uf|x,y> = |x,y XOR table[x]> with the input
register first and m output qubits last. The optional m defaults to 1.
The table is a flat vector containing 2^n outputs in ascending input order,
with 2–256 entries. Each entry is a decimal integer from 0 to 2^m−1.
Output width is 1–8 qubits; the two registers together are limited to 9 qubits.
The table must be supplied explicitly; this operation constructs a dense
matrix and does not compile arbitrary predicates or provide a search speedup.

This follows the [IBM query-model definition](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/query-model-of-computation).
The operation is unitary and its own inverse for every valid table, including
noninjective functions. It XORs into y rather than replacing y. For example,
`oracle([0,1])` is CNOT, `oracle([0,0,0,1])` is Toffoli, and
`oracle([2,1],2)|011>` gives |001>. Decimal output 2 means the binary string 10.

For one output qubit initially in |−>, the query kicks back a phase
(−1)^f(x) onto the input. The bundled Deutsch–Jozsa example uses the balanced
parity truth table [0,1,1,0]. A constant table returns the all-zero input result
after the final Hadamards; that conclusion relies on the constant-or-balanced
promise and is not a general test of arbitrary tables. Tests check every basis
mapping for a repeated-output, two-bit table, as well as phase kickback,
involution, nonadjacent placement and invalid values.

### Modular multiplication and order finding

`modmul(a,N)` is the reversible multiplication operator used in order finding:
it sends |x> to |a x mod N> for x below N, and fixes all basis states x >= N.
The register has ceil(log2(N)) qubits, so the matrix dimension is the smallest
power of two at least N. This explicit extension keeps unused basis states
orthogonal to the modular subspace. Integer N is limited to 2–512, and a must
satisfy 1 <= a < N and gcd(a,N)=1. Noncoprime multipliers are rejected because
they cannot define this reversible operation.

The construction follows the modular-multiplication operator in
[IBM's Shor lesson](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/shor-algorithm).
It is a dense educational matrix, not a scalable arithmetic-gate synthesis or
a complete factoring routine. Powers, adjoints, `controlled` and `apply` work
with it. For example, modmul(2,15) cycles 1 → 2 → 4 → 8 → 1 and its adjoint
equals modmul(8,15). Padded state |1111> stays fixed.

The phase-estimation example prepares the normalized eigenstate
(|0001> − i|0010> − |0100> + i|1000>)/2, whose eigenvalue is i. Counting wire 0
controls the squared multiplier and wire 1 the multiplier itself. Applying
QFT(2)† on those wires yields 01, the binary fraction 0.01 = 1/4. This tests
both inverse-QFT sign and most-significant-first wire ordering. A general
order-finding run starts the work register in |1>, samples eigenphases, then
requires classical rational reconstruction and verification.

### Truncated bosonic Fock-space operators

`destroy(d)` (alias `annihilation(d)`) constructs the lowering operator a;
`create(d)` (alias `creation(d)`) constructs a†; `numberop(d)` constructs
n = a†a = diag(0,1,...,d−1). These are exact dense matrices for integer
truncation dimensions 2–512. They follow the zero-offset definitions in
[QuTiP's operator reference](https://qutip.readthedocs.io/en/qutip-5.0.x/apidoc/functions.html).
Use explicit occupation basis dimensions: `|2>_5` or `basis(2,5)`.
Bare |10> still means the two-qubit computational state, not ten particles.

Below the upper boundary, a|n> = sqrt(n)|n−1> and
a†|n> = sqrt(n+1)|n+1>. The vacuum is annihilated, and raising the top
state also returns zero because the next occupation is outside the truncation.
Consequently [a,a†] = I − d|d−1><d−1|, not I. The number-operator commutators
remain [n,a] = −a and [n,a†] = a†. The examples explicitly expose the boundary
instead of silently treating the matrices as infinite-dimensional operators.

Tensor products construct independent modes. Neither ladder operator is
unitary; do not interpret its action as a deterministic circuit gate or
silently normalize the result. Existing `norm`, `normalize`, `expect`,
`density`, `comm`, matrix exponentials and Hamiltonian evolution compose with
these matrices within their respective size limits. No convergence guarantee
for a chosen truncation or abstract infinite-dimensional algebra is provided.

### Fermions and Jordan–Wigner parity strings

`fdestroy(modes,site)` and `fcreate(modes,site)` construct exact fermionic
annihilation and creation matrices for 1–9 modes. Sites are zero-based,
leftmost first; each computational basis bit is an occupation number.
The annihilator is Z^⊗site ⊗ [(X+iY)/2] ⊗ I^⊗(modes−site−1), with
[(X+iY)/2] = |0><1|. Creation is its adjoint. This uses the Jordan–Wigner
parity-string construction described in the
[QuTiP fermionic-operator reference](https://qutip.readthedocs.io/en/qutip-5.0.x/apidoc/functions.html),
with our occupation and tensor-order conventions made explicit here.

Acting on an allowed occupation state changes the selected bit and multiplies
by (−1) to the number of occupied earlier modes. Destruction of an empty mode
and creation in an occupied mode return zero. For example,
`fdestroy(3,1)|110>` = −|100>, while `fcreate(3,2)|110>` = |111>.
The canonical relations {a_j,a_k†} = δ_jk I and {a_j,a_k} = 0 hold on
the entire finite occupation space; tests cover every pair in three modes.

These operators are not interchangeable with independently tensoring bosonic
two-level lowering matrices: the parity strings are required across sites.
Products a_j†a_j give occupation observables and sums give total particle
number. Build hopping and interaction Hamiltonians from their products and
use `evolution` within its matrix-size limits. Matrices are dense and no
fermionic circuit synthesis, automatic normal ordering, or superselection
validation is implied.

`FSWAP` is the fermionic swap matrix: it exchanges |01> and |10>, fixes |00>,
and negates |11>. It equals CZ SWAP exactly and is its own inverse. Following
[OpenFermion's FSWAP definition](https://quantumai.google/reference/python/openfermion/circuits/FSWAP),
it exchanges adjacent Jordan–Wigner modes: conjugating a mode's creation or
annihilation operator by the adjacent FSWAP yields the neighboring mode's
operator. The composer displays an f beside each swap cross and exports SWAP
followed by CZ. Tests verify all basis states and operator-conjugation identities.

Applying this two-qubit matrix to nonadjacent qubits is allowed, but does not
automatically implement a nonadjacent fermionic mode exchange: occupations
between the modes contribute additional parity signs. Use a sequence of
adjacent FSWAPs when rearranging the full fermionic mode ordering.

### Argument-count validation

Quantum calls reject missing or extra arguments before evaluation. For
example, `dagger(X,Y)` and `diffusion(2,0)` are errors rather than calculations
with an ignored trailing argument. Registration and the generic quantum-call
parser share one signature table so new functions inherit this validation.
Documented overloads such as `ptrace(state,indices[,dimensions])` and
`controlled(U[,count[,state]])` retain their explicit parser rules. Ordinary
libqalculate functions keep their existing argument semantics.

### Operator hats in mathematical TeX

`\hat{X}`, `\hat X` and `\widehat{X+Y}` are accepted in quantum mode.
Here a hat is an operator annotation, following the usage of hatted operators
in [IBM's Hamiltonian documentation](https://docs.quantum.ibm.com/api/qiskit-addon-utils/problem-generators).
It leaves the underlying value unchanged. Names remain intact for subscripts
and function calls: `\hat{\sigma}_{y}` is Pauli Y and
`\hat{\operatorname{destroy}}(3)` is the three-level annihilation matrix.
Compound operands retain grouping under a dagger or power.

Hats do not declare unknown operators, infer a Hamiltonian, quantize a scalar,
or perform a Fourier transform. In particular, `\hat{H}` retains the existing
Hadamard meaning of H. Other accents such as tilde, bar and vector arrows can
carry different semantics and remain unsupported rather than being stripped.
Empty or unclosed hat arguments produce errors.

### Imaginary coefficients next to gate names

An `i` immediately before a complete built-in fixed gate name is an imaginary
coefficient: `iY`, `-iX`, `2iH`, and `iSdg` mean scalar multiplication. The
coefficient remains outside a gate's power or dagger: `iY^2 = i(Y^2)` and
`iY† = i(Y†)`, while `(iY)^2` and `(iY)†` apply to the whole product.
Complete gate names take priority, so `iSWAP` retains its exchange-gate meaning;
`iiSWAP` means i times iSWAP. Use explicit multiplication for parameterized
functions or other identifiers, such as `i*Rz(theta)` or `i*myOperator`.
This rule is confined to quantum notation mode and does not split general
identifiers or interpret `XY` as a tensor product or matrix product.

### Interaction rotations in the circuit composer

Rxx, Ryy, Rzz and Rzx are available as two-wire, one-angle steps. Each means
exp(−i theta A⊗B/2), with the first written axis on the first selected wire.
In particular Rzx(theta) on wires [2,0] applies Z on q2 and X on q0; it is
not a controlled Rx. The diagram labels both Pauli axes and retains the angle.
This follows the interaction-rotation convention in the
[IBM RXX reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RXXGate),
with tensor ordering stated explicitly rather than adopting Qiskit's matrix
bit ordering.

OpenQASM export uses CX–Rz(theta)–CX with H changes of basis for X and
Rx(±pi/2) changes of basis for Y. Z needs no basis change. The construction
retains global phase. The same implementation supplies fSim's XX and YY
components. Export tests compare the parsed program on all eight three-qubit
basis states with nonadjacent ordered targets [2,0].

### Finite spin angular momentum

`Jx(j)`, `Jy(j)`, `Jz(j)`, `Jplus(j)`, and `Jminus(j)` construct
(2j+1)-dimensional matrices for integer or half-integer j in [1/2,63/2].
Units use hbar=1. The basis is ordered m=j,j-1,...,-j, so basis(k,2j+1)
has magnetic quantum number m=j-k. Spin zero is excluded because this
interface requires a matrix dimension of at least two.

The definitions follow [QuTiP's jmat implementation](https://qutip.readthedocs.io/en/v5.2.3/_modules/qutip/core/operators.html):
Jz has diagonal m, Jplus maps m to m+1 with coefficient
sqrt(j(j+1)-m(m+1)), Jminus is its adjoint, Jx=(Jplus+Jminus)/2,
and Jy=(Jplus-Jminus)/(2i). End-point ladder actions are zero.
The implementation retains exact square roots and rational entries.

Examples:

```text
Jx(1/2)                         # X/2
norm(Jplus(1)basis(1,3)-sqrt(2)*basis(0,3))
expect(Jx(3/2)^2+Jy(3/2)^2+Jz(3/2)^2,basis(2,4))
evolution(Jz(1),pi)             # spin-one z rotation
```

Tests cover all cyclic commutators, adjoint ladders, their coefficients and
endpoints, and the Casimir identity Jx^2+Jy^2+Jz^2=j(j+1)I across five
spin values. These functions do not parse coupled |j,m> labels, perform
Clebsch-Gordan decomposition, or define abstract angular-momentum algebra.

Spin components also accept J_x(j), J_y(j), J_z(j), J_+(j), and J_-(j),
including braced subscripts and operator hats such as `\hat{J}_{+}(1)`.
Unicode Jₓ, J₊, and J₋ are accepted as function names. The explicit
spin argument remains required: an isolated J symbol does not infer a
representation from a following state. Signed unbraced subscripts are
recognized only for the complete J name, preserving ordinary arithmetic
and rejecting ambiguous signed subscripts on unrelated identifiers.

### Circuit reordering and deletion

Select a numbered circuit step, then use Move earlier or Move later to change
its execution order. The selected gate retains its parameters and targets;
pending field edits remain pending until Update gate. Delete selected removes
that step immediately. Boundary moves and invalid indices do not mutate the
circuit. Save/Open and OpenQASM export retain the revised order. Cancel edit
only cancels pending field edits; it does not undo moves or deletions.

GUI tests move S before H in an H-S-CNOT sequence, verify the changed Bell
state, reverse the move, delete S, and check save/open and exported H-CNOT.
They also cover invalid indices and deletion down to an empty circuit.

### Circuit undo and redo

Undo and Redo keep up to 100 committed circuit changes in the current composer
window, including register changes and file/example replacement. Compound
example loads form one history entry. Snapshots preserve every gate, angle,
ordered target list, and register size. Invalid operations and selection-only
changes leave history untouched; a new circuit mutation clears the redo branch.
Restoring a snapshot clears the selected step and pending field edits. History
is session-local and is not written into circuit files.

GUI checks restore deletions to an empty circuit and back, invalidate redo on
new edits, preserve redo after invalid edits, and undo/redo a teleportation
preset across register sizes. The recovered state is calculated after restore.

### Two-bit feedback and repetition-code correction

The composer now accepts M00-X, M01-X, M10-X, M11-X and corresponding Z
variants. The first two ordered wires are measured in the Z basis; the third
is the correction target. The first measured wire is the most significant
syndrome bit. Each step performs fresh measurements. Its OpenQASM export
uses two fresh classical bits and a conjunction of their comparisons.

The Bit-flip correction preset encodes |i> in data wires 0,1,2, injects X on
wire 1, then stores parities q0 XOR q1 and q1 XOR q2 in ancillas 3 and 4.
Syndromes 10, 11, 01 select X corrections on data wires 0, 1, 2 respectively.
The circuit then decodes onto q0. Partial tracing wires [1,2,3,4] recovers
|i><i|. Repeated syndrome measurements are equivalent here because correction
acts only on data wires and leaves the recorded ancillas unchanged.

This follows the repetition-code construction described in
[IBM Quantum repetition-code tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/repetition-codes).
It corrects one bit flip, not general Pauli errors, multiple flips, or faulty
syndrome-extraction operations. GUI tests cover all three single-error
positions and no error. Backend tests cover all two-bit outcomes with reversed
measurement order for both X and Z feedback. An independent OpenQASM parser
checks the exported comparisons and reconstructs the exported correction
calculation to verify the recovered density matrix.

### Spin-half arrow basis labels

The qubit basis accepts |↑>, |↓>, and ordered strings such as |↑↓↑>.
Pasted TeX accepts \ket{\uparrow\downarrow}, matching bras, compact overlaps,
and outer products. Arrows can mix with binary digits, but not with named
states or other numbers. The existing ten-qubit basis-string limit applies.
Explicit dimension suffixes still require a decimal numeric index.

The convention is ↑=0 and ↓=1, with Jz(1/2) eigenvalues +1/2 and -1/2.
This matches the Z-basis convention described by
[QuTiP state manipulation documentation](https://qutip.org/docs/4.7/guide/guide-states.html).
These labels denote spin-half tensor factors, not arbitrary higher-spin
magnetic states or Fock occupation labels. Tests cover all three-qubit strings,
orthogonality, ladder actions, overlaps, outer products, and TeX spellings.

### Compact product-state labels

Product kets and bras accept strings formed from 0,1,+,- and spin arrows.
For example, |+-> means |+> tensor |->, and |0+> means |0> tensor |+>.
The first label is the leftmost tensor factor, with a ten-qubit limit.
Unicode minus and mathematical TeX ket/bra commands use the same grammar.
Compact overlaps and matrix elements support these labels as well.

The special labels |i>, |+i>, and |-i> remain single-qubit Y eigenstates.
They cannot be concatenated with other letters into a product label; use
explicit tensor products for such states. Named state labels and explicit
qudit dimensions retain their existing meanings.

Validation compares all eight three-qubit X-basis product states against
H tensor H tensor H acting on computational basis states, checks all 64
pairwise overlaps, mixed-basis ordering, outer products and matrix elements.
The Algorithms library demonstrates XOR phase kickback starting with |++->.

### Matrix-element operator scope

A complete bra/operator/ket expression now treats the operator between its
bars as one expression. For example, <+-|X tensor X|+-> evaluates to -1
(write tensor as @ or the Unicode symbol), and <0|X+Z|0> evaluates to 1.
Additional parentheses around that operator are optional. This resolves the
previous precedence gap for tensor products and sums in matrix elements.

The scanner respects nested parentheses, matrices, function arguments and
quoted operator labels. It does not cross a surrounding argument delimiter
or another top-level bra. Explicitly separated bra products and ordinary
outer products retain their existing grammar. The operator is evaluated by
the same parser with the same depth and node limits. Operator double-bra and
double-ket matrix elements follow the same grouping rule.

Checks cover tensor and sum operators, scalar coefficients inside and outside
the matrix element, nested density calls, matrix literals, consecutive matrix
elements, TeX braket notation, double-kets, and malformed dimensions/delimiters.
Tensor products now restore flat bra vectors to one-row matrices before
forming the Kronecker product, matching the existing bra treatment in vec
and permute. Checks cover bra-bra, mixed ket-bra, and three-factor products.
The same row restoration also applies to dagger and transpose: a bra dagger
returns its column ket, and applying dagger twice preserves a complex ket.

### Von Neumann entropy

#### Entanglement negativity and logarithmic negativity

`negativity(state,subsystems[,dimensions])` implements
N = (||rho^(T_A)||_1 - 1)/2, equivalently the absolute sum of negative
eigenvalues of the normalized state's partial transpose.
`lognegativity` has the same arguments and returns log2(1+2N).
These conventions follow [Vidal and Werner, A computable measure of
entanglement](https://arxiv.org/abs/quant-ph/0102117) and
[QuTiP's negativity implementation](https://qutip.org/docs/4.4/modules/qutip/entropy.html).

Inputs are finite numerical column kets or physical density matrices of total
dimension 2–64. Validation shares entropy's Hermiticity, positivity, and
uncertainty tolerances. Kets become normalized density matrices; mixed states
are symmetrized and normalized by trace before partial transpose. Subsystems
are a zero-based index or list, leftmost first, with the same validation as
`ptranspose`. Dimensions default to qubits; explicit mixed-radix dimensions
must multiply to the state dimension. Transposing all subsystems yields zero.

The numerical Hermitian eigensolver uses double precision and the same real
embedding as entropy. Each eigenvalue occurs twice, so the negative sum is
halved. Negativity below 1e-13 is rounded to zero; results carry 12-digit
approximate status. A zero value is not a general separability certificate:
PPT entangled states exist in higher dimensions. There is no symbolic
entanglement classification or arbitrary-precision spectral solver here.

Validation covers Bell and GHZ states, unequal Schmidt coefficients, complex
phases, local unitaries, product and classically correlated states, noisy
Werner states above and at the PPT threshold, unnormalized large kets,
mixed dimensions, and invalid inputs. `windows/test-negativity.py` separately
constructs dense complex pure states in Fourier local bases, checking both
subsystems and both measures against their known Schmidt coefficients for
2x2, 2x3, 3x3, 4x4, 4x8, and 8x8 bipartitions.

#### Entropy conventions

`entropy(state)` computes -sum(p log2(p)), with zero eigenvalues contributing
zero. Its bit convention follows [Qiskit quantum_info entropy](https://quantum.cloud.ibm.com/docs/en/api/qiskit/quantum_info).
[QuTiP entropy documentation](https://qutip.readthedocs.io/en/qutip-5.0.x/apidoc/functions.html)
also supports this convention but defaults to natural logarithms; this API
accepts an optional base as entropy(state,base). The base must be finite, real and greater than one; e selects nats and 10 selects decimal units.

A finite nonzero column ket (dimension 2-1024) has zero entropy. Square density
matrices of dimension 2-64 are normalized by their positive trace, consistent
with this extension's normalized state statistics. The numerical matrix path
uses a real symmetric embedding of the Hermitian matrix and cyclic Jacobi
rotations. The embedding duplicates each eigenvalue, so its entropy sum is
halved. No external eigensolver/runtime is required.

Matrix results are approximate, displayed with 12 significant digits using
ordinary double precision even if the calculator precision is higher. This is
not an arbitrary-precision spectral method or a rigorous error bound. Entries
must be finite and representable as doubles. Broad uncertainty intervals are
rejected. Hermiticity is checked at 1e-12 relative to the largest entry;
normalized eigenvalues below -1e-12 or above 1+1e-12 are rejected. Values just
outside [0,1] within that tolerance are clamped. A magnitude below 1e-13 in the
final entropy is rounded to zero. The rotation tolerance is 1e-14 with at most
100 sweeps. Ill-conditioned cases near these tolerances require care.

Validation includes pure states, Bell marginal entropy, maximally mixed states
through dimension 64, nontrivial two-level mixtures with complex coherence,
and a Fourier-conjugated four-level state with entropy 1.75 bits. Invalid
shapes, zero/negative weight, non-Hermitian and indefinite matrices are rejected.

### Unicode integer superscripts

Quantum notation translates consecutive superscript digits, optionally preceded
by a superscript plus or minus, into a grouped caret exponent before parsing
gate names. Examples include X², H⁻¹, X¹² and (X+Z)². This fixes the previous
behavior where libqalculate could receive X² as an unknown symbol rather than
the known Pauli gate with a power. Existing precedence is retained: iY² means
i times Y squared, while (iY)² squares the complete product.

Quoted strings are not rewritten. Superscript signs without digits and signs
inside a digit sequence are rejected. Superscript letters and fractional
superscripts are not supported by this translation; use caret expressions.
The test suite covers gates, inverses, grouped operators, functions, scalars,
matrix elements, adjacent multiplication, and malformed superscript runs.
Quantum-mode matrix powers now return a matching identity matrix at exponent
zero (for example CNOT^0 is identity(4)); nonsquare zero powers are rejected.

### Windows circuit-save reliability

Windows .NET Runtime event logs identified intermittent GUI smoke terminations
inside File.Replace in SaveCircuit. Save now retries only Windows sharing and
lock violations (codes 32 and 33) and error 1175 (unable to remove the replaced
file), up to five retries separated by 200 ms.
Atomic replacement is retained; the destination is never truncated as a fallback.
Other errors propagate immediately to the existing save-error UI.

Deterministic tests hold a destination open without delete sharing, confirm a
persistent lock fails while preserving its bytes, release a temporary lock on
a background thread and verify save/open recovery, and check temporary-file
cleanup. The smoke harness also records unexpected exception details and exits
with failure instead of terminating without a diagnostic result file.


### Trace distance

`tracedistance(a,b)` (alias `tracedist`) implements one half of the trace norm
of the difference of normalized density operators. This convention matches
[QuTiP trace distance](https://qutip.readthedocs.io/en/v5.1.0/_modules/qutip/core/metrics.html).
Inputs may be kets or density matrices, must have matching dimension 2-64, and
are normalized independently by norm or trace. Nonphysical matrices are rejected
using the same numerical validation and tolerance as entropy.

The shared Hermitian eigensolver diagonalizes the difference in a real symmetric
embedding. Every eigenvalue appears twice, so the sum of absolute embedding
eigenvalues is divided by four. Results are approximate with 12 significant
digits, use double precision, and are not rigorous error bounds. Distances
below 1e-13 are rounded to zero, and tiny overshoots above one are clamped.

Tests include identical/orthogonal pure states, complex qubits, mixed states,
normalization invariance, common tensor factors and dephasing. Independent
known-spectrum tests conjugate two probability distributions by the same dense
complex unitary in dimensions through 16; the expected distance is their
classical total variation distance. Entropy tests are retained after sharing
the eigensolver. Larger literal tests invoke registered core functions directly
to avoid the quantum notation parser's separate node limit.

### Squared state fidelity

`fidelity(a,b)` implements F=(tr sqrt(sqrt(rho) sigma sqrt(rho)))^2, using the
squared convention of [Qiskit state_fidelity](https://quantum.cloud.ibm.com/docs/en/api/qiskit/quantum_info).
Some texts and libraries instead call sqrt(F) fidelity. The GUI example and
function documentation explicitly state which convention is used here.

`root_fidelity(a,b)` (alias `rootfidelity`) returns the nonnegative square root
of that result, matching the unsquared convention in
[IBM's fidelity lesson](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/fidelity).
It retains the same input normalization, physical-state validation, dimensions,
and approximate numerical accuracy. `root_fidelity(|0>,|+>)` is 1/sqrt(2),
whereas `fidelity(|0>,|+>)` is 1/2. Bare F is not an implicit function alias.
The existing squared-fidelity cutoff also applies: squared results below
1e-13 are rounded to zero before taking the root. This implementation should
not be used to resolve root fidelities near or below roughly 3.2e-7.

The public IBM course outline is recorded in `ibm-learning-sections.json`:
137 section links across 15 courses, plus 12 standalone module links, observed
on 2026-10-14. This is a discovery inventory, not a compatibility certificate.
`windows/test-ibm-measurement-lessons.py` checks 122 concrete instances of
Helstrom discrimination, Pauli/tetrahedral tomography, purification by partial
trace, and both fidelity conventions against independent NumPy calculations.
It also checks six invalid root-fidelity calls. Symbolic ensembles, arbitrary
indexed proofs, automatic optimal measurements and full lesson programs remain
outside that test coverage.

Inputs are kets or density matrices with matching dimension 2-64, normalized
independently and validated with the same tolerances as entropy/trace distance.
If either argument is a ket, the calculation uses tr(rho sigma). Otherwise,
the shared real symmetric eigensolver accumulates eigenvectors, constructs the
positive matrix square root, and diagonalizes its sandwich with the second
state. Duplicate eigenvalues from the real embedding are accounted for.

All results are approximate double-precision values displayed with 12
significant digits. These digits are not a guaranteed accuracy. In particular,
square roots near zero amplify roundoff: rank-deficient matrices may have errors
around 1e-7. Negative eigenvalues within 1e-12 are clipped to zero, results below
1e-13 are rounded to zero, and overshoots of one within 1e-6 are clamped; larger
violations fail. Use a higher-precision external spectral solver when such
near-boundary accuracy is required.

Tests include pure-state overlaps, scaled states, mixed/pure interchange,
noncommuting mixed qubits with analytic fidelity 7/8, rank-deficient entangled
states, and dephasing. Independent dense complex tests through dimension 16
compare commuting states against (sum sqrt(p_i q_i))^2, while retaining the
entropy and trace-distance tests after adding eigenvector accumulation.

The diagnostic harness captured Windows save error 1175 explicitly. Its retry
is based on Microsoft's documented guarantee that both files retain their names:
[ReplaceFile documentation](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/winbase/nf-winbase-replacefilew.md).
Errors 1176/1177 have different file-state consequences and are not retried.

### Measurement probability charts

The Windows calculator renders a horizontal probability chart for quantum-mode
expressions beginning with probs(...), when the result is a finite real column
vector of 2-64 entries in [0,1] summing to one within 1e-9. The original result
and its exact/approximate label are retained. A numerical copy supplies chart
coordinates without converting the original calculation to approximate mode.
Broad uncertainty intervals are rejected for plotting.

Outcome indices default to decimal positions in the returned vector. For a
power-of-two outcome count, the Outcome labels selector also offers padded
binary indices (for example, 001). These are index representations, without
assuming every power-of-two system is made of qubits. Marginal probability
ordering follows the supplied subsystem list. Switching labels does not
recalculate, alter the original result, or add a history entry. The preference
lasts while the app is open and is not saved in calculator sessions. Other
outcome counts use decimal labels and preserve the preference for later charts. Bars use a fixed
zero-to-one scale, percentages round to two decimal places, and tooltips expose
more numeric digits. Long charts scroll; nonprobability and failed results hide
the chart. The worker emits the optional probabilities JSON array only when
requested via --probabilities and the result passes validation.

GUI tests also check binary padding through 64 outcomes, accessible labels,
qudit fallback, retained preferences, and switching back to decimal.
GUI tests check Bell-pair bars, percentage labels, switching back to an operator
result, and hiding charts after errors. Worker tests cover exact rational
probabilities, invalid distributions and the chart-size limit. A rendered
Bell-pair chart was inspected for layout and scaling.

## Single-qubit noise constructors

`amplitude_damping(p)`, `phase_damping(p)` and `depolarizing(lambda)` return
vectors of 2-by-2 Kraus matrices. They compose with `channel`, `choi` and
`superop`; use `channel(density(state),amplitude_damping(p),wire)` for local
noise. These are ensemble channels, not sampled error trajectories.

Amplitude damping uses K0=diag(1,sqrt(1-p)) and
K1=sqrt(p)|0><1|. It models relaxation to the ground state. Phase damping
uses the same K0 and K1=sqrt(p)|1><1|, preserving populations while
attenuating coherence by sqrt(1-p). Both require 0<=p<=1. The latter p is
not a phase-flip probability. These conventions follow the equations in
[Qiskit Aer amplitude damping](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.amplitude_damping_error.html)
at zero excited-state equilibrium population and
[phase damping](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.phase_damping_error.html).

Depolarization follows
[Qiskit Aer](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.depolarizing_error.html):
E(rho)=(1-lambda)rho+lambda Tr(rho)I/2. Its Kraus weights are
sqrt(1-3lambda/4)I and sqrt(lambda/4) times each of X,Y,Z. The full
completely-positive range 0<=lambda<=4/3 is supported, including complete
mixing at 1 and a uniform nonidentity Pauli error at 4/3.

Parameters must evaluate to finite real numbers; broad uncertain intervals,
unresolved symbols and out-of-domain values are rejected. Exact radicals and
rational arithmetic are retained in the returned matrices. Each constructor
always returns its two or four operators, including zero operators at endpoints.
Correlated multi-qubit noise constructors and automatic insertion of noise
after every gate remain future work. Individual noise operations can be added
explicitly in the composer, as described below.

Regression coverage checks analytic population/coherence evolution, both
endpoints, a locally damped entangled state, local complete depolarization,
trace preservation through the Choi partial trace, superoperator action,
invalid domains and arity. Three executable GUI examples expose the operations.

## Generalized and combined damping

`amplitude_damping(a,p)` adds equilibrium excited-state population p; its
four Kraus matrices include upward as well as downward relaxation.
`phase_amplitude_damping(a,b,p=0)` additionally damps phase, returning six
operators. Parameters lie in [0,1] with a+b<=1. In both cases the excited
population transforms as rho11'=(1-a)rho11+a*p*Tr(rho). Combined damping
multiplies off-diagonal entries by sqrt(1-a-b). For nonzero a, the stationary
normalized state is diag(1-p,p); when a=0, populations stay unchanged.

The formulas follow [Qiskit Aer combined damping](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.phase_amplitude_damping_error.html).
The supplied p is a probability, not a temperature. Four or six Kraus operators
are retained even when some vanish. Tests check equilibrium, analytic complex
coherence, extreme populations, complete relaxation, Choi trace preservation,
local action on entanglement, and equivalence to amplitude damping followed
by phase damping with rescaled parameter b/(1-a), for a<1.

## Noise in the circuit editor

The gate selector includes AD, GAD, PD, PAD, and Depol. All take one wire;
the parameter hint describes their physical meanings. AD/PD take p, GAD takes
p and equilibrium excited population, PAD takes amplitude/phase/population,
and Depol takes lambda. Parameters may be calculator expressions. Arity and
parentheses are checked when adding, editing, or opening a circuit; numerical
domain validation happens when the expression is evaluated by libqalculate.

Noise operations use amber boxes and retain parameters below the wire. At the
first noise step, a pure circuit state is converted to a density matrix. Later
gates, channels, resets and measurements retain the appropriate representation.
Save/open, step movement, editing and undo/redo preserve noise operations.
OpenQASM export explicitly refuses these circuits before offering a save path;
the exporter currently has no representation for these channels and must not
silently omit them. Save as .qcircuit to retain the complete circuit.

GUI tests evaluate all five channels against analytic complex density matrices,
continue through later gates and channels, apply noise after reset/measurement/
feedback, verify order and parameter edits, and check round trips, malformed-file
preservation, undo/redo, and export refusal. A Bell circuit with local damping
and dephasing is rendered for visual inspection.

## Pauli transfer matrices

`ptm(Kraus_list)` (alias `PTM`) accepts matching square Kraus matrices for
one to four qubits. For a unitary U, pass `vector(U)`. With dimension d=2^n,
the entries are R_ij=Tr(P_i E(P_j))/d, using the lexicographic basis
I,X,Y,Z or II,IX,IY,IZ,XI,... . This follows the
[Qiskit PTM definition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.PTM).
Rows index output Pauli coordinates and columns input coordinates. The
leftmost letter acts on the leftmost tensor factor. For a normalized qubit,
R acts on [1,x,y,z]. Trace preservation would give first row [1,0,...];
unitality would additionally give first column [1,0,...].

Implementation reuses the column-vector superoperator and performs a sparse
Pauli basis change, retaining exact arithmetic. It does not normalize or
certify completeness of arbitrary Kraus lists. Rectangular operators,
non-qubit dimensions, inconsistent shapes and oversized matrices are rejected.
The existing 256-operator limit applies.

Exact tests cover I/H/S, nonunital and generalized damping, phase damping,
depolarization, composition, tensor order, CNOT signs, three-qubit signs,
four-qubit identity and scaled non-trace-preserving maps. The independent
`windows/test-ptm.py` computes all entries of dense complex one- and two-qubit
examples by direct matrix multiplication and the defining trace formula.
GUI checks verify the 4-by-4 display and Bloch-coordinate action.

## Normalized Pauli coordinates

`paulivec(A)` maps a square qubit operator to coefficients
v_j=Tr(P_j A)/sqrt(d), and `unpaulivec(v)` reconstructs
A=sum_j v_j P_j/sqrt(d). This is the normalized Pauli vectorization convention
in the [Qiskit PTM reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.PTM).
One to four qubits are supported; inverse input lengths are 4,16,64,256.
Both operations retain exact arithmetic and accept non-Hermitian complex
operators. They neither enforce positivity nor normalize trace.

The normalization preserves the Hilbert-Schmidt inner product and norm.
For a qubit state the coordinates are [1,x,y,z]/sqrt(2), with the same
lexicographic order as PTM. Thus a channel can be applied as
`unpaulivec(ptm(Ks)paulivec(rho))`. Ordinary `vec` and double-ket operator
notation continue to mean column stacking.

Tests cover Y signs, a non-Hermitian complex matrix, multi-qubit ordering,
both round-trip directions, Bell correlations, norm preservation, zero
operators, invalid dimensions and arity, and reconstruction after unitary
and nonunitary channels. The shared sparse basis implementation is also
checked by the independent PTM trace-formula test.

## Whitespace in pasted notation

Quantum-prefix detection is shared by the parser and all unit-conversion
checks. Leading ASCII or Unicode whitespace, and an initial UTF-8 BOM, are
accepted before `quantum:`. This prevents a leading-space `quantum:norm(|->)`
from being treated as an ordinary conversion-arrow expression.

Within quantum expressions, characters with the Unicode White_Space property
are normalized to ASCII spaces outside quoted strings. The list is checked
against the [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/ucd/PropList.txt):
U+0009–000D,0020,0085,00A0,1680,2000–200A,2028,2029,202F,205F,3000.
Zero-width formatting characters are not treated as spaces. A BOM at the
beginning of the quantum expression is also accepted. Quoted text is retained.

Tests cover each whitespace character before the explicit prefix and between
operators, BOMs, CRLF multiline input, quoted Pauli-word rejection, GUI paste
paths, and unchanged ordinary `to` and `->` unit conversions.

## T1/T2 thermal relaxation

`thermal_relaxation(T1,T2,time,p=0)` returns a single-qubit Kraus list.
The constants must be positive (positive infinity is permitted), elapsed time
finite and nonnegative, p in [0,1], and T2<=2*T1. Numeric time values must
use consistent units. These parameters and the physical constraint follow
[Qiskit Aer thermal relaxation](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.thermal_relaxation_error.html).

The implementation derives combined damping parameters
a=1-exp(-time/T1), b=exp(-time/T1)-exp(-2*time/T2). Consequently excited
population evolves to p+(rho11-p)exp(-time/T1) for normalized states, while
off-diagonal coherence is multiplied by exp(-time/T2). The T2 constraint
ensures b>=0. Infinite time constants mean no decay in that component; time
zero is the identity. Exact expressions are retained where possible.

Tests cover the amplitude-only boundary, pure dephasing, infinite constants,
zero time, equilibrium, composition over successive time intervals, trace
preservation, exact range rejection and numerical population/coherence decay.
The composer offers Thermal with four parameters and inherits noise editing,
save/open, and explicit OpenQASM-export refusal. Its GUI test compares the
output against an independently specified complex density matrix.

## Bloch coordinates and sphere view

`bloch(state)` returns a column [x;y;z], the normalized X/Y/Z expectations
of a two-component ket or 2-by-2 density matrix. This follows the
[IBM quantum-state plotting convention](https://quantum.cloud.ibm.com/docs/en/guides/plot-quantum-states).
Kets are converted to density matrices and the trace is normalized. Larger
registers accept the optional wire argument described below. Coordinates retain exact
arithmetic where possible. Physical-state validation reuses the numerical
entropy checks: finite entries within double range, narrow uncertainty,
positive trace, and positivity within 1e-12. Exact non-Hermitian matrices
are rejected; approximate inputs use their validated Hermitian part.

Quantum-mode expressions starting with `bloch(...)` request a numeric coordinate
array from the worker and show an orthographic sphere projection. Rotation and
reset-view controls change only the camera azimuth. Exact coordinates remain
above the plot. Approximate length and purity=(1+length^2)/2 appear beside it;
a zero vector is drawn at the center. Accessibility text includes all three
coordinates. Invalid, nonnumeric, and subsequent non-Bloch results hide the view.

Tests cover six Pauli eigenstates, global phase and input scaling, mixed states,
rotations, partial traces, complex coherences, malformed/unphysical states,
and approximate thermal noise. GUI tests exercise the view, rotation/reset,
the center point and hiding behavior. Both initial and interactive layouts were
rendered and inspected.

## Selected-qubit inspection

`bloch(state,wire)` traces out every qubit except the selected zero-based wire,
where wire 0 is leftmost. Pure kets support 1–10 qubits; density matrices have
the existing 262144-entry cap (up to 9 qubits). Pure-state reduction accumulates
the four reduced entries directly, without allocating the full density matrix.
The reduced state is normalized and validated by `bloch`; this operation does
not certify positivity of an arbitrary full-register density matrix. It is
equivalent to forming the reduced state explicitly and inspecting that state.

The circuit editor's Inspect control selects State, Probabilities, Schmidt coefficients, or Bloch
qubit. The latter enables a wire field and validates its range before loading
the expression. Inspection does not change the saved circuit or its operations.
Tests cover wire ordering, Bell and complex product states, input scaling,
noise, dimension limits, invalid indices, and direct editor-to-view workflows.

## Quoted control patterns

Quoted control patterns are also accepted: `controlled(X,2,"01")` applies X
when the leading controls are 01. Exactly n binary digits are required for n
controls, including leading zeroes; spaces and other characters are rejected.
The control count may be an integer-valued expression. This mirrors the
bitstring validation described by [Qiskit ControlledGate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.3/qiskit.circuit.ControlledGate).
Our existing tensor convention still places the first supplied control at the
leftmost, most significant position. Tests enumerate every two-control pattern
on all computational basis states and cover reordered wires and width errors.

## Chi process matrices

`chi(Ks)` (aliases `Chi`, `χ`, and TeX `\chi`) converts matching square Kraus
operators for one to four qubits into a process matrix in the normalized Pauli
basis. With d=2^n and Pauli order I,X,Y,Z (lexicographic tensor products for
multiple qubits), the convention is E(rho)=sum(chi_ij P_i rho P_j)/d.
Consequently chi=sum_k paulivec(K_k) paulivec(K_k)†. This matches the
[Qiskit Chi definition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Chi).
Some literature omits the 1/d factor and therefore reports coefficients divided
by d relative to these results. Trace-preserving maps have trace chi=d;
`chi(vector(I))` is diag(2,0,0,0). No normalization or trace-preservation
certification is performed on the supplied list.

The implementation changes the column-stacked Choi matrix to the normalized
Pauli basis. Unlike PTM, multiplying chi matrices does not compose channels.
Tests cover complex S-gate phases, amplitude damping, complete depolarization,
tensor ordering, Kraus mixing, scaling, aliases and dimensions. The independent
`windows/test-chi.py` constructs coefficients using direct Pauli traces and
checks every entry for dense complex one- and two-qubit Kraus lists.

## Equatorial rotations

`R(theta,phi)` denotes exp(-i theta (cos(phi)X+sin(phi)Y)/2), using the
[Qiskit RGate convention](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.2/qiskit.circuit.library.RGate).
Both angles are in radians. The diagonal entries are cos(theta/2); the upper
and lower off-diagonal entries are -i exp(-i phi)sin(theta/2) and
-i exp(i phi)sin(theta/2). Thus R(theta,0)=Rx(theta), R(theta,pi/2)=Ry(theta),
and R(2pi,phi)=-I. The two-argument spelling avoids guessing the meaning of an
ambiguous one-argument R. Symbolic angles follow the existing rotation rules.

The editor accepts R with two parameters, supports editing and .qcircuit
save/open, and exports the chronological sequence Rz(-phi), Rx(theta),
Rz(phi). Tests compare this exact decomposition on every three-qubit basis
state, including untouched wires; global phase is retained. Core tests also
cover the exponential definition, adjoints, controlled use and density maps.

## Left and right multiplication superoperators

`spre(A)` represents X -> AX and `spost(B)` represents X -> XB. In the
column-stacking basis they are I tensor A and transpose(B) tensor I.
`sprepost(A,B)` directly represents X -> AXB as transpose(B) tensor A.
The second operator is transposed, not conjugated; use `sprepost(U,U†)`
for a unitary channel. This follows the [QuTiP superoperator definitions](https://qutip.readthedocs.io/en/latest/apidoc/quantumobject.html).

Each input matrix is limited to 16 rows and columns. spre/spost require
square matrices; sprepost also accepts rectangular matrices, with X shaped
as columns(A) by rows(B), and output shaped as rows(A) by columns(B).
These are general linear maps, without positivity or trace-preservation
assumptions. `spre(H)-spost(H)` gives the commutator superoperator; multiplying
by -i gives the Hamiltonian part of a master-equation generator (hbar=1).
Tests cover complex transpose signs, rectangular maps, non-qubit dimensions,
dimension boundaries, invalid inputs, and agreement with Kraus conversion.

## Lindblad master-equation generators

`lindblad_dissipator(C)` returns D[C](rho)=C rho C†−(C†C rho+rho C†C)/2
as a column-stacked superoperator. `liouvillian(H,vector(C0,C1,...))`
returns L(rho)=−i[H,rho]+sum D[Ck](rho), with hbar=1. Omitting the list
gives Hamiltonian evolution only. These conventions follow the single-operator
dissipator and Hamiltonian construction in [QuTiP's implementation](https://qutip.readthedocs.io/en/v5.2.2/_modules/qutip/core/superoperator.html).

H must be Hermitian and all operators square with matching dimension 2–16;
the collapse list may contain at most 256 matrices. A rate gamma belongs in
the collapse operator as sqrt(gamma)C. For zero Hamiltonian use `0I` (or a
zero matrix of the required dimension), not the scalar 0. The returned matrix
is a generator, not a channel: time-independent evolution is
`unvec(expm(t*liouvillian(H,Ks))vec(rho),d)` for a d-dimensional system.
The existing exponential limits still apply: general numerical exponentials
support matrices up to 64×64, so general propagation supports d≤8 even though
generator construction supports d≤16. No time-dependent differential-equation
solver is supplied. Tests cover trace preservation, exact derivatives,
complex collapse phases, rate scaling, multiple collapse terms, dimensions,
Hermiticity rejection and numerical relaxation/coherent evolution.

## Saved calculation sessions

The Windows calculator saves version 1 `.qsession` JSON files containing the
current draft expression, notation/evaluation modes, and up to 50 recent
calculations with their expression, modes and result text. Result previews
are capped at 32768 characters; current full results are unaffected. Opening
does not evaluate file contents. Restored results are explicitly marked Saved;
double-click recalls the expression and modes, then Calculate recomputes it.
Current output and visualizations are cleared on restore to avoid presenting
an old result as the restored draft's result. Circuit editor files are separate.

Files are limited to 8 MB. The entire document is deserialized and validated
before changing the workspace. Saves use a unique temporary sibling followed
by atomic replacement, with bounded retries for transient sharing failures.
Session controls are disabled during calculation. GUI smoke tests cover exact
round trips, each entry's modes, malformed/oversized input, locked destination
preservation, temporary-file cleanup, oversized drafts and recomputation.


### Parity-selective two-qubit rotations

`XXPlusYY(theta,beta)` rotates the odd-parity pair |01>, |10>;
`XXMinusYY(theta,beta)` rotates the even-parity pair |00>, |11>.
The calculator accepts omitted beta as zero. The composer takes two explicit
comma-separated angles, in radians. Complex or symbolic parameters are formal
matrix expressions; unitarity requires real angles.

With the first operand the leftmost, most-significant qubit, define
`c=cos(theta/2)`, `s=-i*sin(theta/2)`. The nontrivial block of XXPlusYY,
in the order (01,10), is `[c,s*exp(i*beta);s*exp(-i*beta),c]`.
For XXMinusYY, in the order (00,11), it is
`[c,s*exp(-i*beta);s*exp(i*beta),c]`. The other two states are unchanged.
These signs preserve physical operand order when converting IBM's little-endian
matrix convention. At beta=0, XXPlusYY(theta) equals fSim(theta/2,0).
The inverse negates theta and preserves beta. No ambiguous `XY` alias is added.

Sources: [IBM XXPlusYYGate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.3/qiskit.circuit.library.XXPlusYYGate)
and [IBM XXMinusYYGate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.3/qiskit.circuit.library.XXMinusYYGate).
The composer exports standard-gate decompositions using half-angle XX and YY
rotations and conjugating Rz gates, including all relative and global phases.
Tests cover basis-state phases, inverse and zero-angle identities, omitted beta,
parameter validation, circuit save/open/edit, and independent complex simulation
of the actual OpenQASM exports on nonadjacent ordered wires with a spectator.


### Schmidt coefficients across a bipartition

`schmidt_coeffs(psi,subsystems)` returns a column of the normalized pure state's
Schmidt coefficients, sorted largest first, including zeros. The selected
subsystems form one side and their complement forms the other. Indices are
zero-based with the leftmost subsystem first; their list order does not affect
singular values. A third argument supplies mixed-radix dimensions, for example
`schmidt_coeffs(|0>_2@|0>_3+|1>_2@|2>_3,0,[2,3])`.
The number of returned entries is the smaller side's Hilbert-space dimension.
Selecting every subsystem gives a single coefficient 1; Qalculate! may simplify
the resulting 1x1 column to a scalar.

For a normalized bipartite ket, the decomposition has the form
`psi = sum_j s_j a_j @ b_j`, with orthonormal local vectors, nonnegative `s_j`,
and `sum_j s_j^2 = 1`. The squared coefficients are the nonzero spectra of the
reduced density matrices. This function returns the coefficients, not the local
basis vectors. It does not define a multipartite Schmidt decomposition or accept
mixed density matrices. Source: [IBM quantum_info, Schmidt decomposition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/quantum_info).

Implementation reshapes the amplitudes and performs a cyclic one-sided complex
Jacobi singular-value iteration. [LAPACK's Jacobi SVD documentation](https://www.netlib.org/lapack/explore-html/d9/deb/group__gesvj.html)
provides numerical-method background; this is a separate small-matrix
implementation, not LAPACK or a claim to its accuracy guarantees. Working on
amplitudes avoids squaring the condition number in a reduced-density matrix.
The nonzero input is scaled and normalized before iteration, and at most 1024
amplitudes are accepted. Both qubit and explicit mixed-radix partitions use the
same numerical path. Results are approximate, printed to 12 digits; this is not
a guarantee of relative accuracy for tiny values. Coefficients below 1e-14
are reported as zero. Do not use that cutoff as an exact Schmidt-rank proof.
Finite numeric input is required; symbolic values and broad intervals are
rejected. Absolute errors also depend on input conditioning and conversion to
double precision. Iteration is bounded and reports failure if it does not converge.

Independent tests construct pure states from prescribed singular values with
complex Fourier bases, test unequal dimensions and nonadjacent partitions,
rank-deficient states, coefficients of size 1e-12, input scales 1e±200, and a
1024-amplitude maximally entangled state. GUI coverage checks approximate
coefficient rendering; regression cases check normalization, product/Bell/GHZ
states, explicit qudits, and invalid input.


#### Circuit workspace Schmidt inspection

The Inspect selector now includes Schmidt coefficients. Side A accepts a
comma-separated set of zero-based wire indices such as `0,2`; all other wires
form side B. The GUI requires two nonempty sides and rejects duplicates,
malformed or out-of-range indices. It sorts the indices before generating
`schmidt_coeffs(circuit_state,[...])`. This view is available for circuits that
produce state vectors. Measurement, reset, classical feedback, and noise create
density-matrix expressions and are rejected with an explanation, even if a
particular parameter choice could leave a physically pure state. Use the other
inspection views for these circuits. Inspection settings do not change or
persist in the circuit file. The calculator still accepts trivial bipartitions
when entered directly.

GUI smoke tests evaluate Bell and nonadjacent GHZ partitions and reject invalid
partitions and each family of density-matrix-producing operation. Responsive
layout checks cover State and Schmidt views at three window sizes, both three-
and eight-wire diagrams, and expanded/collapsed details.


### Operator and Schatten norms

`schatten(A,p)` and `norm(A,p)` use the singular values of A, returning
`(sum_j s_j^p)^(1/p)` for finite real p >= 1. At positive infinity the result
is the largest singular value. Named forms are `tracenorm(A)` (p=1),
`frobeniusnorm(A)` (p=2), and `spectralnorm(A)` (p=infinity).
These are approximate numeric functions for matrices with at most 1024 entries;
rectangular matrices, row vectors, kets, and scalars are accepted. Scalars use
absolute value. No physical-state assumptions or normalization are imposed.
Plain `norm(ket)` retains the previous exact Euclidean ket operation.

Indexed delimiters include `‖A‖₁`, `‖A‖₂`, `‖A‖_1`, `‖A‖_{infinity}`,
`\lVert A\rVert_1`, `\left\|A\right\|_{\infty}`, and `\norm{A}_F`.
The index F denotes the Frobenius norm. This follows the Schatten convention:
the subscript 2 means Frobenius, **not** the induced matrix 2-norm. Use
`spectralnorm(A)` for the latter. Bare matrix norm bars remain invalid because
they do not specify a convention. The diamond norm of a channel is different
and is not implemented by these functions.

Source: [Watrous, Notes on super-operator norms induced by Schatten norms](https://arxiv.org/abs/quant-ph/0411077).
For example, diag(3,4) has trace norm 7, Frobenius norm 5, spectral norm 4,
and Schatten-3 norm 91^(1/3). A nonnormal matrix such as `[0,2;0,0]` has trace
and spectral norms 2 even though both eigenvalues are zero.

Implementation obtains normalized singular values using the Schmidt amplitude
SVD and rescales by the Frobenius norm computed with Number arithmetic. This
avoids double-precision overflow when squaring large matrix entries. The p=2,
scalar, and zero cases do not require SVD. Finite entries must fit double
precision without broad uncertainty. SVD cutoff and conditioning limitations
from Schmidt coefficients apply to relative singular values. Output is marked
approximate at 12 digits; that is not a relative-error guarantee for every
ill-conditioned matrix. Powers are computed after scaling by the largest
singular value, so large finite orders do not overflow the power sum.

Tests cover complex rectangular matrices with prescribed singular values,
rank deficiency, noninteger and large p, row bras, zero/scalar matrices,
input scales 1e±200, nonnormal matrices, 1024 entries, TeX/Unicode indexed bars,
and unchanged plain ket norms.


#### Double-bar matrices and formatted norm indices

The amsmath `Vmatrix` environment is accepted with an explicit norm order:
`\begin{Vmatrix}3&0\\0&4\end{Vmatrix}_1` returns the trace norm 7.
Without an index it remains an error rather than choosing a matrix-norm
convention. Single-bar `vmatrix` retains its determinant interpretation.
The [LaTeX amsmath source](https://raw.githubusercontent.com/latex3/latex2e/develop/required/amsmath/amsmath.dtx)
defines these environments using the corresponding single/double delimiters.

Whitespace and existing math-font wrappers are accepted around the Frobenius
index, including `_{ F }`, `_{\mathrm{F}}`, and `_\mathrm{F}`. Superscripts can
precede or follow the norm index: `\lVert A\rVert^2_1` squares the trace norm,
just like `\lVert A\rVert_1^2`. Large delimiter commands `\bigg`, `\Bigg`,
`\biggl`, `\biggr`, `\Biggl`, and `\Biggr` affect only presentation and are
ignored like the existing sizing commands. Empty orders or powers are errors.
Tests compare matrix environments, explicit delimiters, the norm macro and
Unicode bars, formatted indices, and both script orders. Exact ket norms and
determinants retain their existing behavior.

TeX control-word scanning uses explicit ASCII letters, avoiding locale-dependent
classification of UTF-8 bytes. In particular, a Unicode subscript directly after
a closing TeX delimiter is not consumed into the command name.

### Phase-estimation preset and marginal inspection

The circuit editor's Examples menu includes **Phase estimation · T gate**.
It prepares q3 in |1>, uses q0,q1,q2 as a three-bit counting register, applies
controlled P(theta) powers 4, 2, and 1, then the inverse three-qubit QFT.
The preset theta=pi/4 is the T-gate eigenphase 1/8 of a turn. Counting bits
q0q1q2 finish as 001; the target remains |1>. There are 14 editable standard
gates. To change the phase coherently, change the first three CP angles to
4*theta, 2*theta, and theta; leave the inverse-QFT gates unchanged.
This is a phase-gate eigenstate example, not an arbitrary eigenvalue solver.
It does not run hardware or simulate shot noise.

The preset selects **Marginal probabilities** with measured wires `0,1,2`.
Loading that view evaluates `probs(circuit,[0,1,2])`, so chart outcome 1 means
binary 001 and phase estimate 1/8, without counting the target qubit. General
marginal inspection accepts a nonempty list of distinct valid wire indices,
preserves the entered order, and supports both pure and noisy circuits.
For example, `2,1,0` reverses the outcome-bit order. Unlike a Schmidt partition,
the marginal list may include every wire. Inspection settings are not saved
in the .qcircuit file and do not change its gates.

Source: [IBM, The phase-estimation procedure](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure).
For a counting outcome k, the analytic amplitude is
`(1/8) sum_(x=0)^7 exp(i*x*(theta-2*pi*k/8))`.
GUI tests evaluate all eight exact phases k*pi/4, verify full states and
marginal bit order, and check save/open and undo/redo. Independent simulation
of the actual OpenQASM exports covers those eight phases and theta=pi/8.
The latter produces a distribution checked against the complex Fourier sum.
Responsive layout checks include the marginal-inspection controls.

### Reflections and selective phases for arbitrary states

`reflection(psi)` constructs the Householder sign flip `I - 2P`, where
`P = |psi><psi| / <psi|psi>`. The supplied nonzero column ket need not be
normalized. It accepts 2 to 512 finite numeric amplitudes, including qudits.
The selected state gets eigenvalue -1; every orthogonal state is unchanged.
Some literature uses the opposite sign for a state reflection. Here,
`reflection(|++>) = -diffusion(2)`, and `reflection(|1>) = Z`.
The sign is preserved when constructing a controlled operation.

`phase_reflection(psi,theta)` constructs `I + (exp(i*theta)-1)P` for a finite
real angle in radians. It multiplies the selected state by exp(i*theta) and
leaves its orthogonal complement unchanged. At theta=pi it equals reflection;
at zero it is identity. Negating theta gives the inverse. The implementation
uses equivalent sine/cosine expressions to retain exact familiar angles.
Symbolic amplitudes, zero states, mixed density matrices, non-real angles,
and broad uncertainty intervals are rejected. Validation and normalization use libqalculate Number arithmetic without
conversion to double precision; algebraic calculations retain exact values
where supported. Input scaling and global phase do not change P. Regression
cases include scaling by 1e1000 and 1e-1000.

One Grover iteration is now expressible as
`-reflection(|++>)reflection(|11>)|++>`, which yields |11> exactly.
The leading minus implements the positive-uniform-state diffusion convention.
For general amplitude amplification, phase choices must satisfy the relevant
algorithm's conditions; arbitrary phase choices do not guarantee amplification.
Sources: [Brassard et al., Quantum Amplitude Amplification and Estimation](https://arxiv.org/abs/quant-ph/0005055)
and [Hoyer, On Arbitrary Phases in Quantum Amplitude Amplification](https://arxiv.org/abs/quant-ph/0006031).

Regression tests check involution, Hermiticity, unitarity, eigenvectors,
orthogonal complements, phase composition, controlled signs, qudits, extreme
input scaling, Grover amplification, and invalid inputs. Independent tests
compare complete complex matrices with directly computed normalized projectors.

### Editable Grover circuit presets

Examples > Grover search offers targets 00, 01, 10, and 11. Each preset prepares
|++>, marks the chosen basis state with an X-conjugated CZ oracle, and applies
H on both wires, X on both wires, CZ, X on both wires, then H on both wires.
The last block is I-2|++><++|, the negative of the conventional diffusion
operator. One iteration therefore returns exactly -|target>, with probability
one for the marked outcome. The global phase is retained in the calculator and
OpenQASM export. Wires q0,q1 are the leftmost-first bit order in the calculator.
The consuming OpenQASM tool may display bitstrings in a different order.

These are explicit, editable two-qubit examples with a known marked target,
not a search service over unknown data. They use 12-16 gates, select the full
probability view, support undo/redo and .qcircuit save/open, and export using
standard H, X, and CZ gates. Tests check all four exact state vectors and use
an independent complex-state simulation of all four exported programs.

Source: [IBM, Grover's algorithm](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/grovers),
including the phase-marking oracle and diffusion construction.

### Tensor-power typography and bras

TeX operator superscripts accept surrounding whitespace, including
`H ^ { \otimes 2 }`, `X^{ \dagger }`, `Y^{ \ast }`, and `Y^{ \top }`.
Numeric powers retain their existing semantics. Tensor powers accept bras as
well as kets and operators: `<i|^{\otimes 2}|11>` is exactly -1/2, preserving
complex conjugation and left-to-right tensor order. Exponents remain integers
from 0 through 10, subject to the tensor matrix-size limit; exponent zero
returns the one-dimensional identity. Symbolic unevaluated tensor powers and
infinite tensor products are not implemented.

Regression cases cover spaced superscripts, complex bra contraction, zero and
threefold powers, the function form `tensorpow(<1|,2)`, and ordinary numeric
powers. The tensor-power convention also appears in
[IBM's data-encoding course](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/data-encoding).

### Finite indexed tensor products

`tensorproduct(expression,first,last,index)` and
`\bigotimes_{k=0}^{2}{Ry(k*pi)}` evaluate factors in increasing index order,
placing the first factor on the left. TeX bounds can appear in either order;
`\limits` is accepted and the operand must be braced. Bounds are inclusive
integers within -1000000 through 1000000, with 1-32 factors and the existing
1024-row/column, 262144-entry matrix allocation limit. Reversed/empty bounds,
infinite limits, and numeric or known-constant indices are rejected.
Use an unknown symbolic index such as k or j. Factors may be operators, kets,
or bras. Scalar factors are rejected by the matrix tensor operation.

Index substitution respects nested tensorproduct, sum, and product bindings.
A nested repeated index is local to its body; bounds can depend on an outer
index. Numeric and symbolic gate parameters use the existing evaluator; this
is a finite construction, not a formal infinite tensor algebra.

`(\bigotimes_{k=0}^{2}{Ry(k*pi)})|000>` returns -|010>, including the global
phase from Ry(2*pi). Regression cases check mixed-dimensional basis factors,
complex bras, negative lower bounds, single-factor products, nested scopes,
invalid bounds, and exact gate action.

Source: [IBM, Data encoding](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/data-encoding),
which uses indexed tensor products for parallel phase-gate layers.

### Indexed block-diagonal operators

`blocksum(expression,first,last,index)` and
`\bigoplus_{k=0}^{1}{X^k}` construct a block-diagonal linear map, with blocks
ordered by increasing index. The example is exactly CNOT: identity occupies
the control-zero block and X the control-one block. Similarly,
`blocksum(P(k*pi/2),0,1,k)` is controlled(S).

Scalar blocks are one-dimensional maps. Rectangular matrices are allowed;
rows and columns are summed independently. A column or row matrix is treated
as a rectangular linear map, not as a request to concatenate state vectors.
The result does not retain Hilbert-space metadata. Blocks are not required
to be unitary; a controlled-gate interpretation requires equal-sized unitary
blocks and an appropriate control-register dimension.

The bounds, 32-term cap, symbolic-index rules, and nested-index scoping are the
same as tensorproduct. The result remains subject to 1024 rows, 1024 columns,
and 262144 entries. The empty range is rejected; a single block returns that
block. Tests cover CNOT and controlled-S, varying block sizes, scalar blocks,
full rectangular complex matrices, nested operations, and invalid bounds.

Source: [IBM, Uniformly controlled gates](https://quantum.cloud.ibm.com/docs/en/api/qiskit/1.2/qiskit.circuit.library.UCGate),
which represents multiplexed gates as block-diagonal unitary matrices.

### Unicode large operators

Pasted ∑ (U+2211), ∏ (U+220F), ⨂ (U+2A02), and ⨁ (U+2A01) use the
same finite indexed syntax as \sum, \prod, \bigotimes, and \bigoplus.
For example, `∑_{k=0}^{3}{k^2}` is 14 and `⨁_{k=0}^{1}{X^k}` is CNOT.
Bounds may appear in either order, and an optional \limits is accepted.
Explicit lower/upper bounds and a braced operand remain required. A copied
two-dimensional layout with no delimiters is not reconstructed automatically.
Large ⨂ and ⨁ are distinct from binary ⊗ and ⊕. Quoted labels are preserved.

Tests compare 48 Unicode and TeX calculations across bound orders and wrappers,
plus 16 malformed bounds/operand forms and a nested sum/product example.
Sources: [Unicode mathematics report](https://www.unicode.org/reports/tr25/tr25-16.html)
and [Supplemental Mathematical Operators](https://www.unicode.org/Public//UCD/latest/charts/nameslist/2a00/).

### Evaluated computational-basis labels

With an explicit dimension, the contents of a ket or bra may be an
index expression: `|k+1>_4`, `|mod(5,3)>_3`, and `<k|_4`. Compact inner products
such as `<1+1|mod(5,3)>_3` use the same dimension for both indices. Evaluation
must ultimately produce an integer in [0,d-1]. Unresolved indices, matrices,
complex values, and out-of-range indices are rejected. Parser nesting and
complexity limits apply to label expressions too.

This permits textbook sums directly:
`\sum_{k=0}^{3}{\ket{k}_4}/2` prepares the uniform state;
`\sum_{k=0}^{2}{|k>_3<k|_3}` resolves the qutrit identity;
`\sum_{k=0}^{3}{exp(2*pi*i*k/4)|k>_4}/2` equals QFT(2)|01>.
Explicit dimensions are required for computed indices; the parser does not
infer a Hilbert space from an unqualified label. `|001>` remains an eight-entry
binary ket, while `|001>_3` selects decimal index 1 in a three-entry ket.

Tests verify these identities exactly, computed bras, modular expressions,
indexed tensor products, compact overlaps, invalid indices, and binary labels.
The use of computed basis indices in order finding is illustrated in
[IBM's Shor tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/shors-algorithm).

### Evaluated basis dimensions and subscript scope

Grouped dimension suffixes evaluate expressions: `|7>_{2^3}` and `|7>_(2^3)`
both equal |111>. Their exponent belongs to the dimension, not to the ket.
This also works in bras, compact overlaps, outer products, and matrix elements.
Equivalent dimensions such as 2^3 and 4+4 are compared through the evaluated
matrix dimensions, so `<7|_{2^3}7>_{4+4}` is one. Unequal dimensions are rejected.
An index-dependent dimension is supported within finite indexed operations,
for example `\bigotimes_{k=2}^{4}{|k-1>_{k}}` gives a 2×3×4-dimensional ket.

The dimension must ultimately be an integer from 2 through 1024. Unknown,
complex, fractional, and oversized dimensions fail validation. Unbraced
literal suffixes still work; compound expressions require explicit grouping.
Binary labels without dimension suffixes retain their previous interpretation.
Tests cover scope, equivalent and unequal dimensions, sums over register
sizes, mixed-dimensional products, and basis resolutions of identity.
The n-qubit dimension 2^n is reviewed in
[AWS's quantum measurement guide](https://aws.amazon.com/blogs/quantum-computing/exploring-quantum-measurements-observables-and-operators-practical-insights-with-amazon-braket/).

### Infix modular arithmetic

Quantum-mode expressions accept `a mod b`, `a \bmod b`, `a \mod b`, and
`a % b` as spellings of the existing `mod(a,b)` function. A plain-text mod
requires preceding whitespace, preserving implicit multiplication in
`2mod(17,5)`. `\mathrm{mod}` works with its generated spacing. The operator
has multiplication/division precedence and associates left to right:
`2+7 mod 3` is 3, `(2+7) mod 3` is 0, and `17 mod 5 * 2` is 4.
For positive integer moduli, negative dividends give the usual nonnegative
residue (for example, -17 mod 5 is 3).

This applies within computed basis labels: `|2*k\bmod 15>_16` is an evaluated
ket. Summing `|2*k\bmod 15>_16<k|_16` for k=0..14 and adding `|15>_16<15|_16`
reconstructs modmul(2,15), including its identity action on unused register
states. `\sum_{k=0}^{3}{|2^k\bmod 15>_16}/2` is the normalized order-four orbit.
Tests check that full permutation matrix, ket/bra labels, arithmetic scope,
negative dividends, and preservation of function-call multiplication.

The backend's mod semantics are retained, including unevaluated results where
it cannot determine a residue; such a result is not a valid basis index.
Congruence relations and \pmod annotations are not parsed as arithmetic.
In quantum mode % means modulo; outside quantum mode existing percentage
syntax is unchanged. The partial-transpose superscript parser is unchanged.
Source: [IBM's Shor tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/shors-algorithm),
which uses modular products in computational-basis labels.

### Repeated-bit register labels

Unqualified `|0^n>` and `|1^n>` denote n repeated zero or one bits, respectively:
`|0^3>` equals |000>, and `|1^3>` equals |111>. TeX `\ket{0^{3}}`, Unicode
`|1³⟩`, standalone bras, compact overlaps, and matrix elements are accepted.
The count can be bound by a finite indexed operation. Group compound counts,
for example `|0^(n+1)>`; `|0^n+1>` is rejected as ambiguous.

Counts must evaluate to integers from zero through ten. Zero copies give the
one-dimensional tensor identity, printed as 1. Unknown, fractional, complex,
negative, or oversized counts are rejected. An explicit dimension changes the
label interpretation back to an arithmetic basis index: `|1^3>_8` is basis(1,8),
not |111>. Literal bitstrings and existing named-state labels are unchanged.

Tests cover both bits, TeX and Unicode, bras and overlaps, varying counts in
sums/tensor products, zero and ten copies, dimension-qualified arithmetic,
and invalid counts. The all-zero register notation appears in
[IBM's Shor tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/shors-algorithm)
in its phase-estimation input state.

### Named Bell states

Signed Bell labels inside bras and kets expand to exact normalized vectors:
Phi+/Φ+/φ+ = (|00>+|11>)/sqrt(2), Phi− = (|00>−|11>)/sqrt(2),
Psi+/Ψ+/ψ+ = (|01>+|10>)/sqrt(2), and Psi− = (|01>−|10>)/sqrt(2).
The last sign is a relative phase; the singlet Ψ− changes sign under SWAP.
ASCII names Phi/phi and Psi/psi and Greek Φ/φ/ϕ and Ψ/ψ are supported.
Signs may be inline, superscripted, or subscripted. Examples include `|Φ+>`,
`|Ψ⁻⟩`, `|Phi^->`, `\ket{\Phi^{+}}`, and `\ket{\Psi_{-}}`.
Compact overlaps such as `<Φ⁺|Φ⁻>` also work.

These signed labels are reserved for the Bell convention only inside Dirac
brackets. Bare unsigned Greek symbols retain their existing meaning. Explicit
dimension suffixes instead request arithmetic basis indices and do not apply
to Bell names. An ambiguous ± label must be replaced by one chosen sign.
Tests cover all supported name/sign spellings, the full orthonormality table,
local Pauli actions, the singlet's SWAP phase, reduced states, and resolution
of the four-dimensional identity.

Source: [IBM, Quantum information for multiple systems](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/quantum-information).

### Editable Bell-state preparation circuits

The circuit editor's Examples > Bell states submenu prepares Φ+, Φ−, Ψ+, or Ψ−.
All start with H on q0 followed by CNOT(0,1). Ψ states then use X on q1; minus
states use Z on q0. Applying these in that order preserves the exact Bell
phase convention, including the positive |01> amplitude of Ψ−. Selecting a
preset switches to the State inspection view, where relative phases are visible.
Probability distributions alone cannot distinguish the plus/minus variants.
The editor still starts with Φ+ by default.

GUI tests cover exact comparison to each named ket, undo/redo, save/open, and
invalid preset indices leaving the circuit intact. An independent complex-state
simulator checks every exported OpenQASM circuit. Layout tests cover three
window sizes, expanded details, zoom, fit, and scrolling; a singlet preparation
was rendered and visually reviewed.

### Adjacent Dirac registers

Consecutive ket factors such as `|0>|1>` or `\ket{0}\ket{1}` form a tensor
product in written order. This grouping binds before surrounding multiplication:
`CNOT|+>|0>` produces Φ+, and `CNOT|1>|0>` produces |11>. It works with named
Bell states, complex one-qubit states, and explicit qudit dimensions.
Consecutive bras can be grouped as `(<0|<1|)` and contracted against a register.
Multi-register matrix elements accept bare adjacent output and input factors,
for example `<0|<1| CNOT |0>|1>`, as well as explicitly grouped registers.

A bra followed by a ket still contracts; a ket followed by a bra still forms
an outer product. Thus `|0>|1><0|<1|` is the projector onto |01>. Ordinary
matrix expressions retain multiplication, and explicit `*` between two kets
still requests matrix multiplication and reports incompatible dimensions.
Use ⊗ for arbitrary parenthesized, function-valued, or powered state expressions
where a direct Dirac-factor run is not present. No subsystem metadata is inferred.

Tests cover gate action and grouping, complex amplitudes, mixed dimensions,
TeX kets, grouped bras, full outer-product matrices, postfix adjoints, preserved
operator multiplication, and dimension errors.
Source: [Microsoft, Dirac notation](https://learn.microsoft.com/en-ca/azure/quantum/concepts-dirac-notation).


### Matrix elements with adjacent input registers

A matrix element now combines all adjacent input kets before applying its
operator: `<00|CNOT|+>|0>` evaluates to `1/sqrt(2)`, as does the amplitude
onto `<11|`. This also supports three or more factors and mixed-dimensional
registers. The operator between the bars retains its full expression scope,
so `<00|CNOT+identity(4)|+>|0>` is `sqrt(2)`. A postfix power after the completed
matrix element applies to the resulting scalar; use explicit parentheses
when applying an operation to an individual register. Multiple bare output bras also group into one output register, as in
`<0|<1| CNOT |0>|1>`. Parentheses remain available for explicit grouping.

Exact regression checks compare Bell amplitudes, imaginary amplitudes, mixed
dimensions, TeX input, sums of operators, and scalar powers. This follows the
same tensor-product convention in the Microsoft Dirac-notation source above.


### Adjacent output bras and compact register inner products

Bare adjacent bras form a tensor-product output register before an operator
or input register is contracted. `<1|<1|CNOT|+>|0>` is `1/sqrt(2)`.
The shared-bar form `<i|<-|i>|->` and the fully separated form
`<i|<-| |i>|->` both give `1`, with complex conjugation on the complete
output register. Mixed dimensions are explicit per factor, for example
`<2|_3<1|identity(6)|2>_3|1>` gives `1`.

A postfix operation on an individual following bra keeps that factor separate:
`<i|<i|†` remains the single-qubit inner product `1`. To adjoint an entire
output register, group it: `(<0|<1|)†` gives `|01>`.
An already complete single-bra compact inner product stays complete;
`<0|0>|1>` is the scalar `1` multiplying `|1>`.

The independent test `windows/test-output-registers.py` checks 864 complex
contractions for CNOT, CZ, and SWAP, using computational and non-real output
bras. This implements the tensor-product bra convention and conjugation
specified by [Microsoft's Dirac-notation reference](https://learn.microsoft.com/en-us/azure/quantum/concepts-dirac-notation).


### Comma-separated register labels

`|0,1>` means `|0> ⊗ |1>`; commas mark register boundaries without changing
factor order. Each field can be a binary string, a supported named state,
or a repeated-bit register: `|00,1>`, `|+,i>`, `|Phi+,1>`, and `|0^2,1>`.
Bras and compact matrix elements use the same convention:
`<i,-|i,-> = 1` and `<1,1|CNOT|+,0> = 1/sqrt(2)`.
The TeX forms `\ket{0,1}` and `\braket{i,-|i,-}` are supported.

This is a tensor-product label, not a vector of amplitudes. Empty fields and
nonbinary decimal fields without dimensions are errors. A single dimension
suffix on a comma-separated label is rejected because it does not specify
each register's dimension; write `|2>_3|1>` for mixed-dimensional registers.
Commas nested inside a computed basis index remain function arguments,
so `|mod(5,3)>_3` still means the qutrit basis state with index 2.

The comma convention is explicitly described in Washington University's
[Principles of Quantum Communications](https://www.cse.wustl.edu/~jain/cse570-19/ftp/quantum/index.html)
(search-index text accessed 2026-10-13; direct retrieval returned HTTP 502).
Tests include exact states, conjugation, outer products, TeX, invalid labels,
and independent complex contractions via `test-output-registers.py --commas`.


### Bernstein–Vazirani circuit presets

The circuit GUI now builds all eight three-bit Bernstein–Vazirani instances.
Starting from |0000>, it applies X to q3, H to all four wires, CNOT(qj,q3)
for each set bit sj, and H to q0–q2. In the leftmost-first convention the
exact output is |s>⊗|−>; no global or relative phase is discarded. The
selected marginal view lists q0,q1,q2 and gives probability 1 at s.

The preset explicitly constructs the chosen oracle f(x)=s·x mod 2. The one-query
claim concerns access to this oracle, not the number of gates in its shown
implementation. These are educational instances with a known selected string.
The circuit has 8+popcount(s) gates and supports editing, save/open, undo/redo,
and OpenQASM 3 export. Tests cover every string, invalid-input preservation,
and independent simulation of all exported amplitudes and marginals.

Source: [IBM Quantum Learning, the Deutsch–Jozsa algorithm and Bernstein–Vazirani problem](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm).


### Binary inner products for oracle formulas

`bitdot(x,y)` (alias `binarydot`) computes the parity of pairwise bit products:
`(x0*y0 + ... + xn*yn) mod 2`. Inputs may be quoted binary strings or numeric
row/column vectors, with 1–1024 entries and equal lengths. Scalar 0 or 1 is
a one-bit input. Quoted strings preserve leading zeros, so `"001"` has length
3 and cannot silently match `"1"`. Entries must evaluate to exactly 0 or 1;
nonbinary, symbolic, complex, empty, and multi-row/multi-column matrix inputs
are rejected. Row and column orientations both follow entry order.

Examples: `bitdot("101","110") = 1`, `bitdot("111","110") = 0`, and
`(-1)^bitdot("101","100") = -1`. This operation supplies the binary phase
exponents and parity oracles used by Bernstein–Vazirani and Walsh–Hadamard
identities. The ordinary centered dot retains multiplication semantics;
there is no implicit conversion from ordinary arithmetic to arithmetic mod 2.

The independent test checks all 256 pairs of four-bit strings and additional
vector, symbolic-sum, phase, and validation cases. Source: [IBM Quantum Learning,
binary dot product in the Bernstein–Vazirani analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm).


### Width-preserving binary exclusive-OR

`bitxor(x,y)` (alias `binaryxor`) performs entrywise XOR on equally long binary
strings or vectors, using the same validation as `bitdot`. It returns a flat
bit vector in input order: `bitxor("101","110") = [0,1,1]`. Leading zeros
remain entries, and a one-bit result displays as a scalar. Row and column
inputs may be mixed; the result uses one canonical flat-vector representation.
The output can be fed directly to either binary operation.

`bitxor(bitxor(s,t),t)` restores s, and `bitdot(bitxor(s,t),x)` equals
`xor(bitdot(s,x),bitdot(t,x))`. The existing `xor` function still operates on
integers, for example `xor(5,6)=3`. Outside basis labels, the ⊕ symbol retains its direct-sum meaning
in quantum matrix expressions; use the explicit binary function for bit strings.

Tests independently compare all 256 four-bit XOR pairs, 64 binary-dot linearity
identities, nested composition, invalid arguments, and the 1/1024-bit boundaries.
Source: [IBM Quantum Learning, binary XOR and dot-product identities](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm).


### Fixed-width binary registers and integer values

`bits(value,width)` converts a nonnegative integer into a flat bit vector with
exactly `width` entries, most significant bit first. Width must be an integer
from 1 to 1024 and the value must be less than 2^width; excess bits are rejected,
never truncated. Example: `bits(5,4) = [0,1,0,1]`.
`bitvalue(bits)` decodes a quoted bit string or a row/column bit vector as a
nonnegative integer in that same order: `bitvalue("00101") = 5`.
As with the other binary functions, a one-bit vector displays as a scalar.

Both conversions use exact arbitrary-precision integers. The integer result
has no width metadata; supply a width when converting back to preserve any
leading zeros. `bitvalue(bitxor(bits(5,4),bits(6,4))) = 3` and
`|bitvalue("101")>_8 = |101>` show composition with binary arithmetic and
basis-state labels.

For a three-qubit Walsh–Hadamard transform, every matrix coefficient satisfies
`<y|H⊗H⊗H|x> = (-1)^bitdot(bits(x,3),bits(y,3))/sqrt(8)` when the bra and ket
labels denote three-bit basis indices (or use explicit dimension 8).
Tests compare all 64 coefficients, 316 conversion cases with Python integers,
round trips up to the largest 1024-bit value, and invalid/overflow inputs.
Source: [IBM Quantum Learning, the binary-dot-product formula for Hadamard gates](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm).


### Expression-defined reversible oracles

`oracle_function(expression,n,m,x)` evaluates the expression at every integer
input x from 0 through 2^n−1 and builds the reversible query matrix
`|x,y> → |x,y XOR f(x)>`. The input register is first and most significant;
the output register has m bits. Each result must be an integer in 0…2^m−1.
Widths are positive integers with n+m≤9; the largest matrix is 512×512.
The index must be an unknown symbolic variable, not a known constant.

`oracle_function(x,1,1,x)` is CNOT. For the Bernstein–Vazirani instance s=101,
use `oracle_function(bitdot("101",bits(x,3)),3,1,x)`. It composes with gates,
superpositions, and marginal probabilities just like a truth-table oracle.
`oracle_function(mod(x*x+1,4),2,2,x)` demonstrates a two-bit output register.
The expression is evaluated with the bound input substituted before numeric
validation. Nested indexed operations respect their own bound variables.

This constructs an explicit dense matrix by enumerating the function's values;
it is not a compiler from arbitrary functions to scalable hardware circuits.
The existing table-based `oracle` remains available. Tests compare every basis
mapping for polynomial and parity functions, exact coherent phase kickback,
involution, nested index scope, the maximum matrix dimension, and invalid
function values or dimensions.
Source: [IBM Quantum Learning, unitary query gates](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/query-model-of-computation).


### Expression-defined phase oracles

`phase_function(expression,n,x)` builds the diagonal matrix with entry
`(-1)^f(x)` at each n-bit basis index x. The expression must evaluate to
exactly 0 or 1 for every input. Width is 1–9 qubits and the bound index must
be an unknown symbolic variable. The expression uses the calculator's existing
arithmetic/function grammar, rather than a separate Boolean-expression language.

`phase_function(floor(x/3),2,x)` is CZ: only index 3 is marked.
`probs(diffusion(2)phase_function(floor(x/3),2,x)|++>)` therefore finds |11>
with ideal probability 1. `phase_function(bitdot("101",bits(x,3)),3,x)`
implements the Bernstein–Vazirani phase oracle without an ancilla.
Constant-zero and constant-one functions produce I and −I respectively;
the latter's global phase is retained.

As with `oracle_function`, this constructs an explicit dense matrix, not a
hardware gate synthesis. It shares capture-avoiding index substitution with
finite sums/products and reversible oracle expressions. Tests check all columns
of parity phase oracles on 1–4 qubits, coherent algorithm outputs, nested scope,
the maximum matrix size, and invalid expressions.
Source: [IBM PhaseOracleGate, phase-oracle definition](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.PhaseOracleGate).


### Comparison predicates in quantum expressions

Quantum expressions accept `=`, `==`, `!=`, `<`, `>`, `<=`, and `>=`, plus
Unicode ≤, ≥, ≠ and TeX \le/\leq, \ge/\geq, \ne/\neq. Arithmetic binds
before comparisons. A chain such as `1<=x<3` means both `1<=x` and `x<3`,
not a comparison against the Boolean result of the first relation. Numeric
true/false results are 1/0; `=` compares and does not assign a variable.

`phase_function(x=3,2,x)` is CZ. `phase_function(1<=x<3,2,x)` marks indices
1 and 2, and `oracle_function(x>1,2,1,x)` builds the truth table [0,0,1,1].
These predicates also work inside finite indexed expressions. A formula that
remains undecidable after index substitution is rejected by the oracle builder.

ASCII `<` is recognized as a bra opener when a complete bra delimiter is
present; otherwise it may introduce a comparison after an expression. Group
predicates in parentheses when mixing them with state arithmetic, for example
`(2<3)|0>`. Standard ket endings and adjacent bras retain their Dirac roles.
Tests cover 175 independently computed signed-integer comparisons, chained
ranges, arithmetic precedence, Unicode/TeX spellings, oracle predicates,
finite sums, malformed input, and existing Dirac expressions.

The Boolean-predicate interpretation used by the phase oracle follows the
[IBM PhaseOracleGate definition](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.PhaseOracleGate).


### Boolean combinations of predicates

Quantum expressions accept `and`, `or`, and `not`, Unicode ∧, ∨, ¬, and TeX
\land/\wedge, \lor/\vee, \lnot/\neg. From strongest to weakest,
precedence is arithmetic, comparisons (including chains), NOT, AND, XOR, then OR.
Thus `not x=3` means `not (x=3)`, and `a or b and c` means `a or (b and c)`.
Use parentheses to change grouping or embed a logical predicate in arithmetic.
Numeric zero is false and nonzero values are true; logical results are 0 or 1.
The lowercase operator words are reserved in operand positions.

`phase_function(x=1 or x=3,2,x)` equals I⊗Z and transforms |++> into |+−>.
`phase_function(x>=1 and x<=2,2,x)` marks indices 1 and 2.
`oracle_function(x<2 and not x=0,2,1,x)` has truth table [0,1,0,0].
As before, an oracle expression must become a definite 0/1 result (or an
in-range output integer for a reversible oracle) after substitution.

Tests cover word/Unicode/TeX truth tables, nonbinary numeric truth values,
operator precedence, De Morgan identities, compound oracle construction,
and missing or misplaced operands. This extends the predicate expression
syntax used by the [phase-oracle definition](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.PhaseOracleGate).

Comparison lookahead respects function argument boundaries before a Dirac state: `vector(1<2,|0>)` returns a vector containing the true predicate (1) and the ket; `vector(2<1,|0>)` contains 0 and the ket. Comma-separated bra registers such as `2<0,1|` remain valid. Regression tests cover predicates followed by kets, bras, and further comparison arguments.

### Exclusive OR in oracle predicates

Use `a xor b`, `a ⊻ b`, or `a \veebar b` for logical exclusive OR. Numeric
zero is false, nonzero is true, and the result is 1 precisely when the truth
values differ. Chains compute parity. Comparisons and NOT bind more tightly
than AND, then XOR, then OR. Parentheses override this order.

`phase_function(x>=2 xor x mod 2,2,x)` equals Z⊗Z: indices 1 and 2 acquire
minus signs. `(H@H)phase_function(x>=2 xor x mod 2,2,x)|++>` yields |11>,
recovering the parity mask. The corresponding reversible oracle has truth
table [0,1,1,0].

The functional call `xor(5,6)` retains native integer bitwise XOR (3).
Use explicit multiplication, such as `2*xor(5,6)`, when multiplying that
function's result. `bitxor` still operates on whole bit vectors; outside basis labels, ⊕ still
forms a matrix direct sum, and ^ remains exponentiation.

[IBM PhaseOracleGate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.PhaseOracleGate)
includes logical XOR in its Boolean oracle language. This parser uses its
own spellings to avoid collisions with mathematical powers and Dirac notation.
The AND/XOR/OR ordering agrees with the Boolean operator ordering documented
by [Microsoft](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/boolean-logical-operators).
Tests independently enumerate truth values and three-operand precedence,
and check the phase and reversible oracle matrices and recovered quantum state.

### Comparing predicate results

Parenthesized predicates can be compared as their 0/1 values. For example,
`(0=0)!=(1=0)` is 1, and `(0=0)=(1=0)` is 0. This also applies to ordered
comparisons, deeper nesting, and chains such as `0<=(2>1)<2`.

`phase_function((x=1)!=(x=2),2,x)` equals Z⊗Z, while the equality version
used in a reversible oracle has truth table [1,0,0,1]. Each operand is
explicitly evaluated before the enclosing comparison is constructed;
parentheses therefore preserve the intended Boolean subexpression.
Tests independently enumerate all seven comparison spellings applied to
nested predicates, alongside mixed inner operators and quantum oracles.

### Simon circuit examples

The Windows circuit composer offers **Examples → Simon’s algorithm** for
all eight three-bit strings. Each circuit has six wires: input q0q1q2 and
output q3q4q5. Hadamards surround one reversible oracle query on the input
register, while the output register begins in |000>.

For nonzero s, let p be its first 1 bit (left to right). The implemented
oracle is f(x)=x XOR (x_p s). This linear function has kernel {000,s}, so
f(x)=f(y) precisely when x=y or x XOR y=s. Three CNOTs copy x into the
output register, then pivot-controlled CNOTs XOR s when x_p=1. For s=000,
f(x)=x is one-to-one. The visible gates are an educational oracle instance;
the preset does not discover an arbitrary black-box function.

The default view shows the marginal probabilities on q0q1q2. Nonzero s
has four equiprobable outcomes y satisfying bitdot(y,s)=0; s=000 has all
eight outcomes with probability 1/8. A single outcome does not recover s.
Repeated measurements and binary linear algebra supply the remaining
classical part of Simon’s algorithm. The display shows the exact ideal
distribution, not random shots or an automatic recovery routine.

This implements the circuit and measurement analysis in
[IBM’s Simon lesson](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm).
The app uses input-register-first ordering explicitly. Save/open, undo/redo,
and OpenQASM export preserve all eight circuits. Independent tests verify
every reversible basis mapping, the oracle promise, all final Fourier
amplitudes and marginals, and the candidate masks implied by full support.

### Exact binary linear algebra

`gf2_rref(A)` returns reduced row-echelon form over GF(2), `gf2_rank(A)`
returns its rank, and `gf2_nullspace(A)` returns a matrix whose columns form
a basis of the right kernel (A s = 0 modulo 2). Basis columns follow the
free-variable order from left to right. All binary linear combinations of
these columns are solutions, including zero. These operations use XOR row
addition, not real or complex arithmetic.

Inputs must be nonempty matrices of 0/1 entries with at most 128 rows and
128 columns. A flat vector is a single equation (one row); scalar 0 or 1
is a 1×1 matrix. Nonbinary entries are rejected rather than reduced modulo
2 implicitly. RREF retains zero rows. A full-column-rank matrix has no
basis vectors, so `gf2_nullspace` returns the empty vector `[]` to represent
the zero-dimensional kernel; Qalculate cannot represent a zero-column
matrix. A zero matrix has the identity as its nullspace basis.

For Simon measurements 010 and 101,
`gf2_nullspace([0,1,0;1,0,1])` returns [1;0;1]. Their rank is 2 and the
possible masks are 000 and 101; the nonzero promise selects 101. With
fewer independent equations the nullspace has multiple basis columns and
more measurements are needed. Ordinary matrix multiplication is unchanged:
when checking A times a binary basis, its entries must be interpreted
modulo 2.

[IBM’s algorithmic foundations](https://learning.quantum.ibm.com/course/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations)
describes Simon post-processing as a binary nullspace calculation via Gaussian
elimination. Tests independently enumerate row spaces and kernels for 100
small matrices, recover all seven nonzero three-bit masks, and check input
validation and the dimension boundary.

### Binary matrix inverses

`gf2_inverse(A)` inverts a square 0/1 matrix over GF(2), with the same
128×128 input limit as the other binary matrix operations. Singular matrices
are rejected, including matrices that are invertible over the reals but
singular modulo 2. Scalar 1 represents the invertible 1×1 matrix; scalar 0
is singular. Nonbinary, empty, and nonsquare inputs are rejected.

For example, `gf2_inverse([1,1,0;0,1,1;0,0,1])` gives
[1,1,1;0,1,1;0,0,1]. This is a binary inverse, not an ordinary inverse:
products are interpreted with each entry reduced modulo 2. For a reversible
linear bit map y=A x, it recovers x from y. It does not by itself synthesize
a quantum gate circuit or change the meaning of matrix powers or †.

The implementation row-reduces [A|I] and extracts the right block when the
left block has full rank, as illustrated in the
[SageMath GF(2) matrix reference](https://doc.sagemath.org/html/en/reference/matrices/sage/matrix/matrix_mod2_dense.html).
Independent tests exhaust all 512 binary 3×3 matrices, verify both products
for all 168 invertible cases, reject the 344 singular cases, and check
recovery of all 1,344 input bitstrings for the invertible maps.

### Binary-map composition and quantum permutation gates

`gf2_mul(A,B)` multiplies compatible 0/1 matrices over GF(2), with XOR as
addition. Each operand may have up to 128 rows and columns. Flat vectors
are rows; use a column matrix such as [1;0;1] for a bit-column input. Inner
dimensions must match. This does not alter ordinary matrix multiplication.

`linear_gate(A)` constructs the exact 2^n×2^n permutation matrix U_A with
U_A|x>=|A x mod 2>. A must be an invertible binary n×n matrix, 1≤n≤9.
Rows describe output bits and columns input bits, both left to right in the
app's register convention (q0 is the most significant bit). This lifts a
classical bit map to a unitary acting linearly on quantum superpositions.
Singular maps cannot define such a gate and are rejected.

Examples: `linear_gate([1,0;1,1])` is CNOT and
`linear_gate([0,1;1,0])` is SWAP. The composition identity is
`linear_gate(gf2_mul(A,B)) = linear_gate(A)*linear_gate(B)`; B acts first.
The inverse is `linear_gate(gf2_inverse(A)) = linear_gate(A)†`.
The function produces a dense operator for calculator expressions; it does
not synthesize a CNOT/SWAP gate list in the circuit editor.

[IBM LinearFunction](https://quantum.cloud.ibm.com/docs/api/qiskit/qiskit.circuit.library.LinearFunction)
describes reversible linear circuits through invertible binary matrices.
This implementation documents its own wire ordering explicitly. Tests cover
all 512 three-bit maps (168 permutations, 344 singular rejections), independent
rectangular products, composition and inverse identities, entanglement, and
both function dimension limits.

### Editable circuits from binary maps

In the circuit composer choose **Build → From binary matrix…**. Enter a
square 0/1 matrix using comma- or space-separated entries and semicolon- or
newline-separated rows; surrounding square brackets are optional. It supports
1–8 input/output bits, with rows as output bits, columns as input bits, and q0
first. An invertible map replaces the current circuit with editable CNOT and
SWAP steps. Validation and synthesis finish before any circuit state changes;
invalid input preserves the circuit. Undo restores the previous circuit.

The compiler row-reduces the binary matrix to identity, records CNOT row
additions and SWAP row exchanges, then reverses those self-inverse operations.
It is a correct decomposition, not a gate-count optimizer. The composer now
accepts 64 steps, sufficient for this eight-bit elimination construction.
The TeX preprocessing depth limit is 128 to accommodate generated long
expressions. The main parser counts both unary and atom frames, so its limit
is 256 frames; the 512-node complexity and input-size limits still apply.

The generated circuit starts in |0…0>, like all composer circuits. Insert and
move preparation gates before the synthesized map to inspect other states.
Identity maps require zero gates. Save/open and OpenQASM export preserve the
compiled circuits. Tests exhaust all three-bit maps and independently verify
their exported basis permutations; eight-bit examples cover longer circuits,
all 256 input states per map, and long-expression calculation.

### Physics-package Dirac macros

The TeX reader accepts `\expval{A}{state}`, `\ev{A}{state}`, and
`\expectationvalue{A}{state}` as explicit bra/operator/ket expectation values.
`\matrixel{left}{A}{right}`, `\mel`, and `\matrixelement` take three arguments.
The arguments use the same finite state labels as ordinary Dirac input;
for example `\expval{Y}{i}` is 1 and `\matrixel{0}{Y}{1}` is −i.
Observable expressions retain their grouping and bras are conjugated.

`\dyad` and `\op` are aliases for `\ketbra`/`\outerproduct`, with an optional
second label; a single label forms its projector. The whole outer product
is grouped under a following power or dagger. `\ip` aliases the inner
product. A single-label `\braket{a}` or `\innerproduct{a}` means <a|a>;
bar-separated braket expressions remain supported.

A single sizing star is accepted for bra, ket, inner-product and outer-product
macros. Expectation and matrix-element macros accept one or two sizing stars.
These stars affect typesetting in LaTeX and do not change the calculation.
An implicit expectation such as `\expval{A}` is rejected with an explicit-state
message, because no global state is assumed. This remains a structural math
reader, not a TeX macro execution engine.

These conventions were checked against the
[CTAN physics package](https://ctan.org/pkg/physics) and its
[documentation source](https://mirrors.mit.edu/CTAN/macros/latex/contrib/physics/physics.tex).
Tests cover aliases, sizing variants, complex conjugation, multi-qubit labels,
compound observables, power/adjoint scope, and malformed arguments.

### IBM Quantum Learning and qBraid coverage audit

The requested reference corpus now includes all [IBM Quantum Learning](https://quantum.cloud.ibm.com/learning/en), including its course and classroom-module catalogs, and qBraid syntax and learning. `Learning-source-inventory.json` in the portable distribution (source: `docs/learning-source-inventory.json`) records initial discovery, dated 2026-10-14. It is an audit queue, not a compatibility certification: the complete lesson and notebook corpus has not yet been checked.

The existing finite-dimensional calculator covers many mathematical building blocks. Matching an algorithm mathematically does not imply that its Qiskit, qBraid Python, or OpenQASM source program can be pasted and executed. The app currently exports a bounded OpenQASM gate subset; its PyQASM-backed importer handles bounded static OpenQASM circuits, while general runtime classical programs and a Python/SDK runtime remain unimplemented. Its editor remains limited to 8 qubits and 64 steps, so utility-scale examples are outside the simulator's capacity.

The [qBraid algorithm examples](https://docs.qbraid.com/v2/algorithms/user-guide/overview) contain subroutines, loops and classical control as well as gates. Their language compatibility requires a compiler/runtime audit in addition to checking QFT, QPE and Bernstein-Vazirani mathematics. [qBraid learning access](https://docs.qbraid.com/v2/home/learning) is account/organization dependent; the available course contents have not been audited. The public demo repository is listed separately in the inventory.

A concrete mathematical gap is [IBM's stabilizer-code formalism](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes): Pauli matrices and binary linear algebra are available, but symbolic groups generated by Pauli operators and general code objects are not. These remain open requirements, alongside the rest of the lesson-level audit.

### OpenQASM import through qBraid PyQASM

Circuit composer → File → Import OpenQASM accepts `.qasm` files using OpenQASM 2 or 3. The bundled PyQASM 1.0.4 compiler expands static loops, subroutines, custom gates, register operations, and classical constant expressions before the result is validated against the editor's gate set. No Python installation is needed to run the portable app. The build dependency versions are in `windows/qasm-import-requirements.txt`; `windows/build-qasm-import.ps1` freezes the helper and copies dependency licenses.

Supported primitive gates retain their matrix convention and global phase. `GPhase(theta)` multiplies the whole state by `exp(i*theta)`; its displayed wire is arbitrary. Inverse, integral-power, and representable positive/negative-control modifiers are supported. Unsupported controlled gates are rejected. Gate angles compiled by PyQASM are numerical floating-point values, so imported expressions are not an exact symbolic reconstruction of the original angle source.

Registers map to consecutive editor wires in declaration order, with register index zero first. This differs from Qiskit's usual printed bitstring order; compare named wires, not an unexamined string reversal. Measurement steps retain the nonselective quantum state (dephasing); classical outcomes and classical register mappings are not retained. The import status explicitly states this. Use the probability inspector for the resulting quantum-wire distribution. Programs with runtime classical feedback are rejected instead of dropping their conditions.

Imports are limited to 256 KB, 1–8 qubits and 64 compiled steps, with a 30-second compiler timeout and 4096 iterations per compiled loop. Pulse/timing operations, arbitrary include files, unresolved runtime operations and unsupported gates fail before the editor is changed. Import is one undoable operation and can be saved as `.qcircuit`. These bounds do not establish full IBM/qBraid program compatibility.

Primary references: [PyQASM compilation examples](https://docs.qbraid.com/v2/pyqasm/user-guide/examples) and [qBraid algorithm programs](https://docs.qbraid.com/v2/algorithms/user-guide/overview). Independent verification in `windows/test-qasm-import.py` checks full Fourier columns through four qubits, all three-bit Bernstein–Vazirani secrets, U-gate phase conventions, explicit global phase, modifier semantics and measured density matrices.

### Controlled global phase and U conventions

The import adapter corrects a phase-losing lowering in the pinned PyQASM 1.0.4 compiler: `ctrl @ gphase(a)` must be `P(a)`, not merely an equivalent-up-to-phase `Rz(a)`. One- and two-control global phases, negative controls, inverses, integer powers and occurrences inside custom gates preserve the full state amplitudes. Three or more controls on `gphase` are currently rejected. This adapter uses a version-checked visitor override, restored after each compilation; upgrading PyQASM requires revalidating it.

The reference material uses different `U` phase conventions. [IBM's UGate matrix](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.UGate) is `P(phi) Ry(theta) P(lambda)`. The [published OpenQASM 3 gate matrix](https://openqasm.com/versions/3.0/language/gates.html) equals `exp(i*theta/2)` times that matrix. Circuit composer → File → Import OpenQASM now offers both conventions. Choose **IBM / Qiskit U convention** for IBM/Qiskit-generated programs, or **Published OpenQASM 3 U convention** for programs written against that explicit matrix definition. The latter requires an OpenQASM 3 version declaration. This choice concerns uppercase builtin `U`; `u` and `u3` retain the IBM/Qiskit convention in both modes. It is not a claim of complete specification conformance.

One-control `U` and `u3` operations expand into controlled phase and Y rotations. With the published convention, the extra phase is applied to the control branch, including negative controls and inverses; it must not be applied globally. Direct U, coherent inputs, both columns, inverse and controlled forms, custom-gate calls and integer powers are checked against independently calculated matrix entries. Frozen-compiler tests exercise both modes. The command-line helper accepts `--published-u`; without it, the helper keeps the IBM/Qiskit convention.

### Stabilizer generators, code spaces and syndromes

Following [IBM Quantum Learning's stabilizer-code definition](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes), the calculator now accepts a signed Pauli matrix or a vector of generators:

- `stabilizer_projector(vector(X@X,Z@Z))` constructs the exact projector onto the common +1 eigenspace. Here it is `density(|Phi+>)`.
- `stabilizer_dimension(vector(Z@Z@I,I@Z@Z))` returns 2, the dimension of the three-qubit repetition-code space.
- `stabilizer_syndrome(vector(Z@Z@I,I@Z@Z),I@X@I)` returns `[1  1]`: 0 means the error commutes with that generator, 1 means it anticommutes. The corresponding stabilizer measurement signs are +1 and -1. This is the deterministic syndrome of a Pauli error on a valid encoded state, not a measurement sampler for an arbitrary state.

Generators must be Hermitian signed tensor products of I, X, Y and Z on the same 1–9 qubits. Up to 32 generators are accepted. They must commute, and their generated group must not contain -I. Consistent redundant generators (including +I) are accepted; the dimension is computed from independent binary generators. Inconsistent signs, such as XX, ZZ and +YY together, are rejected. Syndrome errors may carry any of the phases ±1 or ±i, which do not change the syndrome. A one-entry syndrome simplifies to a scalar under libqalculate's usual vector rules.

The implementation validates the Pauli form, uses binary symplectic commutation and signed group elimination, and forms the projector through exact rational/complex arithmetic using sparse Pauli actions. The functions do not automatically construct encoding/decoding circuits and do not implement unrestricted symbolic group objects. Independent tests compare all signed two-qubit generator pairs against numerical common eigenspaces and verify the five-qubit code's dimension and all 15 distinct single-qubit-error syndromes.

### Pasting stabilizer group notation

The first argument of `stabilizer_projector`, `stabilizer_dimension` and `stabilizer_syndrome` accepts generated-group brackets, following the notation in [IBM's stabilizer lesson](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes):

- `stabilizer_projector(⟨XX, ZZ⟩)` gives the Bell-state projector.
- `stabilizer_dimension(<ZZI, IZZ>)` gives 2.
- `stabilizer_syndrome(⟨ZZI, IZZ⟩, pauli(IXI))` gives `[1  1]`.
- `stabilizer_dimension(\left\langle XX, ZZ, -YY\right\rangle)` gives 1; the third generator is redundant and consistent.

Inside this specific group argument, adjacent I/X/Y/Z letters are tensor factors, so `XX`, `X X`, `X@X`, and `X⊗X` all denote the two-qubit Pauli XX. Optional leading signs and Pauli phases follow the `pauli(...)` convention; non-Hermitian generators are still rejected by the stabilizer validation. ASCII, Unicode, and LaTeX angle brackets are accepted, including TeX sizing and font commands. Up to 32 generators on 1–9 qubits are supported.

These brackets specify generators without enumerating the entire group. Outside this argument position, angle brackets retain their existing bra–ket/comparison meaning. General generator expressions can still be supplied with `vector(...)`; bracketed shorthand is limited to signed Pauli words and tensor separators. Empty generators, missing brackets, invalid tensor separators, noncommuting lists and inconsistent signs are rejected.


### Stabilizer distance and code parameters

`stabilizer_distance(generators)` computes the minimum weight of a Pauli operator
that commutes with every generator but is not proportional to a stabilizer.
This follows [IBM Quantum Learning's logical code-distance definition](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes).
`stabilizer_parameters(generators)` returns `[n k d]`, the three entries in
`[[n,k,d]]` code notation: physical qubits, encoded logical qubits, and distance.
This is a flat numeric result, not a new bracket-expression grammar.

Examples:
- `stabilizer_parameters(⟨XZZXI,IXZZX,XIXZZ,ZXIXZ⟩)` → `[5 1 3]`.
- `stabilizer_parameters(⟨ZZZZIII,ZZIIZZI,ZIZIZIZ,XXXXIII,XXIIXXI,XIXIXIX⟩)` → `[7 1 3]` (Steane).
- `stabilizer_distance(⟨ZZI,IZZ⟩)` → `1`: repetition protects bit flips, but a single Z acts logically.

The computation is exact and exhaustive for the supported 1–9 physical qubits.
Binary symplectic elimination tests membership modulo phase, so low-weight
stabilizers in degenerate codes do not incorrectly lower the distance.
Consistent redundant generators and signed generators are accepted. At least one
logical qubit is required: full-rank stabilizer states (`k=0`) are rejected with
an explicit diagnostic, because their alternative structural-distance convention
is not used here. General large-code distance searches remain unsupported.
Tests independently inspect Pauli action on projected two-qubit code spaces,
and check the five-qubit, Steane, Shor, repetition and degenerate ancilla codes.


### Lowest-weight syndrome correction

`stabilizer_correction(generators, syndrome)` returns a Pauli correction matrix.
Syndrome entries are 0/1 in generator order; for one generator a scalar is also
accepted. These are sign bits (0 means +1), not eigenvalues. Signed and redundant
generators use the same conventions as `stabilizer_syndrome`.

For example, `stabilizer_correction(⟨ZZI,IZZ⟩,[1,1])` returns IXI. Applying that
matrix after a middle-qubit X restores the repetition-code state. The operation
exhaustively searches 1–9 qubits. Impossible syndromes, including contradictions
between redundant checks, are rejected. Zero syndrome selects identity.

The strategy follows [IBM's stabilizer correction lesson](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes).
It guarantees correction for Pauli errors of weight at most floor((d−1)/2).
A measured syndrome alone does not identify every possible error; errors outside
the code's correction capability can leave a logical error. This is a minimum-weight
decoder, not a decoder optimized for a supplied noise model.

Ties choose the smallest binary value x+(z<<n), with qubit zero most significant.
The returned tensor product uses positive I/X/Y/Z factors. Global phases do not
change correction. Full-rank stabilizer states are supported here. The function
returns a matrix, not a measurement circuit or automatic classical-feedback program.

Validation exhausts syndromes of representative small codes and checks every
single-qubit Pauli error for the five-qubit, Steane and Shor codes. Independent
numeric projector calculations confirm recovery of complex encoded states.


### Pauli labels and direct matrix construction

`pauli("XYZ")` and `Pauli('XYZ')` both construct X⊗Y⊗Z. Labels may be
unquoted, single-quoted or double-quoted. A prefix consists of an optional sign,
optional `1`, and optional `i` or `j`: for example `-1jXYZ`, `+iYY`, or `-1Z`.
The prefix is a global phase. This matches the string forms documented for
[Qiskit Pauli](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Pauli).
It does not execute Python object methods or other Qiskit code.

Qiskit numbers the rightmost label character as qubit zero. Quantum Studio's
circuit editor instead numbers the leftmost tensor factor as wire zero; the
matrix associated with a fixed Pauli word is unchanged. Labels remain limited
to 1–9 letters. Stabilizer group shorthand accepts the same prefixes but still
requires Hermitian generators, so an imaginary overall phase is rejected there.

Construction now derives the sparse Pauli entries from binary X/Z masks and a
phase modulo four, then builds the result directly. It no longer evaluates a
chain of intermediate tensor products. Numeric results retain exact phases.
Independent tests compare every Pauli word through three qubits in all four
phases with NumPy tensor matrices, check larger words through nine qubits, and
exercise all prefix spellings and malformed labels. Existing tensor notation
continues to use the general tensor-product implementation.


### CSS check matrices and coset states

`css_generators(Hx,Hz)` converts rows of binary check matrices to positive Pauli
stabilizers: X checks first, then Z checks, preserving row order. Columns are
qubits, with the leftmost column the most significant tensor factor. It requires
`Hx Hz^T = 0` over GF(2). The construction follows
[IBM Quantum Learning's CSS lesson](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/css-codes).

`css_state(Hx,Hz,u)` returns the normalized uniform ket on the coset obtained by
XORing the basis index u with every distinct word in the row space of Hx.
The representative must pass every Z check. This realizes the lesson's
|u ⊕ D_X⟩ code-space vectors; different representatives may give the same state.
It does not choose a logical basis or synthesize an encoding circuit.

Both functions accept 1–9 columns and at most 32 total check rows. Empty `[]`
means no checks of that type; both sets cannot be empty because the width would
be unknown. A scalar is a 1×1 check, a flat vector is one row, and zero or
redundant rows are accepted. State normalization uses the number of distinct
row-space words, not the number of supplied rows.

Examples:
- `stabilizer_parameters(css_generators([1,1,1,1],[1,1,1,1]))` → `[4 2 2]`.
- `css_state([1,1],[1,1],0)` → the Bell state (|00⟩+|11⟩)/√2.
- `css_generators([],[1,1,0;0,1,1])` → the repetition-code Z checks.

Tests exhaust three-column single-row check pairs against independent tensor
projectors and verify the Steane logical states, redundancy, one-sided checks,
syndrome ordering, correction composition and input limits.


### CSS state preparation in the circuit editor

Choose **Build → CSS code state** in the composer. Enter Hx and Hz as binary
check matrices and a representative bitstring with q0 first. The defaults
prepare Steane logical |0⟩; changing the representative to 0000111 prepares
the lesson's logical |1⟩. Use [] for an absent check type. The builder supports
1–8 qubits and at most 32 total rows, within the editor's 64-step limit.

The generated circuit starts from |0…0⟩. Binary row reduction selects independent
X-check pivots. Hadamards prepare those pivot bits, CNOTs generate the remaining
row-space bits, and final X gates apply the representative shift. The result
matches the native css_state function, including amplitudes and phase. This
prepares one selected coset state; it is not a general encoder for an unknown
logical input or a fault-tolerant preparation procedure.

All checks are validated before replacing the circuit. The result supports
undo/redo, editing, save/open, calculator inspection and OpenQASM export.
Tests exhaust the three-qubit single-row combinations and include Steane,
redundant rows, one-sided checks and mixed-row cases through eight qubits.
They compare exported gate sequences with independent projector amplitudes and
the native CSS state constructor, and verify that invalid inputs preserve the
previous circuit.


### CSS encoding isometry

css_encoder(Hx,Hz) returns the exact 2^n by 2^k encoding matrix V, where
k = n − rank(Hx) − rank(Hz). It accepts the same binary checks and 1–9 qubit,
32-row limits as css_generators. Multiplying V by a logical ket encodes all of
its amplitudes coherently. V†V is identity; VV† is the code-space projector.
For density matrices, use V ρ V†. The adjoint decodes states already in the code
space; it is not by itself an error-correction operation on arbitrary inputs.

Logical basis convention: begin with the X-check row space, scan integer words
from smallest to largest, and extend it with each unused word satisfying all
Z checks. The first selected representative corresponds to the least significant
logical bit. Each encoding column is the normalized coset superposition for
the XOR combination selected by that column's binary index. This convention
is invariant under redundant or row-equivalent checks. It gives the identity
map for a code with only zero checks and matches the two Steane logical states
shown in IBM's CSS lesson. With k=0, the result is a single normalized column.

Example: css_encoder([],[1,1,0;0,1,1]) maps |i⟩ to
(|000⟩+i|111⟩)/√2. Apply a suitable syndrome correction before decoding an
errored state. The matrix represents an isometry. The composer can synthesize
a full unitary extension as described below.

Tests construct an independent orthonormal basis from projected computational
states, check exact adjoint identities, complex-state recovery and density
encoding, and verify the Steane convention and nine-qubit boundary.

### CSS encoding circuits

Choose **Build → CSS encoding circuit** for an H/CNOT/SWAP implementation of
css_encoder(Hx,Hz). The first k wires contain the logical input in ordinary
most-significant-wire-first order; the remaining n−k wires start at zero.
The logical basis matches the exact isometry, including its relative phases.
The extension on nonzero ancillas is not part of that isometry specification.

Select **Append to my current logical-input circuit** to preserve a prepared
k-qubit state while adding the ancillas and encoding gates. For example, prepare
H then S on one qubit and append the default Steane encoder to encode |i⟩.
Mixed inputs and noise channels are preserved; such circuits can be saved as
.qcircuit files, while OpenQASM export rejects unsupported noise channels.
Without Append, the builder replaces the circuit with the encoder acting on
the all-zero input. Append requires k>0 and an existing register of exactly k
qubits. Limits are 1–8 physical qubits, 32 check rows and 64 total steps.
Invalid checks, incompatible registers and excess steps preserve the old circuit.

Construction selects a basis of the X-check row space and the canonical logical
representatives, extends these to an invertible binary matrix, applies H to
the X-span input wires, then synthesizes that matrix using CNOT and SWAP.
Independent tests verify 73 circuits across 565 logical basis columns, coherent
and noisy append, save/open, undo/redo, export and 28 incompatible check pairs.
General non-CSS stabilizer encoders and fault-tolerant encoding remain open.

### Cirq power gates used by qBraid VQE

The public qBraid `qBraid-Algorithms/cirq_vqe.ipynb` notebook uses
XPowGate, ZPowGate and CZPowGate with half-turn exponents. Calculator calls
with those names now accept `exponent` and `global_shift`, either as named
arguments in either order or positional (exponent, shift). Defaults are 1 and 0.
For example, `XPowGate(exponent=1/2)` is SX, `ZPowGate(1/4)` is T, and
`CZPowGate(1/2)` is controlled-S. Duplicate or unknown keywords are rejected.
These expressions describe two-level qubits; the Cirq `dimension` option and
Python `cirq.` namespace are not accepted.

XPowGate(t,s) = exp(i π t (s+1/2)) Rx(πt).
ZPowGate(t,s) = exp(i π t s) P(πt).
CZPowGate(t,s) = exp(i π t s) CP(πt).
The default phase of XPowGate differs from Rx, including for noninteger powers.
The full phase is retained when these matrices are passed to controlled().
Tests compare 262 identities across negative, fractional and zero exponents,
global shifts, equivalent keyword orders and controlled forms; eight malformed
calls are rejected.

Sources: [Cirq XPowGate](https://quantumai.google/reference/python/cirq/XPowGate)
and [Cirq CZPowGate](https://quantumai.google/reference/python/cirq/CZPowGate).
The pinned qBraid notebook audit in `qbraid-notebook-audit.json` records the
specific source revision and remaining gaps. Code cells and Markdown in all 35 pinned notebooks have been
statically inspected; executable workflow and linked-course audits remain open. The literal five-qubit Deutsch–Jozsa example imports;
two ten-qubit PyQASM examples exceed the editor limit. Python/GPU/provider
execution and complete notebook compatibility are not implied by gate support.


### iSWAP in OpenQASM SDK workflows

The qBraid SDK transpiler example includes iSWAP. The native matrix and visual
composer already supported it; the importer now also accepts primitive
`iswap a,b;`. Inverse and integer-power modifiers preserve its odd-parity phase.
One `ctrl` or `negctrl` is supported, including inverses before or after control.
Multiple controls and fractional OpenQASM powers remain unsupported.

The inverse is iSWAP followed by Z on both targets. A controlled version applies
CP(π/2) from the control to each target, then CCZ and CSWAP. Inverting it changes
the CP angles to −π/2. This retains relative phases on superposed controls.
Tests cover all matrix columns, coherent inputs, reversed target order and a
control that is not the first physical wire. Source-defined gates named iswap
still use their own definition. Malformed arity and duplicate wires are rejected.

Source: [IBM iSwapGate matrix](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.iSwapGate).
The pinned audit now covers the six qBraid SDK notebooks as well as the earlier
eight algorithm/PyQASM notebooks. The SDK Bell OpenQASM literal is independently
checked after nonselective measurement. Framework constructors, conversion graphs,
provider jobs, Python visualization functions and random circuit generation are
not executable calculator notation and remain outside implemented program support.


### Hellinger measures for measured distributions

`hellinger_fidelity(p,q)` and `hellinger_distance(p,q)` accept aligned vectors
of counts or probabilities and normalize each by its own total. Row vectors,
column vectors and a scalar representing a single outcome are accepted, with
1–1024 outcomes. Values must be finite nonnegative real numbers, the total of
each input must be positive, and lengths must match. Broad uncertainty, complex
amplitudes and general matrices are rejected. Use zero for a missing outcome;
Python dictionaries and automatic bitstring-label alignment are not implemented.

For normalized p and q, fidelity is (Σ sqrt(p_i q_i))². Distance is
sqrt(Σ (sqrt(p_i)−sqrt(q_i))² / 2). The distance implementation uses the squared
differences rather than subtracting an overlap from one, reducing cancellation
for nearly equal distributions. Identical exact normalized entries contribute
zero directly. Familiar rational fidelities remain exact in exact mode.

Example: `hellinger_fidelity([100,0,0,100],[90,10,10,90])` is 9/10.
This supports the measurement-distribution comparison in qBraid's Quobly GHZ
benchmark. It does not reproduce the provider's noise model. Measurement
fidelity ignores coherence and is not general quantum state fidelity.

Sources: [IBM Hellinger measures](https://quantum.cloud.ibm.com/docs/en/api/qiskit/quantum_info#hellinger_fidelity)
and the pinned runtime notebook in `qbraid-notebook-audit.json`. The audit now
also covers four QIR and eight runtime notebook code-cell sets. Their analog
pulse programs, provider jobs and framework execution remain unimplemented.


### Binary numerals in phase estimation

The QPE lesson writes the measured phase 1/2 as `0.100_2`. Quantum mode now
accepts finite binary integer/fractional numerals using `_2`, Unicode `₂`, or
TeX `_{2}`. Conversion produces an exact integer divided by a power of two,
without floating-point conversion. Both integer and fractional parts are allowed:
`10.101₂ = 21/8`. Unary signs and powers retain ordinary arithmetic precedence.

Limits: 1024 binary digits and one optional radix point. Nonbinary digits,
repeated base-two subscripts, ASCII radix subscripts other than 2, and scientific
exponents inside binary numerals are rejected. Other Unicode radix subscripts
are not interpreted as numeric bases. A suffix outside a parenthesized numeral,
repeating expansions and symbolic bit sequences are not implemented. Numeric
expression complexity limits still apply to the surrounding expression.
Dimension-qualified kets such as `|1>_3` retain their separate meaning.

Source: the pinned [qBraid QPE lesson](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qpe.ipynb).
119 exact identities cover input spellings, signs, powers, matrix/ket use,
ordinary decimal/scientific regression cases and the digit boundary.

### Public qBraid notebook audit status

All 35 notebook code-cell and Markdown sets at the pinned revision have received
static review. Seven literal OpenQASM programs are checked numerically and two
ten-qubit capacity gaps are reproduced. This establishes neither full SDK
execution nor coverage of every linked course, generated program, saved output
or external include file. The detailed JSON audit records outstanding indexed
spin framework methods, abstract graph sums, analog pulse programs, larger circuits,
framework execution and provider workflows.

The audit also records source issues. In the AutoQASM Deutsch–Jozsa prose,
the psi_2 denominator is written sqrt(2^n+1), although the unnormalized sum has
squared norm 2^(n+1). The required denominator is sqrt(2^(n+1)); at n=4 the
printed state has squared norm 32/17. This is a source normalization error,
not a convention the calculator should adopt. Two provider examples also mix
an OpenQASM 2 header with version-3 declarations; pinned PyQASM accepts these,
but that does not establish strict version-2 conformance.


### CUDA-Q indexed spin expressions

`spin.i(k)`, `spin.x(k)`, `spin.y(k)` and `spin.z(k)` now build Pauli operators
on a shared register inferred from the largest index anywhere in the expression.
The register includes indices 0 through that index, including identities on unused
positions. Indices are literal nonnegative integers from 0 to 8. Index zero is
the rightmost tensor factor, following CUDA-Q qubit ordering rather than the
composer's leftmost-wire convention. `spin.z(0)*spin.i(1)` therefore gives I⊗Z.
Multiplication on one index retains Pauli order and phases; factors on different
indices commute. Add an identity factor on the desired highest index to extend
an otherwise smaller register.

The Python-qualified `cudaq.spin.x(k)` and C++ `cudaq::spin::x(k)` /
`cudaq::spin_op::x(k)` spellings are accepted too. In an expression containing
indexed spin factors, scalar-plus-square-operator additions promote the scalar
to an identity offset. Scalar/scalar arithmetic is unchanged; adding matrices
or vectors requires matching shapes. This contextual rule also applies to other
square matrices used in that same expression. It does not change ordinary
calculator expressions that contain no indexed spin factors.

The CUDA-Q/qBraid Hamiltonian expression can be pasted without replacing its
scalar offset or manually building tensor products. Its theta=0 ansatz is |01⟩
in the app's tensor order and gives energy −0.43629. For general theta the
independent analytic expectation is 5.907 − 4.2866 sin(theta) − 6.34329 cos(theta).
The example library includes both a scalar-offset demonstration and this energy.

The app's full-register embedding is explicit: it does not imitate compressed
active-degree matrix layouts or object-method options in every CUDA-Q version.
Python/C++ assignment statements, kernels, `observe` calls, symbolic indices,
framework objects and arbitrary SDK execution are still unsupported.

Sources: [CUDA-Q operator specification](https://nvidia.github.io/cuda-quantum/latest/specification/cudaq/operators.html)
and [Python operator matrix ordering](https://nvidia.github.io/cuda-quantum/latest/api/languages/python_api.html).
Independent tests cover 87 matrices/order/offset/expectation cases and 11 invalid
expressions, including the full qBraid Hamiltonian, complex Pauli products,
register extension, every supported namespace and the nine-qubit boundary.


### Literal XOR in query-gate basis labels

Inside an unqualified bra or ket, `⊕` and TeX `\oplus` combine literal,
equal-width binary strings: `|001 ⊕ 101⟩` is `|100⟩`, and
`\bra{001\oplus 101}` is `⟨100|`. Chains are evaluated left to right.
Leading zeros preserve register width. Each operand has 1–10 bits.
Comma-separated registers and adjacent kets compose as usual:
`|01,001⊕101⟩` is `|01100⟩`. Unequal widths, empty operands, nonbinary
digits, named states, symbolic variables and function-valued operands are
rejected. Explicit qudit dimensions do not enable XOR label syntax.

Outside state labels, `X ⊕ Z` remains a matrix direct sum, including its
existing scalar behavior. Use `bitxor` for general bit-vector expressions
and `oracle(table,m)` for finite query gates. This is not a parser for
abstract mappings such as `f:Σⁿ→Σᵐ` or symbolic `|y⊕f(x)⟩`.

The regression suite exhaustively checks all three-bit pairs in bras and
kets, register composition, the ten-bit boundary, invalid labels, direct-sum
preservation and all basis inputs of a one-input/three-output-bit oracle.
Source: [IBM Quantum Learning, query gates](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/query-model-of-computation).
