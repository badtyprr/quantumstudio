# Reviewed setup in selected notebook routes

Selected-cell contracts may now use the existing setup observer and inventory
check. Setup must be the first selected code cell, with a nonempty list of
nonblank command strings. Missing commands, Boolean/noninteger indexes, omitted
setup cells and setup after another selected cell are rejected before launch.
Public contracts still bind the observer and check hashes before inspecting the
environment. No new public contract or arbitrary-notebook route is enabled.

Previously every selected contract containing setup was rejected. This prevented
selected local routes from observing original setup cells. The change removes
that blanket restriction while preserving exclusions and the distinction between
selected execution and whole-notebook acceptance. Original source bytes remain
unchanged; authored setup cells have separate roles and indexes.

The observer executes only the contract's reviewed pip commands, records their
actual exit codes, and compares package metadata/RECORD inventories before and
after setup. A failure prevents subsequent source cells and witnesses from
running. This is not whole-environment file-integrity verification, OS isolation,
or a translation of shell syntax. The existing whole-notebook setup observer and
its source/hash are unchanged.

## Motivation and limits

The unchanged QB004 setup cell uses `%%capture` and single-quoted pip arguments.
A Windows prerequisite probe reports IPython cell success while the actual pip
command exits 1. Success of a captured cell alone therefore cannot establish
successful setup. This change supplies the selected route's exit/inventory gate;
QB004's Windows quotation compatibility still needs explicit treatment before
that original setup cell can be accepted. No QB004 route or provider acceptance
is claimed here.

## Verification

The new success/failure-ordering tests failed against the previous blanket
rejection. After the change, 38 selection, post-cell-observer and profile tests
pass. They cover preserved exclusions, unchanged source bytes, stopping later
cells after setup-check failure, and rejection of incomplete or misplaced setup.

Three real Windows-kernel tests pass: selected `%%capture` with successful pip,
selected `%%capture` with failing pip, and the existing whole-route setup test.
Successful setup preserves the metadata/RECORD inventory. Failed setup retains
its nonzero exit, leaves later selected cells unrun, and keeps excluded cells
excluded. Every run reports zero remaining owned processes. These are finite
runtime fixtures, not an original notebook replay or fresh dependency install.

The adjacent [index](selected-setup.json) binds retained evidence under
`cleanup-audit/learning-coverage-20261117/dev13-selected-setup/`, plus the original
QB004 setup probe. CI, packaging and release remain pending; no checklist row is
closed.
