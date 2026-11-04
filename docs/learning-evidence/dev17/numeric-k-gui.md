# Assigned numeric-k supplemental GUI acceptance

This focused supplement leaves `windows/Dev17GuiTests.cs` and its wrapper
unchanged. The existing 306 keyword checks remain, with 71 additional assertions
(377 total expected). GUI execution against the coordinator's fresh candidate is
pending; compilation and worker probes are not Clipboard acceptance or release.

## Independent expectations and assignment route

The contract preserves ordinary numeric partial traces independently of literal
mapping labels. `src/quantum-named-subsystem-test.cc` explicitly installs a
`KnownVariable` named k with value zero and checks bare k, [k], explicit [2,2]
dimensions, and `sum(ptrace(identity(4),[k,"not"]),1,1,"not")`.
The existing 212-check worker suite does not directly test that assigned-k case.

For the contract's IBM mixture rho, tracing index zero sums
`rho[2*a+b,2*a+d]` over a, giving `[3/4,1/4;1/4,1/4]`. Tracing index one gives
`diag(1/2,1/2)`. The mixed selector [k,"not"] with k=0 and the single sum
iteration "not"=1 traces both factors of I4, giving its full trace, exactly 4.
These expectations precede GUI execution and are independently reproduced by
the worker fixture's rational basis-contraction oracle.

Each GUI Calculate starts a fresh worker. The supplemental expression uses
`if(save(0,"k")=0,function('quantum: EXPRESSION'),-1)` to assign k before parsing
the inner expression. This is an actual scalar assignment, not a zero-width
sum binder substituted for the requested case. A k=1 control distinguishes the
two indices. Directly placing ptrace in the if branch parses k too early and
fails; that attempted route remains in the probe evidence.

Inside this generic function wrapper, use the registered `qsubsystems` spelling.
The unregistered `subsystems` alias is affected by generic x/y/z rewriting and
fails there. This limitation is preserved in the evidence, not claimed fixed.
Both spellings are handled by the same mapping parser outside that wrapper.

## Coverage and evidence boundaries

The supplement invokes actual Calculate and Copy controls and reads Windows
Clipboard before exact value assertions and re-entry. It checks all three
assigned-zero numeric forms, the k=1 control, the mixed quoted-not scalar,
and exact declaration metadata. Mapping [not,k] deliberately puts k second,
so literal k selects a different factor from numeric zero. It saves/reopens
the compatibility expression and copied mapping, tests a conflicting mapping
between save/reopen, checks both retained labels, and rejects numeric indices
on the mapped value. Sessions preserve expressions/history, not a global scalar
assignment across worker processes. New failures attempt a `failure.png` capture.

New expected captures are `numeric-k-compatibility.png`, `numeric-k-reopened.png`,
`numeric-k-mapping-reopened.png`, and `numeric-k-mapped-index-rejected.png`.
Sessions are `numeric-k.qsession` and `numeric-k-mapping.qsession`.
`numeric-k-result.txt` reports the 71 new assertions separately from the total.

External evidence: `F:/src/libqalculate/cleanup-audit/dev17-numeric-k-gui-20261103/`.
`oracle-probes-1.*`, `oracle-probes-2.*`, and `oracle-confirmed.*` retain the
initial routes and failures. `oracle-confirmed-2.*` records nine successful
worker checks against the coordinator-approved retained hosted candidate:

- Source: `6005e1de0e36c985a1319d6255274c430d06b634`.
- Worker SHA-256 before and after:
  `ef5bc7947b0df1f1fdfd41a3b03a2646db663598b671a7248b0cbfeaf573937d`.

These worker probes establish the fixture route and expected values, not GUI
acceptance of a future candidate. Fresh candidate identities, complete results,
capture inspection, integrity records and independent reviews will be recorded
in the focused external handoff. The coordinator owns build/workflow integration
and final release decisions; DEV-17 release completion is not claimed here.
