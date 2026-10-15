Quantum Studio for Windows x64

Schmidt coefficients: schmidt_coeffs(3|00>+4i|11>,0) gives [0.8;0.6].
Supports pure-state bipartitions and explicit qudit dimensions. See the guide
for numerical limits; this does not return the local Schmidt basis vectors.

XXPlusYY(theta,beta) and XXMinusYY(theta,beta) support parity-selective
two-qubit rotations, circuit editing, and phase-preserving OpenQASM export.

The Notation guide button opens a bundled, searchable offline reference.
Fractional gate powers now evaluate: try sqrt(X), sqrt(SWAP), or (H*S)^(1/2).
Matrix logarithms use logm(U); i*logm(U) is a unit-time Hamiltonian generator.
See Evolution and measurement in the guide for branches and numerical limits.
Exact special cases retain their phase; general unitary/Hermitian powers
use numerical spectral evaluation. See Controls and interactions in the guide.
Search by operation or multiple words, press / to focus search, and Escape
to clear it. Topic links navigate directly to the relevant notation.

Operator double brackets accept grouped expressions: |(X+iY)>> and
<<(X+iY)|(X+iY)>>. The latter is the Hilbert-Schmidt overlap, equal to 4.

Negativity and logarithmic negativity analyze entanglement in noisy circuits:
negativity((|00>+|11>)/sqrt(2),0) returns 0.5. Use lognegativity for the
base-2 logarithmic measure. Both support total state dimensions up to 64.
See Quantum entropy in the guide for mixed dimensions and numerical limits.

RUN
Extract the entire ZIP, then double-click QuantumStudio.exe.
Keep quantum-worker.exe, data, and DLLs beside it. No MSYS2 installation is
required to run the packaged app. The GUI uses Windows .NET Framework 4.x/WPF
(included with Windows 11). This is a portable unsigned application.

Choose Quantum notation for bra-ket expressions and Standard calculator for
ordinary Qalculate! syntax. Choose Exact arithmetic or Numerical evaluation.
Numerical mode uses 30-digit working precision; displayed digits may be fewer.
Ctrl+Enter calculates. Copy copies the result. History recalls evaluation mode.
Double-click a history item to recall it. Save session writes a .qsession file
with the current draft, its modes, and up to 50 history entries. Open session
replaces the current workspace after validating the whole file. Saved results
are text snapshots; opening never runs expressions. Large history results are
shortened to 32768 characters; recalculate for the full result. Session files
are limited to 8 MB and are saved only when you choose Save session. Circuit
editor state is saved separately as .qcircuit. The notation guide includes
examples, qubit ordering, and coverage limits.
Browse all examples opens a searchable library of editable circuit, measurement,
noise, and evolution expressions. Select an entry and choose Use selected example.
Compose a circuit opens a visual editor for 1–8 qubits and up to 64 gate steps.
Choose a gate and ordered wire indices, then Add gate. Controls come first.
Build > CSS code state prepares a coset state from binary X/Z check matrices
and representative bits. Defaults prepare Steane logical zero; 0000111 gives
logical one. The generated H/CNOT/X circuit is editable and exportable.
Build > CSS encoding circuit encodes arbitrary logical amplitudes using
H/CNOT/SWAP. The first k wires carry the logical input; other wires start at zero.
Select Append to retain an existing k-qubit input preparation, including noise.
For Steane |i>, prepare H then S on one qubit and append the default encoder.
Noise remains saveable in .qcircuit files but cannot be exported to OpenQASM.
Controlled gates include CY, CH, CCZ, and CSWAP (one control, two swap targets).
Sdg, Tdg, SX, and SXdg provide adjoints and the conventional square-root X gate.
In expressions, SX is one gate; write S X or S*X for their matrix product.
Reset reinitializes its selected wire to zero and returns a density matrix.
It preserves the reduced state of other wires, including mixed states.
Measure performs Z-basis measurement with its outcome discarded. The expression
dephase(state,indices) computes this ensemble state, without random sampling.
feedforward(state,measured,outcome,U,targets) measures and conditionally applies
an operator while retaining all branches. The example library includes teleportation.
The composer also provides a Teleport example and M0-X/M1-X/M0-Z/M1-Z steps:
measure the first wire and correct the second when the result matches 0 or 1.
Dashed lines indicate measurement feedback. Export includes classical bits and
conditional gates for these steps; each step performs a fresh measurement.
CP, CRx, CRy, and CRz provide controlled phase and rotations; enter control then
target wire and an angle in radians. CP and CRz retain their distinct phases.
Dimension-qualified basis notation supports qudits: |2>_3 equals basis(2,3).
Here the subscript means dimension, not wire number. Unsuffixed binary kets keep
their qubit meaning; nonbinary numeric labels require an explicit dimension.
SUM(d) or SUM_{d} is qudit modular controlled addition; SUM(dc,dt) supports
different dimensions. The example library includes entangled qutrit preparation.
permute(state,order,dimensions) reorders tensor factors; omit dimensions for
qubits. After permuting mixed dimensions, use the reordered dimension list in
subsequent operations. Results do not store subsystem metadata.
vec(A) column-stacks an operator; unvec(v,rows) reverses it. Double kets such as
|Y>> and double bras <<Y| use this convention. The example library demonstrates it.
superop(vector(K0,K1,...)) and choi(vector(K0,K1,...)) convert Kraus operators
to channel matrices. Choi order is input ⊗ output and is not trace-normalized.
The circuit preview's File menu contains Open, Save, and Export OpenQASM.
Its Examples menu contains Bell states, Teleportation, Bit-flip correction,
Phase estimation, and Grover search.
Zoom ranges from 25% to 150%; Fit wires fits the register vertically. Long
circuits scroll horizontally, and small windows let the whole editor scroll.
Expand Measurement and feedback help or Equivalent expression when needed.
These view settings do not change the circuit or get saved in .qcircuit files.

