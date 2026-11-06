# IBM025 source inventory and frozen finite reference plan

Assigned base `78bf6cf7fb6ca52c884320cc7ec2a53958627109`. External source/reference work only; no native calculator, SDK, GUI, shared-code edits, media acquisition or rendering. This is not whole-lesson completion or a new feature claim.

## Source provenance

[source.ipynb](source.ipynb) is an exact-byte copy of the notebook lane's original. Its 14,004 bytes, SHA256 `ec06bb65c2b394c9d5053a3dcbcf9407972a8fdca1fed4f0de8c357e91a72df7`, and Git blob `7060659cf1b57309a9119cb95a46ae2a7b9e0b09` were verified against the acquisition manifest. [manifest.json](manifest.json) preserves the complete upstream entry and manifest hash. The [official immutable notebook](https://raw.githubusercontent.com/Qiskit/documentation/a500b17f8b1f156a6bba42ab11f90f3104cad6d4/learning/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/simulating-classical-computations.ipynb) is at revision `a500b17f8b1f156a6bba42ab11f90f3104cad6d4`; historical baseline equivalence is not claimed.

One Markdown cell, ID `dee8cce0`, source SHA256 `6d753b185d0f6d11c946228e4dd37ad17614e7df88fed5dda3a2422a76defa9c`, contains 91 math occurrences (4 display, 87 inline), eight image/diagram references, seven headings, zero code cells and zero textual Figure blocks. [inventory.json](inventory.json) preserves the complete cell and per-occurrence original strings, character offsets and hashes. All source occurrences remain unverified for native/media acceptance. [media-locators.json](media-locators.json) preserves locators only. There is no original executable notebook code or SDK dependency in this body.

All offsets below are zero-based half-open Unicode character offsets in concatenated cell source; hashes are UTF-8 without newline normalization.

## Original claims and interpretation

The explicit Toffoli matrix [1727,2023) swaps basis indices 3 and 7, fixing the others. With source Qiskit ordering, the top two wires are low-significance controls and the bottom wire is the high-significance target: state index is 4t+2b+a. The matrix is an original literal; exhaustive basis enumeration is an authored finite check of it.

The Boolean simulation section [2647,4084) uses fresh zero workspace for AND, OR and FANOUT and retains unused input/garbage bits. FANOUT is copying computational basis information through CNOT, not cloning arbitrary unknown quantum states. Generic claims about simulating every Boolean circuit require construction/proof, not a few truth tables.

The function-domain display is [4440,4475). The garbage-cleaning section [6356,9488) describes compute, copy output, then reverse the computation. The explicit query action [9826,9958) preserves input x and zero workspace while XORing f(x) into y. This is a statement on the zero-workspace subspace; it does not specify every action on nonzero workspace. Ket order is y,workspace,x (x least significant). Reversing a quantum circuit here concerns the unitary reversible R, not arbitrary destructive measurement/reset channels. CNOT copying in a superposition can create entanglement; discarding garbage is not interchangeable with uncomputing it.

The invertible-function section [9488,11942) states U|x>=|f(x)> at [10659,10703). It explicitly requires an implementation of both f and its inverse; this is not an algorithm for discovering an inverse efficiently. On an equal finite domain/codomain, bijectivity makes the matrix a permutation matrix. Noninjective deterministic replacement maps send distinct orthogonal columns to the same basis vector and are not unitary. General workspace bounds and O(t) costs are proof/model obligations. In particular, counting output-copy and rearrangement costs must respect the source circuit/wire model; arithmetic-only checks do not prove asymptotic overhead.

## Media obligations, all uninspected

| Offset | Diagram locator basename |
|---|---|
| [1406,1531) | Toffoli-gate.svg |
| [2497,2645) | build-Toffoli.svg |
| [2927,3100) | AND-OR-FANOUT-with-Toffoli.svg |
| [4915,5074) | reversible-circuit-simulation.svg |
| [5648,5777) | swap.svg |
| [7925,8074) | garbage-free-computation.svg |
| [8156,8307) | simulation-as-query-gate.svg |
| [11778,11942) | fully-reversible-simulation.svg |

No diagram gate sequence has been transcribed or verified. Especially the H/T/T-dagger/CNOT Toffoli decomposition remains an uninspected diagram obligation. Authored finite gate compositions below must not be attributed to those unseen images.

## Frozen reference plan (recorded before execution)

Use only Python standard-library exact integers, finite tuples and lists. Check notebook and this pre-execution plan hash before the run and record them in results. No native or SDK operation. **520 finite cases**, grouped as follows; counts refer to outer cases, not every internal comparison:

1. Eight Toffoli basis inputs: parse the original displayed 8x8 matrix from pinned cell text, compare every complete output column to independently evaluated controlled target flip. Also check matrix entries/dimensions and involution. Original matrix; authored enumeration.
2. Twelve Boolean cases: all four AND inputs, four OR inputs, two NOT inputs and two FANOUT inputs. Author a Toffoli AND and De Morgan OR composition, restoring controls, and a CNOT FANOUT on zero target; compare with Boolean truth definitions. These are authored finite routes, not verified source diagram transcriptions.
3. Four SWAP basis cases: authored three alternating CNOTs versus exchanged two-bit tuple. No diagram acceptance follows.
4. 128 clean-query cases: all 16 authored Boolean functions f:{0,1}^2->{0,1}, all four x and both y, workspace initially zero. Use authored R:x,w -> x,w XOR f(x), then copy workspace to y, then inverse R. Independently expect index (y XOR f(x))*8+x in a four-qubit state, with workspace bit2 zero. Keep full stage indices.
5. Sixteen coherent checks, one for each preceding f: start with signed integer coefficients [1,-1,2,-2,3,-3,4,-4] over zero-workspace indices y*8+x in y-major order. Apply three explicit permutation stages to the full 16-entry vector; compare to a direct query permutation and check all nonzero-workspace amplitudes vanish. Squared norm is 60; coefficients may be read as exact amplitudes divided by sqrt(60). No floating-point tolerance. This tests sign preservation in these finite reference constructions, not general interference theorems.
6. Ninety-six invertible cases: all 24 permutations on four two-bit strings and all four x. With two registers and zero auxiliary input, compute f into the auxiliary, XOR f-inverse(auxiliary) into the original input, then SWAP registers. Expect low register f(x), upper register zero. These ideal-query compositions omit internal workspace implementations; that omission is disclosed rather than represented as a general circuit construction.
7. 256 deterministic replacement maps on four strings: construct each full 4x4 column map and its integer Gram matrix; compare identity exactly and independently compare distinct output count with four. Expect 24 unitary permutation maps and 232 nonunitary maps. This is an authored finite enumeration, not a proof of arbitrary dimension.

The 16 truth tables, four-string permutations/maps and signed coherent coefficients are authored adaptations; none are original lesson input examples. Only the explicit Toffoli matrix is directly transcribed from an original finite numerical display. The remaining three original displays are symbolic/domain statements whose literal native routes remain untested. Passing the planned references does not establish native notation, Copy/re-entry, saved sessions, actual GUI behavior, diagram correctness, arbitrary families, complexity bounds or whole-source completion. Independent reviews are pending.
