# DEV-11b: compact finite toric Pauli checks

Final scoped validation: verified release [c575cb7e](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-c575cb7e); see [combined final evidence](../DEV-11.md#current-scoped-delivery-dev-11bc-and-parallel-audits). Development records below remain historical; the final package reran the applicable checks.

Development evidence is retained below; review, merged CI and final packaged
verification are now complete in the linked delivery record. This scoped change does not certify any complete source row. DEV-11
remains Partial: 16 rows inventoried, zero whole rows certified.

The pinned IBM-063 notebook and source locations are recorded in
`source-manifest.json` and `source-map.json`. The notebook's “Toric code
description” describes a periodic L-by-L family and illustrates L=9. Our L=3
specialization has 18 edge qubits; it is an adaptation, not execution of the
illustration. `toric-probe.py` verifies the pinned notebook hash and copies its
exact section/cell locations into each run's provenance record.

## Conventions and independent expectations

Coordinates x,y are modulo 3. Horizontal edges h(x,y) run from (x,y) to
(x+1,y); vertical edges v(x,y) run to (x,y+1). Wires 0–8 are h in row-major
order; wires 9–17 are v in row-major order. Wire zero is the leftmost/MSB.
The nine X stars precede the nine Z faces, each in row-major order. A star
uses h(x,y), h(x-1,y), v(x,y), v(x,y-1); a face uses h(x,y), h(x,y+1),
v(x,y), v(x+1,y). Syndrome bit 1 denotes eigenvalue -1 after that Pauli error.

The native regression's one-qubit I/X/Y/Z multiplication table independently
checks all four scalar phases and ordered products. The geometric syndrome
oracle uses vertex endpoints and incident faces. The separate Python oracle
works directly on Pauli letters: distinct nonidentity letters anticommute.
Neither oracle calls the implementation's binary symplectic routines.

All 324 generator pairs commute. Products of all stars and all faces are +I;
an independent enumeration yields 65,536 distinct binary group elements;
rank 16 establishes that these are exactly two independent relations and gives
code-space dimension 2^(18-16)=4. The independent Python lower-bound proof
enumerates all 1,431 weight-one/two Paulis and finds a nonzero syndrome for
each. Four weight-three noncontractible loops commute with every check and
have the two expected anticommuting logical pairs. Anticommutation with a
normalizer loop proves they are outside the stabilizer group, so distance is
exactly three. All 54 one-site X/Y/Z syndromes are compared in full.

These are exact integer results, with no numerical tolerance. The product
stores `[n,x,z,p]` for i^p Z^z X^x and retains all phases. It allocates no
2^18-by-2^18 matrix. The new operations have a separate finite contract:
1–25 qubits, at most 64 generators, distance search bound 1–3. A failed
bounded search reports undetermined distance. No decoder is implemented.

## Preservation and validation

The original `quantum:pauli("XIIIIIIIIIIIIIIIII")` rejection was freshly
reproduced against release 214e6866 before product edits and saved outside the
checkout in `cleanup-audit/dev11bc-20261102/original-rejections.json`, with
binary SHA-256 and complete stdout/stderr. Initial launcher mistakes are
preserved separately and are not counted as product failures. The dense
constructor's nine-qubit contract is unchanged; its intentional rejection
remains part of the original 286-fixture baseline, not a new supported case.

Development checks: 743 focused native assertions passed, including ordered
phase multiplication, geometry, rank, distance and invalid-group rejection.
This diagnostic linked the new module/notation against the retained DEV-08
build dependency and is not evidence of a fresh packaged build. The separately built development worker passed all 405 toric cases and their
serialized re-entries. Actual GUI controls passed 52 assertions plus nine
independent exact clipboard comparisons; four captures were inspected. That
development payload combines the freshly built worker with released 214e6866
GUI/dependencies and is not the final package. Full native and final packaged
release checks remain pending.

`toric-probe.py` produces 405 exact worker cases, each followed by re-entry of
the actual `copy_text`. It requires a new output directory, hashes the worker
before/after, checks the pinned source hash, and preserves full results even
on failure. Example after a package is available:

```powershell
python docs/learning-evidence/dev11/toric-probe.py --worker PACKAGE/quantum-worker.exe --sources F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/sources --output NEW_EVIDENCE_DIRECTORY
```

Whole-source proofs, L=9, general decoding, other code families and linked
media remain outside this finite result. DEV-09's unresolved symbolic case
and DEV-10's limits are unchanged.
