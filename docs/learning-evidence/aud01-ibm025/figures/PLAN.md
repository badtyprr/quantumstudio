# IBM025 diagram audit plan — before media inspection

Assigned external source-only scope, base78bf6cf7fb6ca52c884320cc7ec2a53958627109. Notebook SHA256 ec06bb65c2b394c9d5053a3dcbcf9407972a8fdca1fed4f0de8c357e91a72df7 at Qiskit/documentation a500b17f8b1f156a6bba42ab11f90f3104cad6d4; cell dee8cce0. Coordinator-owned acquisition directory: coordinator-20261104/ibm025-svg-acquisition-20261105. Acquisition digest not yet supplied: do not fetch duplicate media or render unbound files.

## Original media inventory and intended inspection

| Original basename | Cell Unicode interval | Inspection obligation |
| --- | --- | --- |
| Toffoli-gate.svg | 1406..1531 | Identify controls/target, original labels and source little-endian order; join to original8x8 matrix. |
| build-Toffoli.svg | 2497..2645 | Transcribe actual ordered H,T,T-dagger,CNOT wires/gates, including parallel gates and controls; independently verify all eight full matrix columns, with phase equality stated explicitly. Do not substitute a familiar decomposition from memory. |
| AND-OR-FANOUT-with-Toffoli.svg | 2927..3100 | Read actual input/workspace/output/leftover wires, NOT placements and ancilla initialization; distinguish displayed leftover states from an authored construction that restores inputs. |
| reversible-circuit-simulation.svg | 4915..5074 | Read input/output grouping, workspace size and f/g register ordering; schematic/proof obligation only unless a finite instantiation is explicitly authored. |
| swap.svg | 5648..5777 | Read every CNOT orientation and compare resulting map on all four basis inputs with SWAP. |
| garbage-free-computation.svg | 7925..8074 | Read compute/copy/uncompute order, register sizes, zeros and final garbage; no assumption that discarding garbage equals reversing it. |
| simulation-as-query-gate.svg | 8156..8307 | Read query register ordering and arbitrary y vs zero initialization; join symbolic display to shown workspace subspace. |
| fully-reversible-simulation.svg | 11778..11942 | Read query f/f-inverse ordering and swaps, retained workspace and output registers; preserve requirement for an inverse implementation. |

## Rendering and provenance

Before rendering, verify exact acquisition manifest SHA, revision, notebook SHA and eight original asset size/SHA/Git-blob bindings. Derive PNGs with the installed Sharp/librsvg static renderer,180dpi white background, recording renderer versions/argv and all PNG hashes. Reject scripts, event handlers, foreign objects, entities/DOCTYPE, CSS imports and nonfragment external references before passing SVG buffers to the renderer. Preserve originals unchanged. Inspect all eight PNGs directly in small groups, record any ambiguity/clipping and join each to source prose/formulas. Renderer preparation must remain fail-closed until acquisition digest is bound.

## Freeze semantic checks after inspection, before execution

Current status: no diagram inspected, no gate transcription established, no checker executed. After direct inspection, append an explicit frozen table of test groups, exact case counts, input enumeration and independent expectations before writing/running check.py. Where a diagram is generic rather than numerical, retain it as a schematic observation; any finite instance must be disclosed as authored. The existing520 IBM025 source references are separate evidence and do not verify these diagrams.

Prefer exact arithmetic for gates with entries in Q(sqrt(2),i), or an independently specified numerical full-matrix comparison if exact representation is impractical. State absolute numerical tolerance separately from exact Boolean/permutation identities. For the pictured Toffoli decomposition, compare full matrix entries including relative/global phase; do not replace full equality with matching output probabilities. Define the phase policy before executing the checker. No broad theorem, arbitrary family, asymptotic cost, native calculator/Copy, SDK, GUI or whole-lesson acceptance follows.

Independent Standards and Spec reviews required after artifacts/checks are finalized. Report exact original and derived hashes, source joins, successful finite checks, unresolved symbolic/proof obligations, and any reproduced source discrepancy to the coordinator. No shared product code or central checklist edits.

