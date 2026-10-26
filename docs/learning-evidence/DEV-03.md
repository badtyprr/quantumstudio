# DEV-03: declared orthonormal bases

Acceptance: declare a named basis and dimension; reduce inner products to Kronecker delta and complete projector sums to identity; leave unknown bases unresolved; preserve declarations through save/load and copy. Symbolic families and a dedicated editor are included in this scope. Released and package-verified in [e9e01c5a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e9e01c5a).

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

Implementation [PR #376](https://github.com/badtyprr/quantumstudio/pull/376) reviewed at `f4ea596dc4daa87a620837227fae469d8d72c52a`; implementation merged revision `26bed7a5da1a03b44b6e715dcffd39a4b77590e6`. Independent Standards and Spec reviews have no outstanding findings. Review found and fixed mixed finite/indexed declaration capture, with independent exact/approximate nesting and copy probes.

Required reviewed-head CI:

- [Native build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40266046626/job/121388597936): passed.
- [Windows GUI build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40266046648/job/121388598652): passed.
- [Windows OpenQASM build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/40266046628/job/121388597859): passed.

The clean package passed all native, worker, GUI, importer/export and portable-archive gates. The 2,178 worker checks include the declared-basis cases and coordinate oracles; 22 declaration/storage checks cover persistence. The actual packaged GUI passed basis editing, calculations, cancel/apply/removal, save/open, and history restoration, with normal and minimum-size screenshots inspected. All payload hashes matched the immutable ZIP before publication.

Release: [e9e01c5a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e9e01c5a). ZIP SHA-256: `4dc6ab77e5b551efc7d3721d93a5a39bf9776a6f9e64bc5260f33c30db066419`.

The first clean package failed at transient export replacement error 1175. [PR #377](https://github.com/badtyprr/quantumstudio/pull/377) adds bounded retries for recoverable Windows errors while retaining atomic replacement and persistent-error reporting. The real temporary-lock regression, 18 atomic checks, 1,000 probe attempts without failure, and six module export cases passed. The fresh release package passed all gates. See [export recovery evidence](EXPORT-RETRY.md); the underlying filesystem cause remains unidentified.

All explicit DEV-03 requirements are verified. This completion does not imply complete IBM lesson coverage or completion of unrelated roadmap items.
