# DEV-03: declared orthonormal bases

Acceptance: declare a named basis and dimension; reduce inner products to Kronecker delta and complete projector sums to identity; leave unknown bases unresolved; preserve declarations through save/load and copy. Symbolic families and a dedicated editor are included in this scope. Release verification remains pending until the reviewed implementation is merged and packaged.

## Primary sources

- [IBM: inner products and projections, orthogonal and orthonormal sets](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/inner-products-and-projections#orthogonal-and-orthonormal-sets): orthonormal vectors have delta inner products; completeness requires a full basis of the ambient dimension.
- [IBM: general measurements, collections of matrices](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements#measurements-as-collections-of-matrices): finite positive dimension and a complete family of projectors summing to identity.
- [IBM: purifications](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/purifications): explicitly specified orthonormal bases must be distinguished from arbitrary vector families.

## Reproducers and expected results

| Requirement | Reproducer | Expected |
| --- | --- | --- |
| Finite named basis | `orthobasis(<red|blue>,B,[|red>,|blue>])` | 0 |
| Indexed family and dimension | `orthofamily(<b(j)|b(k)>,B,b,n)` | Delta(j,k), retaining integer domain 0≤j,k<n and positive integer n |
| Self-overlap domain | `replace(orthofamily(<b(j)|b(j)>,B,b,3),j,3)` | Error, including after copying the unresolved norm |
| Completeness | `orthofamily(sum(|b(j)><b(j)|,0,n-1,j),B,b,n)` | Identity(n), retaining positive integer dimension |
| Singleton shape | Substitute n=1 into the copied identity | 1-by-1 matrix |
| Unknown overlap | `orthofamily(|b(j)>,B,b,n)†*orthofamily(|b(j)>,C,b,n)` | Unresolved overlap, declarations retained |
| Incomplete sum | `orthofamily(sum(|b(j)><b(j)|,0,n-2,j),B,b,n)` | No completeness reduction |
| Editor and persistence | Add named and indexed declarations, calculate, save/open, change dimension, restore history | Independent original declarations restored |

`src/quantum-worker-test.py` exercises exact and approximate modes, copy/re-entry, invalid substitutions, full and partial sums, conflicting declarations, and unknown overlaps. Existing finite basis checks remain in that suite. `windows/BasisDeclarationsTests.cs` tests persistence, independent history snapshots, legacy sessions, and validation. `windows/BasisDeclarationsGuiTests.cs` tests draft isolation, cancel/apply, invalid edits, removal, save/open, and (with a worker) calculations and history restoration. The GUI suite also retains matrix-declaration and malformed-session coverage.

The coordinate oracle is independent of named basis metadata: standard coordinate vectors give I3 as their Gram matrix and full projector sum; the ± and ±i bases give I2 and demonstrate the need for conjugation. Their overlaps with the standard basis are nonzero, so different named bases must not be assumed orthogonal.

## Delivery evidence

Reviewed head, CI jobs, packaged audit, and released revision: pending. This file does not mark DEV-03 complete before those gates pass.
