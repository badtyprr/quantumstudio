# DEV-11d: finite degenerate instrument and recovery audit

Existing DEV-09 capabilities satisfy these finite cases; no replacement feature
or product fix is proposed. Base is `affdcc843916f1c4c40270135f9f7c2e4d83855f`.
The tested released worker is `214e686668672f2ab405300e88baa008eb40fcf4`, SHA-256
`42126088fd76b9dfa5c7787f9bf66a6429c1baa0985ca9543b508322d4dc955d`.
There are no differences in libqalculate, src, windows or data between those
revisions. This is an audit of that binary, not a newly built release.

## Sources and adaptations

The pinned [source manifest](source-manifest.json) and [source map](source-map.json)
identify notebook URLs, cell-local line numbers and equation hashes. The runner
requires the original IBM-056/058 notebook bytes and verifies their hashes.

| Source | Original expression and location | Executed adaptation |
| --- | --- | --- |
| IBM-058, cell 0 `637926c1`, Measurements from Pauli operations, eq013/014, lines 202/211 | `ZZ = Pi0 - Pi1`; `Pi0 = \|00><00\| + \|11><11\|`, `Pi1 = \|01><01\| + \|10><10\|` | Both `(II +/- ZZ)/2`, instrument labels `+1,-1`, each containing one rank-two Kraus projector |
| IBM-056, cell 0 `1c1d9429`, Unitary qubit errors, eq001/005/006, lines 25/59/67 | `U = alpha I + beta X + gamma Y + delta Z`; `Y=iXZ`; coherent syndrome terms `alpha\|I syndrome>psi + beta\|X syndrome>X psi + i gamma\|XZ syndrome>XZ psi + delta\|Z syndrome>Z psi` | `U=(I+iX+iY+iZ)/2`, known-site three-qubit code described below; preserve syndrome amplitudes and physical Y phase |
| IBM-056, same cell, Arbitrary qubit errors, eq009/010/013, lines 124/130/152 | `Phi(sigma)=sum_j A_j sigma A_j^dagger`; `A_j=alpha_j I+beta_j X+gamma_j Y+delta_j Z`; corrected state `xi tensor \|psi><psi\|`, with diagonal syndrome weights `sum_j \|coefficient_j\|^2` | Nonunitary amplitude damping `A0=diag(1,3/5)`, `A1=[0,4/5;0,0]`; full entangled-reference channel and classical syndrome output |

IBM-056 SHA-256: `acacc51286660e12f389aa3282a0ca7a3aa46fb7405dbd9797c5c94b55825f5d`.
IBM-058 SHA-256: `327f3f6dc910b571e1d2bdd18028446a7b9e38855d030f3c37298bf174ea97cc`.
Original notebook equations are mathematical prose, not executable API calls.
All API spellings and diagnostic inputs here are disclosed adaptations.

The original IBM-056 construction uses nine Shor qubits and eight syndrome bits.
**This audit does not execute that original instrument.** The released instrument
limit is dimension 64, so instead the finite channel witness uses commuting
checks `ZZI,XXX`, on three physical qubits with an error at the first physical
site only. Its logical columns are `(000+111)/sqrt(2)` and
`(001+110)/sqrt(2)`. This is not a code correcting unknown errors at arbitrary
sites. Joint projectors `(III+s ZZI)(III+t XXX)/4` each have rank two.
The I/X/Y/Z sectors have `(s,t)=(++),(-+),(--),(+-)`. All tensor factors are
explicit: syndrome first when present, then reference, then the three code qubits.
The maximally entangled encoded input is
`(|0000>+|0111>+|1001>+|1110>)/2` in reference/code order.

## Independent expectations

The oracle uses plain Python complex arithmetic, with explicit 2-by-2 Pauli
matrices and basis vectors. It does not ask the calculator to verify its own
expected answer. Every matrix entry, dimension and complex phase is compared;
all successful outputs must report `approximate=false`. Numeric interpretation
of exact printed radicals uses tolerance `1e-12`; this is not an approximate
evaluation-mode claim or a symbolic proof for arbitrary parameters.

For ZZ, `(00+i11+2*01+2i10)/sqrt(10)` has probabilities `1/5,4/5`.
The conditional density matrices have nonzero off-diagonal entries `-i/2,i/2`
within the corresponding two-dimensional sector. Separate even and odd Bell
states remain unchanged. Splitting the projectors into rank-one Kraus matrices
would destroy those entries and fail these tests.

