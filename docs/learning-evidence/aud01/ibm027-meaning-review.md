# IBM-027 lesson meaning review

Reviewed the 97 inline and display expressions in the pinned phase-estimation problem notebook at revision `d2f891c9`. The [per-expression ledger](ibm027-lesson-results.json) records the input, expected reading, actual display, Copy text, session context and evaluation revision. The notebook has one Markdown cell and zero code cells. Row numbers below are the M identifiers in the [source inventory](ibm027-inventory.json). The [latest Windows replay](ibm027-hermitian.json) used Matrix dimensions for M012, Set notation for M063, and Quantum notation for the remaining expressions. Its successful save, reopen and Copy checks apply to all 97 rows. The following review compares those results with the surrounding lesson text.

| Rows | Meaning in the lesson | Observed result and evidence |
| --- | --- | --- |
| 001, 011, 018, 025, 049 | Arbitrary normal matrix M | Preserved as the symbol M. |
| 002 | M commutes with its adjoint | Preserved both products. [Six matrix controls](ibm027-normality.json) distinguish normal from nonnormal matrices. |
| 003, 054, 068, 077, 081 | Unitary operator U | Preserved as U. Unitarity is a premise in the prose. |
| 004 | Both products of a unitary with its adjoint equal the identity of the same dimension | The unsized identity now follows the adjoint product. [Unitarity controls](ibm027-unitarity.json) accept two-, three- and four-dimensional unitary matrices and reject a shear and both rectangular isometries tested. |
| 005, 006, 007 | Arbitrary Hermitian H and the equality of both products with its square | A session declaration binds H as an N-by-N Hermitian matrix in these three expressions. The equality holds for distinct two- and three-dimensional examples. Substituting a complex symmetric matrix with the wrong adjoint raises a property error. [Hermitian controls](ibm027-hermitian.json). |
| 008, 009, 010 | Nonnormal example and its two different products | The input gives the upper triangular matrix with a single 1. Both explicit product identities return true. Their right-hand projectors select different basis vectors. |
| 012 | Matrix dimensions, N rows by N columns | Select Matrix dimensions. Both counts remain N, and assigning N updates both. [Ordered dimension checks](ibm027-dimensions.json). |
| 013, 046 | Dimension N | Preserved as N. |
| 014, 022, 037 | Set of eigenvectors, including the explicit two-vector case | Indexed or explicit ket set. [Set and substitution checks](ibm027-ketsets.json). |
| 015, 035, 047 | Ordered list of eigenvalues | The result keeps the indexed sequence and its bound N. [List checks](ibm027-indexed-lists.json). |
| 016, 017 | Spectral expansion with coefficient-weighted eigenprojectors | Both notations give the same spectral sum. [Matrix checks](ibm027-spectral.json). |
| 019, 029, 041, 048, 056 | References to numbered equations | The worker returns the numeral 1 or 2. These occurrences are references in the lesson, with no independent calculation to verify. |
| 020, 021, 023 | Eigenvector equation, range of j and derivation of the selected eigenpair | Displays the eigenvector equation and bounded index membership. M023 selects the corresponding weight and vector after substitution. [Eigenpair controls](ibm027-spectral-index.json). |
| 024, 030, 031 | Individually named eigenvalues | Preserves the subscript on each scalar label. |
| 026, 032, 033 | Individually named eigenvectors | Preserves each named ket and subscript. |
| 027, 028, 036, 038 | Two-dimensional identity, including expansions in computational and sign bases | M028 displays the identity matrix. All three explicit equalities return true. |
| 034 | Four simultaneous eigenvalue and eigenvector assignments | Conjunction of the four relations. [All 16 truth assignments](ibm027-declarations.json). |
| 039, 040 | The Hadamard gate and its explicit matrix | The defining equality returns true and H displays the normalized Hadamard matrix. |
| 042, 043, 044, 045 | Hadamard eigendecomposition, real angle state, its two specializations and projector difference | Preserves the equations and exact radicals. [Hadamard substitution controls](ibm027-hadamard.json). |
| 050, 053, 069, 071 | Eigenvalue lambda | Preserved as a scalar symbol. |
| 051, 055, 058, 064, 067, 070, 079, 080 | State or eigenvector psi | Preserved as a named ket. |
| 052, 083 | Eigenpair relation with an eigenvalue or its exponential phase | Displays the operator acting on the ket and the corresponding scalar multiple. [Phase relation checks](ibm027-phase-relation.json). |
| 057, 059, 060 | Norm preservation, nonzero norm and unit modulus | Displays the norm equality chain, nonzero condition and modulus equality. |
| 061, 062, 063 | Complex unit circle defined by a membership predicate, and its two names | The defining equality is true. Both names denote the same set with the recorded notation choice. [Circle controls](ibm027-circle-mode.json). |
| 065, 066, 076, 078 | Number of qubits n | Preserved as n. |
| 072 | Eigenvalue in terms of a full turn scaled by theta | Displays lambda equal to the complex exponential. [Phase checks](ibm027-phase-relation.json). |
| 073, 075, 084, 085, 092 | Phase parameter theta | Preserved as a scalar symbol. |
| 074, 082 | Theta lies in the half-open unit interval | The inequality and membership forms retain the endpoint conventions. [Boundary checks](ibm027-phase-domain.json). |
| 086, 087, 090, 091, 095, 097 | Specified phase values in the discussion of wraparound | Preserves each equality, including the exact rational value 999/1000. |
| 088, 089 | The complex exponential is one at both ends of a full turn | Both explicit equalities return true. |
| 093, 094, 096 | Values near the cut and the example distance | Returns 1, 0 and the exact rational 1/1000. |

Review of PR #530 identified three remaining calculation issues on c51b3d19.

- M004 accepts a three-dimensional identity with the original grouping. Parenthesizing the adjoint product or the unsized identity changes the result to false.
- M020, M024 and M026 retain the literal labels λ_j and ψ_j when the learner assigns j = 2. M023 handles this substitution in the full spectral identity.
- M043 evaluates correctly if the real angle state family is loaded first. Substituting θ = π/8, copying the result and then loading the same family leaves θ unbound on the left.

Integration and release verification remain pending.