Load into calculator transfers the expression for evaluation. Save circuit and
Open circuit preserve editable .qcircuit files across sessions. Unsaved edits are
temporary; changing register size clears its steps. Angles accept expressions.
Export OpenQASM writes an OpenQASM 3.0 program using stdgates.inc. Export angles
support numbers, pi, + - * / and parentheses, with explicit multiplication.
The program resets the register to zero and preserves gate and wire order.
It exports explicit Measure steps without storing outcomes. This is export only;
arbitrary QASM import is unsupported.

Examples include Bell states, Grover search, QFT, Toffoli, indexed nonadjacent
gate application, density matrices, partial traces, and Kraus channels.
Mathematical TeX fragments support fractions, roots, bra/ket macros, matrices,
norms, finite indexed sums/products, and subscripted multi-qubit partial traces.
This is a finite-dimensional calculator, not universal quantum notation support.

qalc.exe is also included. From this directory:
  qalc.exe -t "quantum:CNOT (H @ I) |00>"

SOURCE AND LICENSE
libqalculate and the Quantum Studio extension are GPL-2.0-or-later. See LICENSE.txt.
Source in the accompanying repository includes libqalculate/Quantum.cc,
src/quantum-worker.cc, windows/, tests/quantum.batch, and research notes.
Rebuild with windows/build-native.sh in MSYS2 UCRT64, then run
windows/package.ps1 in PowerShell. Prerequisite packages are listed in the script.
No downloaded prebuilt libqalculate binary is substituted for the modified source.

Bundled native runtimes originate from MSYS2 UCRT64 packages (GCC runtimes,
GMP, MPFR, libxml2, libiconv, winpthreads). License texts available in the packages
are copied to licenses/. GMP and MPFR are LGPL-3.0-or-later (or GPL-2.0-or-later).
Package metadata and corresponding source build recipes:
https://packages.msys2.org/package/mingw-w64-ucrt-x86_64-gmp
https://packages.msys2.org/package/mingw-w64-ucrt-x86_64-mpfr
https://github.com/msys2/MINGW-packages
Upstream libqalculate: https://github.com/Qalculate/libqalculate
Exchange gates: iSWAP/ISWAP and fSim(theta,phi) are available in quantum mode.
Grover search: phaseoracle(n,marked) flips selected decimal basis indices;
diffusion(n) reflects about the uniform state. Both support 1–9 qubits.
See the Algorithms examples for single- and multiple-solution searches.
Reversible queries: oracle(table,m) maps |x,y> to |x,y XOR table[x]>.
m defaults to one output qubit. The Algorithms library includes Deutsch–Jozsa.
modmul(a,N) builds a reversible modular multiplier for coprime a,N (N <= 512).
The Algorithms library includes order-finding and exact phase-estimation examples.
Spin operators: Jx(j), Jy(j), Jz(j), Jplus(j), and Jminus(j) accept integer
or half-integer j from 1/2 through 63/2. The basis is m=j,j-1,...,-j and
hbar=1. For spin 1/2 Jx, Jy, Jz are Pauli matrices divided by 2.
Subscript notation J_x(j), J_y(j), J_z(j), J_+(j), J_-(j) and TeX
forms such as \hat{J}_{+}(j) are supported with the same explicit spin.
Bosonic operators: destroy(d), create(d), and numberop(d) use an explicit
2–512-level Fock-space truncation. See the Bosonic operators examples for the
upper-boundary correction to the creation/annihilation commutator.
Fermions: fdestroy(modes,site) and fcreate(modes,site) use Jordan–Wigner
parity strings for 1–9 modes, with mode 0 the leftmost occupation bit.
FSWAP exchanges adjacent fermionic modes and negates |11>. It is available in
the composer and exports as SWAP then CZ. For nonadjacent fermionic mode
permutations, compose adjacent FSWAPs to preserve the intervening parity signs.
Mathematical TeX accepts operator hats: \hat{X}, \hat{\sigma}_{y}, and
\widehat{X+Y}. Hats preserve existing operator definitions and grouping.
Quantum mode accepts imaginary coefficients next to fixed gate names: iY,
-iX, and iSdg. iSWAP keeps its own gate meaning. Powers bind to the gate,
so iY^2 means i*(Y^2); use (iY)^2 to square the full product.
iSWAP is also available in the composer and exports as SWAP, S, S, CZ.
fSim uses radians and the Cirq negative exchange/controlled-phase convention.
In the composer, enter fSim's angles as theta, phi (for example pi/3, pi/4).
Its OpenQASM export uses standard H, Rx, CX, Rz and CP gates.
The composer also offers U3: enter theta, phi, lambda separated by commas.
Select a numbered step above the circuit to edit its gate, wires or angles.
Update gate applies the edit in place; Cancel edit preserves the original.
Editing remains available at the 64-step limit. Invalid edits do not alter steps.
U3 exports as P(lambda), Ry(theta), P(phi), preserving the calculator's phase.
The composer includes Rxx, Ryy, Rzz and Rzx interaction rotations. Enter two
wire indices in axis order and one angle in radians. Export uses standard
basis changes and CX–Rz–CX, preserving global phase.