For the known-site code, orthogonal error images of both logical columns give
`P_s E_t V = delta_st E_t V`. This identity explains the oracle, but testing
does not stop at projector action. The full noisy reference density, four
probabilities, four conditional density matrices, four corrected poststates,
nonselective discretized channel and nonselective corrected channel are executed.
The unitary coefficients are `(1,i,i,i)/2`, with weights `(1,1,1,1)/4`.
For damping, `A0=(4/5)I+(1/5)Z` and `A1=(2/5)X+(2i/5)Y`, so the independently
derived weights are `(16,4,4,1)/25`. Coherences between different error sectors
vanish after syndrome measurement; reference/logical coherences remain.

Recovery Kraus operators are `C_s P_s A_j`, in that order, with corrections
`I,X,Y,Z` on the first physical site. The reference is untouched. Comparing the
full encoded maximally entangled density checks the restricted logical channel,
including its off-diagonal action; basis-state recovery alone would not do so.
Rectangular Kraus operators `|s> tensor (I_ref tensor C_s P_s A_j)` also produce
the full 64-by-64 output `diag(weights) tensor rho_ref,code`. Every entry is
checked, including off-block zeros. Before measurement, coherent syndrome tagging
and controlled recovery are separately compared as full 64-component vectors:
the corrected vector is `(1,i,i,i)/2 tensor |Phi_encoded>`. No phase quotient
is applied to this comparison.

Unknown completeness and an unknown selector remain pending through Copy.
Concrete invalid substitutions, incomplete instruments, unnormalized/negative
states, dimension mismatch and zero-probability conditioning must return exit 2
and the specific diagnostic. These conditions are not assumed valid.

## Evidence, failure history and reproduction

External evidence is at `F:/src/libqalculate/cleanup-audit/dev11d-20261102/`.
`validated/` records 60/60 passing fresh worker cases. The existing DEV-09 suite
passes 214 checks, including its still-pending fourth tetrahedral `|i>` poststate.
`gui/` records 35 actual packaged GUI checks: Calculate and Copy buttons,
four complete copied-result comparisons, re-entry, session Save/Open through
application serialization, invalid-input recovery and five inspected captures.
The 64-by-1 vector scrolls; the 16-by-16 density uses the textual fallback. Full
content is checked through Copy, not inferred from the visible viewport.
No file-dialog interaction is claimed.

Initial harness runs are retained: `baseline/` used an unsupported `diag`
spelling (34/39); `corrected-harness/` incorrectly expected a one-row matrix
instead of the canonical vector (34/39); `expanded/` used `s` as an unknown
selector but it was not treated as the intended unknown scalar (56/57).
Using the established unknown `x` resolves that harness issue. These are not
product gaps or red/green product fixes. Initial standalone worker invocations
also omitted the packaged data environment and failed before evaluation; the
runner sets it explicitly. No actual product failure was found in this scope.

```powershell
python docs/learning-evidence/dev11/instrument-audit.py --worker F:/src/libqalculate/dist/releases/214e6866/QuantumStudio/quantum-worker.exe --sources F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/sources --output F:/src/libqalculate/cleanup-audit/dev11d-fresh
./windows/test-instrument-recovery-gui.ps1 -Distribution F:/src/libqalculate/dist/releases/214e6866/QuantumStudio -Evidence F:/src/libqalculate/cleanup-audit/dev11d-gui-fresh -Fixtures F:/src/libqalculate/cleanup-audit/dev11d-fresh/results.json
```

Use a new output directory. A different intended integration worker requires an
explicit `--worker-sha256` override, and must have its own recorded revision and
fresh results. Portable raw results and the summary accompany this document.

## Integration and limits

The lead owns shared build lists, central checklist integration, merges and the
combined release. This branch changes only audit fixtures, documentation and a
separate GUI test driver. No QuantumMeasurement, QuantumInstruments, notation or
shared checklist edits; no release publication. Keep the isolated checkout until
integration or verified recovery; evidence remains outside it.

Proposed checklist update: **DEV-11 remains Partial. DEV-11d now has finite
released-capability evidence for both rank-two ZZ outcomes, coherent joint
syndrome recovery, and unitary/nonunitary discretization with an entangled
reference in a disclosed known-site three-qubit adaptation. Original nine-qubit
Shor instrument execution and whole-lesson coverage remain open. DEV-09's fourth
tetrahedral conditional state remains separately unresolved.**
