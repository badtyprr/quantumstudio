# DEV-11 primary-source example inventory

Base: `0fed41cb5637c578737278bf13f59590a56d6cf4`. Retrieved 2026-11-01. All 16 Foundations rows IBM-053–068 are inventoried; zero whole rows are certified. See [README.md](README.md) for the 286 fixtures, [source-manifest.json](source-manifest.json) for official URLs, retrieval timestamps and hashes, and [source-map.json](source-map.json) for exact cell IDs, lines, sections, equations, image references and fixture mappings.

Every notebook has zero code cells: probes adapt mathematical notation, not original IBM executable code. Original notebook snapshots stay outside the clone. Web text was available, but direct HTML downloads returned 403; official notebooks all succeeded. Videos, slides and visual diagram topology remain unaudited. Linked resources with retrieval failures are explicitly identified below.

Pauli strings abbreviate tensor products left to right, with the leftmost qubit most significant in these fixtures. Syndrome 0 means eigenvalue +1; 1 means −1. Full logical checks require every encoded column, relative phase and leakage. Zero syndrome alone does not establish recovery. Derived enumerations are adaptations. Existing stabilizer/CSS APIs are present and exercised.

## [IBM-053](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/introduction)

Introduction to correcting quantum errors: contextual Shor/discretization roadmap. No additional explicit generator calculation in the body. Lesson video and slides remain unaudited.

## [IBM-054](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/repetition-codes)

**Examples:** “Classical encoding and decoding”: 0 → 000, 1 → 111 and majority decoding of eight strings. “Noise reduction for the binary symmetric channel”: 3p² − 2p³. “Encoding qubits”: α|0⟩ + β|1⟩ → α|000⟩ + β|111⟩. “Bit-flip errors”: III/00, IIX/01, IXI/11, XII/10, with the same Pauli as correction. “Phase-flip errors”: IZI changes relative sign despite syndrome 00; error probability 3p(1−p)²+p³. “Modified repetition code for phase-flip errors”: plus/minus encoding and phase recovery.

**Audit:** algebraic encoding/recovery/noise adaptations tested. Exact encoder/parity circuits, ancilla branches, import/export, full classical majority decoding and noisy execution remain open.

## [IBM-055](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/shor-code)

**Examples:** “Code description”: Shor |0L⟩ and |1L⟩ = (|000⟩ ± |111⟩)^⊗3 / √8. “Errors and CNOT gates”: six X/Z propagation identities, covered algebraically by the expanded 16-Pauli conjugation table under IBM-060. “Correcting bit-flip errors”: one X per block. “Correcting phase-flip errors”: Z positions within a block are degenerate; the middle block has outer syndrome 11; any Z in that block corrects. “Simultaneous bit- and phase-flip errors”: one X and one Z, possibly at distinct positions. “Error reduction for random errors”: source noise reduction discussion.

**Audit:** related Shor generators/recovery are tested under IBM-060; there is no distinct IBM-055 execution row. Remaining: full X/Z position cross-product, multiple-block X errors, noise reduction, circuit diagrams and measurement branches. The 27 single-Pauli errors do not exhaust this larger source-correctable family. Preserve the observed Shor timeouts despite the reassociation workaround.

## [IBM-056](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/discretization-of-errors)

**Examples:** “Unitary qubit errors”: U = αI+βX+γY+δZ, Y=iXZ, syndrome probabilities from coefficient modulus-squares, and corrected joint state ξ ⊗ |ψ⟩⟨ψ|. “Arbitrary qubit errors”: Kraus expansion and probabilities summed over Kraus indices. “Generalization”: multi-qubit Pauli products.

**Audit:** one explicit unitary expansion is tested. Full instrument/channel recovery, discard/reset, and entangled-reference behavior remain unaudited and overlap DEV-09. Finite Pauli tests do not establish general recovery.

## [IBM-057](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/introduction)