Move earlier and Move later reposition the selected committed gate, preserving
its wires and angles. Pending field edits remain in the editor until Update gate.
Delete selected removes that step immediately. These operations change the
calculated state and the saved/exported gate order; Cancel edit does not undo them.
Undo and Redo restore up to 100 committed circuit changes in this window,
including gate edits, moves, deletions, register changes, file opening, and
example replacement. A new circuit change clears redo history. Selecting a
step or an invalid edit does not. Pending text field edits are not circuit
history; Undo/Redo discard them and leave no step selected. History is not saved.
Two-bit feedback gates M00-X, M01-X, M10-X, M11-X (and Z variants) take
three distinct wires: two measured wires in bit order, then the target.
Each step performs fresh Z measurements. Bit-flip correction loads a five-qubit
repetition-code example: encode |i>, flip data qubit 1, measure two parities,
correct the syndrome and decode. Use ptrace(expression,[1,2,3,4]) to inspect
recovered q0. This example corrects one X error, not arbitrary quantum noise.
Spin-half arrow labels use |↑> = |0> and |↓> = |1>. Multiple arrows form
ordered qubit products, for example |↑↓> = |01>. TeX \uparrow and \downarrow
work inside bra/ket labels. Explicit dimension suffixes require numeric labels.
Product-state labels can mix 0, 1, +, -, and spin arrows: |0+>, |+->,
and |+↓-> denote ordered tensor products. The labels |i>, |+i>, and |-i>
remain single-qubit Y eigenstates; write explicit tensor products for them.
Matrix elements group the complete operator between bra and ket bars:
<+-|X @ X|+-> and <0|X+Z|0> no longer need extra operator parentheses.
This also applies to TeX braket expressions and operator double-kets.
Entropy: entropy(state) returns von Neumann entropy in bits. Nonzero kets
have zero entropy. Density matrices (dimension 2-64) are normalized by trace
and checked numerically for Hermiticity and positive semidefiniteness.
Matrix results use a double-precision eigensolver and display approximately
12 significant digits; increasing calculator precision does not increase this.
Unicode integer powers such as X², H⁻¹, X¹², and (X+Z)² are accepted.
Powers bind to the preceding gate: iY² = i(Y²), while (iY)² squares the
whole product. Superscript runs require digits with an optional initial sign.
Circuit saving tolerates short-lived file locks. If another application keeps
the destination locked, saving reports an error and preserves the existing file.
The optional entropy(state,base) form uses any finite real base greater than
one; use e for nats or 10 for decimal units. The default remains base 2.
Trace distance: tracedistance(a,b) or tracedist(a,b) measures distinguishability
of two kets/density matrices of the same dimension (2-64). Inputs are normalized;
zero is identical and one is perfectly distinguishable. Results are approximate,
using the same numerical precision and physical-state checks as matrix entropy.
Fidelity: fidelity(a,b) returns squared state fidelity, matching Qiskit
state_fidelity, for normalized kets/density matrices of dimension 2-64.
This differs from conventions that return the square root. Results are
numerical; near rank deficiency, displayed digits may exceed actual accuracy.
Measurement charts: quantum-mode expressions starting with probs(...) show a
bar chart for 2-64 outcomes, alongside the original result. Bars and percentages
are approximate; outcome indices follow the returned vector order. Choose
Decimal or Binary labels for power-of-two outcome counts. Binary indices keep
leading zeroes and follow your marginal wire order. This view preference lasts
until the app closes; switching labels does not recalculate the result. Larger,
symbolic, uncertain or invalid distributions retain the ordinary result view.
Noise constructors: amplitude_damping(p), phase_damping(p), and depolarizing(lambda)
return lists of single-qubit Kraus matrices for channel(), choi(), and superop().
Damping p is in [0,1]; depolarizing lambda is in [0,4/3], with lambda=1
fully mixing the qubit. Use channel(density(state),constructor,wire) for local
noise in a register. See the Noise channels examples and notation guide.
Finite-temperature form: amplitude_damping(p,excited_population), where the
second argument is the equilibrium probability of |1>. Combined damping:
phase_amplitude_damping(amplitude,phase[,excited_population]); amplitude+phase
must not exceed one, and the equilibrium population defaults to zero.
The circuit editor includes AD (amplitude damping), GAD (generalized amplitude
damping), PD (phase damping), PAD (combined damping), and Depol. Select one to
see its parameter order and range; amber blocks mark noise on a chosen wire.
Noise circuits evaluate as density matrices and save/open as .qcircuit files.
OpenQASM export explicitly rejects noise circuits rather than dropping noise.
Chi process matrices use chi(Kraus_list), Chi, or Unicode chi, with
E(rho)=sum(chi_ij P_i rho P_j)/d and trace chi=d for a trace-preserving map.
Ordinary multiplication of chi matrices does not compose channels.
R(theta,phi) rotates about cos(phi)X+sin(phi)Y, with both angles in radians.
spre(A), spost(B), and sprepost(A,B) represent left, right, and two-sided
multiplication on column-stacked operators. Inputs have at most 16 rows and
columns; spre/spost require square inputs, sprepost allows rectangular ones.
The editor supports R with two parameters and exact Rz-Rx-Rz OpenQASM export.
Lindblad dynamics: lindblad_dissipator(C) and liouvillian(H,vector(C0,C1,...))
construct column-stacked generators. liouvillian(H) omits dissipation. Use
sqrt(rate)*C for a collapse operator at that rate, with hbar=1. H must be
Hermitian and all operators have matching dimension 2 to 16. Propagate with
unvec(expm(t*liouvillian(H,Ks))vec(rho),d); general numerical propagation is
limited to d<=8 by the existing matrix-exponential limit.
Controlled-gate patterns: controlled(X,2,"01") accepts a quoted binary pattern
with exactly one digit per control. The first control is the leftmost bit.
Pauli transfer matrices: ptm(Kraus_list) or PTM(Kraus_list), for one to four
qubits. Basis order is I,X,Y,Z for one qubit and II,IX,IY,IZ,XI,... for two.
Use ptm(vector(U)) for the channel rho -> U*rho*U-dagger. No trace normalization
or trace-preservation certification is applied to the supplied Kraus matrices.
Pauli coordinates: paulivec(A) returns Tr(P_j*A)/sqrt(d) in the same basis,
and unpaulivec(v) reconstructs A. Square operators for one to four qubits are
supported, including non-Hermitian operators. These coordinates preserve the
Hilbert-Schmidt norm; for one qubit they are [1,x,y,z]/sqrt(2) for a state.
Pasted notation accepts leading whitespace or a UTF-8 byte-order mark before
quantum:, plus Unicode spaces within expressions. Quoted text is preserved.
Multiline quantum input is supported; ordinary unit conversions remain available
in Standard calculator mode.
Thermal relaxation: thermal_relaxation(T1,T2,time[,excited_population]) returns
Kraus operators with population decay exp(-time/T1) and coherence decay
exp(-time/T2). Use positive T1/T2 (infinity allowed), finite nonnegative time,
and T2 <= 2*T1. Enter numeric times in the same unit. The circuit editor's
Thermal operation takes all four parameters, with excited population in [0,1].
Bloch sphere: bloch(state) returns normalized [x;y;z] coordinates for a qubit
ket or density matrix. In Quantum mode, expressions starting with bloch(...)
also show a sphere projection, rotation controls, vector length and purity.
The plot is approximate; the original coordinate result remains available.
Use bloch(state,wire) to inspect a qubit in a larger register, with wire 0
leftmost. The circuit editor's Inspect selector can load the full state,
measurement probabilities, or a selected qubit's Bloch coordinates.

