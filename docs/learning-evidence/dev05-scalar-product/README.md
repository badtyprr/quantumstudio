# Indexed scalar-product component - 2026-11-10

This checkpoint covers one isolated expression from the IBM Deutsch-Jozsa
notebook, its actual copied expression, and a disclosed numerical example.
DEV-05 remains partial. The surrounding M11 derivation, whole IBM-020 lesson,
GUI/session behavior and release acceptance remain open.

## Original source and behavior

The [source lesson](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm)
notebook snapshot has SHA-256
`513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f`.
Cell 0, ID `17463a96`, Unicode offsets `[4750,4783)` contain:

```text
x_{n-1}y_{n-1} + \cdots + x_0 y_0
```

The substring is unchanged; the first call adds only the `quantum:` transport
prefix. Isolation removes the surrounding aligned presentation, tensor
operator, domain binder and ket, so this is not acceptance of that context.

The earlier development worker at `eebcd8e01` rejected this fragment with
`Unsupported TeX command: \cdots at byte 24`. On the fresh development worker
for `1fc304f1`, the four source-bound calls returned:

| Call | Input route | Result |
| --- | --- | --- |
| Original fragment | Quantum notation, no coefficient assignments | `qscalarproductsum("x_","y_",'n',vector())` |
| Ordinary re-entry | Actual `copy_text` from the first call | Same canonical expression |
| Disclosed numerical example | Actual ordinary-copy result, then `n=2` and `x_0=x_1=y_0=y_1=1` | Exact `2` |
| Parity control | `bitdot(bitstring(3,2),bitstring(3,2))` | Exact `0` |

The ordinary scalar sum and binary parity are different values. The numerical
assignments are explicit adaptations; they are not supplied by the original
substring. The [notation contract](../../quantum-notation.md#indexed-scalar-product-sums)
defines the bounded grammar, width limits, coefficient domain and copy rules.

## Verified development evidence

Product source is `1fc304f1aeb29a417c9593b577f116ec262383c2`; the test-only raw-output
capture correction is `028a6d954af704e2b4621fe398a9df5afa1d2a3f`. The binaries were
built before that test-only correction and remained unchanged afterward.

- Clean full suite: 85 tests, 84 passes, one existing Windows `threadtest` skip,
  no failures or errors. Unit coverage includes 17 batches and 676 assertions.
- Focused coverage: 381 native checks and 55 worker calls, including actual
  copy/re-entry, partial assignments in both orders, aliases, binder scope and
  rejected domains.
- Source probe: four successful calls, 776 captured bytes, empty stderr.
  Each call completed in under 0.44 seconds and recorded the same 29 startup
  modules: the worker, eight toolchain DLLs and 20 host OS modules.
- All recorded module bytes and all 1,686 build files remained unchanged.
  Independent Spec and Standards reviews passed. Complete owned-job receipts
  confirmed zero remaining processes and no audit or cleanup errors.

Startup snapshots do not observe every possible later transient module.
The first fresh-suite attempt remains a failure: 83 passes, one skip and a
Windows unit-launcher syntax error. An isolated CRT probe reproduced the error
with forward slashes in `COMSPEC`; backslashes corrected it. The targeted unit
run and the separate clean full-suite rerun both passed. No failed evidence
was relabeled as a pass.

## Integration checkpoint

[Draft PR #464](https://github.com/badtyprr/quantumstudio/pull/464) applies the
feature to master `f9f43bf9` as commit
`d4f7dba818910eaae9956178c5d350542bd145dd`. It retains all 79 master tests and adds
two tests. The development branch's other draft features are excluded.

[Native CI run 42807830906](https://github.com/badtyprr/quantumstudio/actions/runs/42807830906)
passed all 81 Linux tests, integer undefined-behavior checks and source
distribution verification. Its synthetic merge
`d9454487e7690bf039cc08373824b645cf753e64` has exactly the PR head's source tree
`3b52d42e54c62ac30691f603307a3c8c5e809921`.

These Linux integration results are separate from the development-worker
results above. A fresh Windows integration build is in progress at this
checkpoint. Feature-specific GUI/session and release checks are not credited.

## Evidence records

[evidence.json](evidence.json) carries source coordinates and hashes, actual
requests and responses, raw-output hashes, module hashes, product identities
and acceptance-manifest hashes. Full logs, reviews, original failures and
manifests remain outside disposable builds under
`F:/src/libqalculate/cleanup-audit/coordinator-20261104/`, in the
`dev05-m11-candidate-*` and `dev05-m11-integration-hosted-20261110` records.