Stabilizer-formalism introduction: roadmap, no additional concrete generator example. Video/slides unaudited. The [Box slide URL](https://ibm.box.com/public/static/umposbds8d27cv8rnpsayyaj1k2aw88o.pdf) redirected to an endpoint inaccessible through the web retrieval route. This is an access-route failure, not a claim that the slides do not exist.

## [IBM-058](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/pauli-operations-and-observables)

**Examples:** “Properties of Pauli matrices”: squares I, XY=iZ, YZ=iX, ZX=iY, with reversed products changing sign. “Pauli operations on multiple qubits”: IIIIIIIII, XXIIIIIII, XYZIIIXYZ have weights 0, 2, 6. “Pauli operations as generators”: ⟨X,Y,Z⟩ has 16 matrices; ⟨X,Z⟩ has 8; ⟨XX,ZZ⟩={II,XX,ZZ,−YY}. “Hermitian matrix observables” / “Measurements from Pauli operations”: spectral projectors; ZZ has two rank-two outcomes and must preserve Bell coherence. “Nondestructive implementation through phase estimation”: single-P, three-factor, ZZ and simplified parity diagrams.

**Audit:** finite multiplication and Bell projector action pass. Full group enumeration, general observable decomposition and circuit/instrument semantics remain open; coordinate the latter with DEV-09. Variadic tensor rejection is an invented convenience spelling, not original source code.

## [IBM-059](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/repetition-code-revisited)

**Examples:** “Pauli observables for the repetition code”: generators ZZI, IZZ; group III, ZZI, ZIZ, IZZ; code span |000⟩, |111⟩; alternate ZIZ generator. “Error detection”: columns III, XII, IXI, IIX yield sign rows (+,−,−,+), (+,+,−,−), or bit syndromes 00, 10, 11, 01. “Syndromes”: four orthogonal dimension-two sectors; all 64 Paulis partition evenly; XXX acts as logical X.

**Audit:** all source syndrome columns and the entire 64-Pauli partition pass, with 16 Paulis per sector. Full logical XXX and the adapted ZII witness pass. Actual extraction instrument, full sector-projector behavior and diagram equivalence remain open.

## [IBM-060](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes)

**Examples:** “Definition of stabilizer codes”: commutation, independence and exclusion of −I. “Examples”: repetition, phase repetition, Shor, Steane, five-qubit (XZZXI, IXZZX, XIXZZ, ZXIXZ), and Bell (ZZ,XX) codes. “Code space dimension”: projector product equals group average, rank 2^(n−r). “Clifford operations”: signed H/S conjugations and the 15 nonidentity CNOT conjugations. “Encoders for stabilizer codes”: Clifford isometry and pictured Steane encoder. “Error detection cases”: stabilizer, nontrivial normalizer, detected error. “Distance of a stabilizer code”: Steane weight-at-most-two exclusion and IIIIXXX / IIIIZZZ witnesses. “Correcting errors”: minimum-weight representatives and CE proportional to a stabilizer.

**Audit:** complete single-Pauli syndrome/recovery tables, parameters, Clifford conjugations and invalid-input checks are recorded. Exact pictured Steane encoder, generic synthesis, parameterized proofs and arbitrary-error recovery remain uncertified. The Steane CSS encoder is an algebraic isometry comparison, not the pictured circuit. The SVG fetch produced a web cache miss; visual topology was not independently inspected. Existing syndrome/correction APIs work; Shor multiplication cost is a separate performance issue.

## [IBM-061](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/introduction)

Quantum-code-constructions introduction: CSS, toric, surface and color-code roadmap; no new arithmetic example. Video/slides unaudited.

## [IBM-062](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/css-codes)

**Examples:** “Classical linear codes”: repetition XOR closure and 16 Hamming codewords. “Describing classical linear codes”: generators 1111000, 0110100, 1010010, 1100001; parity checks 1111000, 1100110, 1010101. “Definition of CSS codes”: Bell, Steane and Shor X/Z checks with vanishing cross binary inner products. “Error detection and correction”: independent X/Z decoding. “Code spaces of CSS codes”: dual containment, uniform coset states, Hadamard-dual description and explicit Steane encoding. The dual set is {0000000,0011110,0101101,0110011,1001011,1010101,1100110,1111000}; logical zero is uniform on this set and logical one on the complementary Hamming coset.

**Audit:** both Steane vectors and the full CSS encoder pass. Full classical closure, generic families, the Hadamard-dual construction and all combined-error recoveries remain uncertified by these finite checks.

## [IBM-063](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/toric-code)

**Examples:** “Toric code description”: periodic L-by-L geometry with 2L² edge qubits, weight-four Z plaquettes and X stars, two dependencies, rank 2L²−2 and two logical qubits. The illustration uses L=9. “Detecting errors”: single-X endpoints, open chains, contractible stabilizer loops, noncontractible logical loops and distance L. “Correcting errors”: pairing endpoints, shortest paths and minimum-weight perfect matching.

**Audit:** geometry-derived diagrams, logical matrices and matching decoder remain unaudited. The 18-qubit rejection is a capacity sentinel for adapted L=3, not execution of the original L=9 example or proof that every alternative runtime route is absent.

## [IBM-064](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/other-code-families)

**Examples:** “Surface codes”: rough/smooth boundaries, one logical qubit, a left/right X chain and top/bottom Z chain; a rotated distance-five diagram with weight-two and weight-four checks. “Color codes”: Steane face geometry and Q6…Q0 ordering, paired X/Z faces, and a 19-vertex [[19,1,5]] example. “Other codes / Example: The gross code”: [[144,12,12]], weight-six stabilizer generators, compared with the toric code. The Error Correction Zoo link is an onward discovery resource, not an audited inventory of every external code family.

**Audit:** diagram-derived generators, boundaries, rank/distance and full logical actions remain unaudited. Reusing Steane matrices does not certify larger examples. No gross-code construction or decoder has been executed.

## [IBM-065](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/introduction)

Fault-tolerant-quantum-computing introduction: noisy correction, protected computation, threshold and magic-state roadmap. No new explicit generator table. Media and noisy gadgets remain unaudited.

## [IBM-066](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/approach-to-fault-tolerance)

**Examples:** opening and “Fault-tolerant circuit implementations”: teleportation replaced by encoded gadgets with inserted correction. Five-wire blocks are illustrative, not a fully specified five-qubit implementation. “Noise models”: independent stochastic faults, broader correlated models and the reliable-classical-processing assumption.

**Audit:** concrete gadgets, fault locations, circuit transcription and noisy execution remain unaudited. A conceptual diagram alone cannot establish a missing product operation.

## [IBM-067](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/controlling-error-propagation)

**Examples:** opening CNOT error propagation and cascades. “Examples of transversal gate implementations”: CSS bitwise CNOT; Shor logical X=ZIIZIIZII and logical Z=XXXIIIIII; Steane H^⊗7 implements logical H and (S†)^⊗7 implements logical S. “Error propagation for transversal gadgets” and “Non-universality of transversal gates” describe guarantees and limitations. “Implementing gates with magic states”: T-state injection with two equiprobable branches and conditional S; an S-state alternative uses conditional Z. “Fault-tolerant gadgets from magic states”: encoded injection/measurement, classical postprocessing and distillation. “Fault-tolerant error correction”: protected correction gadgets.

**Audit:** single-CNOT algebra and complete Shor/Steane single-block logical actions pass; cascades are not separately certified. Two-Steane-block CNOT requires all four encoded columns and remains open. Injection, noisy gadgets and transversal fault propagation remain unaudited, with measurement work overlapping DEV-09. The 14-qubit constructor sentinel does not establish that every circuit route is absent.

## [IBM-068](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/threshold-theorem)

**Examples:** “Threshold theorem”: concatenation recurrence p → Cp² → (Cp)³p → (Cp)⁷p, generally (Cp)^(2^k−1)p under p<1/C. The source intentionally omits formal noise-model details. Post-course survey is noncomputational content.

**Audit:** recurrence execution, proof and noisy-gadget simulation remain unaudited. A scalar recurrence check would not certify a physical threshold; no threshold estimate is validated by this audit.

## Queue and integration

Use [README.md](README.md)'s ranked proposals: confirmed Shor multiplication cost; compact representations and two-block execution; DEV-09 instrument integration; original circuits; remaining geometric and gadget families. Keep unsupported adaptation syntax, deliberate capacity limits, incorrect results and supported operations separate. There is no confirmed wrong numerical result in completed comparisons. No implementation, central-checklist, merge or release change is included. All 16 rows remain open.

This is an inventory of source example families and explicit remaining audit surfaces, not a proof audit of every equation. The machine-readable source map additionally locates every parsed display equation and linked image, including unaudited ones. Fixtures contain independently expected and actual results with binary provenance. In particular, the single-Pauli Shor audit must not be substituted for the larger source-correctable error family.
