# Ensembles, instruments and general measurements

Quantum mode supports labeled finite measurement models. Use `vector(...)` for
collections, including a single outcome or a single Kraus matrix. Labels must be
distinct scalar values or quoted text. Outcomes retain their input order.

| Expression | Meaning |
| --- | --- |
| `povm(labels,effects)` | Positive effects summing to the identity |
| `instrument(labels,kraus_groups)` | A vector of Kraus-matrix vectors, one group per outcome |
| `ensemble(labels,weights,states)` | Normalized states with nonnegative weights summing to one |
| `measurementvalid(model)` / `ensemblevalid(model)` | `1` when all validity conditions are proved |
| `effects(model)` / `outcomelabels(model)` | Effects / labels of a validated measurement |
| `ensembleaverage(model)` | Weighted density matrix |
| `probabilities(model,state)` | Outcome probabilities in label order |
| `branches(instrument,state)` | Triples of label, probability and unnormalized output density matrix |
| `poststate(instrument,state,label)` | Normalized conditional density matrix |
| `naimark(model,ancilla_dimension)` | A full unitary dilation of the associated POVM |

For example, IBM's two-effect measurement gives probabilities `vector(5/6,1/6)`:

```
probabilities(povm(vector("red","blue"),vector([2,1;1,1]/3,[1,-1;-1,2]/3)),|+>)
```

A projective instrument gives `density(|1>)` for the blue outcome:

```
poststate(instrument(vector("red","blue"),vector(vector([1,0;0,0]),vector([0,0;0,1]))),|+>,"blue")
```

Each Kraus group may contain several matrices. Matrices share input and output
dimensions across the instrument; rectangular matrices are allowed. A POVM alone
does not determine post-measurement states. Zero-probability outcomes retain zero
unnormalized branches but have no normalized conditional state. Density matrices
returned by these operations work with `ptrace` and `qptracedim(rho,indices,dimensions)`.

Invalid positivity, normalization, completeness or dimensions produce errors.
Unproved symbolic conditions remain in the original expression; they do not become
`1`. Substituting concrete values rechecks those conditions. Copy preserves nested
collections and pending expressions for re-entry. Declared `matrixparam` and
`operatorparam` shapes participate in dimension checking.

Naimark construction places the ancilla before the system and initializes it in
`|0>`. For system dimension n and ancilla dimension a, the result is an an-by-an
unitary whose first n columns stack the positive square roots of the effects.
Ancilla outcome blocks follow the label order; additional blocks have zero input
probability. Other columns complete an orthonormal basis. Applied to an instrument,
this constructs a dilation of its effects; it does not reproduce that instrument's
chosen conditional states.

The ancilla dimension must be an integer at least the number of outcomes and at
most 64. System/output dimensions are at most 64; total Naimark dimension is at
most 128. There are at most 64 labels and 64 Kraus matrices per outcome. Symbolic
ancilla dimensions remain pending. A construction whose roots or orthonormal
completion cannot be established remains unevaluated.

Exact normalization and completeness are strict. Approximate mode permits an
absolute residual of 1e-12 for normalization/completeness, without relaxing
positivity. Numerical unitary completion checks a residual of 1e-10.

See [DEV-09 evidence](learning-evidence/DEV-09.md) for source locations,
adaptations, independent reference results and the current validation status.