## Frozen post-inspection checker plan — no checker executed yet

Acquisition bound to SHA2566377ceb37b0e164ac2c89905360ca3946bcbd00e9e6ae2cec0314b98cd9e8ad7. All eight final PNGs directly inspected, labels/wires readable without observed clipping. `render-manifest.json` binds original SVG and PNG hashes. The preceding pre-inspection status describes the earlier phase; this section freezes the subsequent semantic plan before check.py exists or runs.

Use254exact outer cases, no numerical tolerance:

1. Toffoli-gate.svg:8basis inputs with top-to-bottom wires a,b,c assigned bit0,1,2. Outputs a,b,c XOR ab; compare all full columns to the notebook's original8x8 matrix.
2. build-Toffoli.svg:8full output columns (64amplitudes), exact equality including global phase to that same independently transcribed original matrix. Left-to-right transcription, wire0top: H2,CNOT1→2,Tdagger2,CNOT0→2,T2,CNOT1→2,Tdagger2,CNOT0→2,T1,T2,CNOT0→1,T0,Tdagger1,H2,CNOT0→1. Simultaneous disjoint gates T1/T2 and T0/Tdagger1/H2 may be serialized in this order without changing the circuit. Exactly15gates. Represent amplitudes in Q[z]/(z^4+1), z=exp(iπ/4), as four rational coefficients; T multiplies byz, Tdagger by−z^3, H by(z−z^3)/2 times the sum/difference. Independent expected columns contain only0/1. No approximate complex values or phase normalization allowed.
3. AND-OR-FANOUT-with-Toffoli.svg:4AND,4OR,2FANOUT inputs, workspace initially0. AND preserves(a,b) and computes AND in bit2. OR applies NOT to BOTH input controls, Toffoli, NOT to target; its full outputs are(¬a,¬b,a OR b), matching printed leftover labels. Do NOT restore controls as in the earlier authored reference. FANOUT CNOT top→bottom maps(a,0) to(a,a); no arbitrary-state cloning claim.
4. swap.svg:4basis inputs, CNOT0→1,CNOT1→0,CNOT0→1. Compare complete outputs with swapped bits, not with the earlier reference's result alone.
5. garbage-free-computation.svg and simulation-as-query-gate.svg:128authored finite instances, not literal numerical diagrams. All16truth tables f:{0,1}²→{0,1},4x,2y; n2,k1,m1. Match pictured output ordering of R by computing f into bit2 then SWAP0↔2, so f occupies top bit0 and garbage occupies bits1/2. Copy bit0 into independent y bit3; reverse R by SWAP0↔2 then the same controlled XOR into bit2. Expect final x in bits0/1, workspace bit2zero, y XOR f(x) in bit3. Record each stage. This uses an explicitly authored reversible implementation of R and does not verify a general construction/cost bound. reversible-circuit-simulation.svg remains a symbolic grouping/cost observation, not a literal wire-count contract.
6. fully-reversible-simulation.svg:96authored instances,24permutations f on four two-bit strings and4x. Match actual pictured order: Q_f computes high=f(low) from low=x/high0; SWAP both two-bit registers; Q_f-inverse then XORs f-inverse(low) into high. Expect low=f(x), high0. Treat internal k-workspace as an ideal clean query interface; no gate-level internal-workspace implementation or general inverse-discovery algorithm is claimed. This pictured order differs from the earlier authored source reference that erased before swapping, though their chosen zero-auxiliary outputs coincide.

The four general register diagrams depict symbolic register bundles; the number of illustrative horizontal strokes is not assigned as n,k,m. R and Rdagger act only on x/workspace; the y target passes outside them. Q has final labels x,0^k,y XOR f(x). The last diagram swaps the upper/lower n-bit registers between Q_f and Q_f-inverse while the middle workspace stays in place. Only the above finite authored instances are calculated; general uncomputation/unitarity/asymptotic propositions remain source proof obligations.