Calculation controls: choose 15 seconds, 1 minute, 3 minutes, or 10 minutes
before calculating. Cancel stops the worker. Interrupted results are not added
to history. Time allowances are not saved in .qsession files.

In the circuit editor, select Inspect > Schmidt coefficients and enter side A
wires such as 0,2. The other wires form side B. Both sides must be nonempty.
This view accepts pure circuits; circuits with measurement, reset, feedback,
or noise use density matrices and should use the other inspection views.
The view and partition do not alter the saved circuit.

Operator norms: tracenorm(A), frobeniusnorm(A), spectralnorm(A), and
norm(A,p) use the Schatten convention. Indexed bars such as ‖X‖₁ also work.
Order 2 means Frobenius; infinity means spectral. See the guide for limits.

Circuit Examples > Phase estimation · T gate builds an editable 14-gate
circuit. Its marginal-probability view reports 001, the phase 1/8 of a turn.
Marginal probabilities also inspect selected wires of pure or noisy circuits;
enter the wires in the desired outcome bit order.

State reflections: reflection(psi) = I - 2P, with P the normalized projector
onto psi. phase_reflection(psi,theta) applies exp(i*theta) to that state only.
The sign convention differs from diffusion; see the new Grover example.

Circuit Examples > Grover search offers all four two-bit targets. Each editable
circuit prepares a uniform state, applies a phase-marking oracle, and amplifies
the target to 100% ideal probability in one iteration. Its explicit gate
sequence returns -|target>; that global phase is preserved. Choose Load into
calculator to see probabilities. Save/open, undo/redo, and OpenQASM export work
with these presets. These examples use a known target, not an unknown database.

Examples > Bell states offers all four exact Bell preparations. Choose State
to inspect the relative sign; probabilities cannot distinguish plus from minus.
The circuits use H and CNOT, optionally followed by X on q1 and Z on q0, and
support editing, undo/redo, save/open, and OpenQASM export.

Circuit Examples > Bernstein–Vazirani offers all eight three-bit hidden strings.
Each four-qubit circuit prepares the ancilla in |−>, queries f(x)=s·x mod 2,
and recovers s on q0q1q2. Load into calculator to see its marginal probability.
The CNOTs show the selected oracle implementation; this is an editable teaching
example, with save/open, undo/redo, and OpenQASM export.

Circuit Examples > Simon's algorithm offers all eight three-bit masks, including
000 for a one-to-one oracle. Six wires separate the three input and three output
qubits. The default marginal shows the input outcomes: four equiprobable strings
y with y dot s = 0 modulo 2 for nonzero s, or eight outcomes at 1/8 for 000.
Repeated measurements and classical binary equations are needed to recover an
unknown mask. These editable examples show the ideal distribution; they do not
sample shots or automatically solve an arbitrary oracle. Save/open, undo/redo,
and OpenQASM export are supported.

Build > From binary matrix in the circuit composer creates an editable CNOT/SWAP
circuit for an invertible 1-8 bit map. Separate rows with new lines or semicolons,
and entries with spaces or commas. Rows are output bits, columns input bits;
q0 comes first. Building replaces the current circuit; Undo restores it. Invalid
input leaves the current circuit unchanged. The composer now supports 64 steps.

OPENQASM IMPORT
Circuit composer > File > Import OpenQASM imports static OpenQASM 2/3 circuits
through bundled qBraid PyQASM 1.0.4. No separate Python installation is needed.
Keep the qasm-import folder next to QuantumStudio.exe.
The current limits are 8 qubits, 64 compiled steps and 256 KB source.
Angles become numeric. Measurements discard classical outcomes; inspect quantum
wire probabilities. Runtime classical feedback and pulse/timing programs are
rejected. Registers map to wires in declaration order, index zero first.
Build helper: install windows/qasm-import-requirements.txt into .tools/qasm-venv,
then run windows/build-qasm-import.ps1 (also invoked by package.ps1).
U CONVENTIONS: File > Import OpenQASM offers two choices:
- IBM / Qiskit: U uses P(phi) Ry(theta) P(lambda).
- Published OpenQASM 3: uppercase U includes the extra exp(i*theta/2) phase.
The second choice requires a version 3 program. Lowercase u/u3 keep their
IBM/Qiskit convention. One-control U imports preserve the selected phase.
Controlled gphase preserves the full phase for one or two controls.
