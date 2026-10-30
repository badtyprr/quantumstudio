# Runtime array view worker format

QEXACT15 and QSAMPLE16 extend the previous array-capable protocols. Older
versions reject new opcodes and view selectors. These formats are internal
worker integration; source/model/editor/export support remains unfinished.
All fields below use the existing bounded LF-terminated integer encoding.

A view encodes: writable (0/1), parent-present (0/1), then either a recursively
encoded parent view or backing array ID (0..4095), then selector count (1..7).
Each selector is scalar tag0 followed by an integer expression, or range tag1
followed by a presence mask (start=1, stop=2, step=4) and the present expressions
in start/stop/step encoding order. Runtime evaluation remains start/step/stop.
Omitted endpoints and step retain native full-range/default-step semantics.
Nested views cannot regain write permission. Parser recursion and expanded
expression counts are bounded before construction, at 32 levels and 512 nodes.

An array selection keeps its previous encoding when its first integer is an
array ID. Tag4096 instead introduces a view, followed by the existing logical
index list and bounded UTF-8 source bytes. A rank-zero scalar view permits an
empty logical index list. The backing allocation still controls table and type.

Integer expression opcode12 encodes a view followed by an extent axis (0..6).
Its result is the unsigned machine-width dimension, with no element read.
Step opcode23 encodes a reference count (1..64), then each view and an optional
fixed shape (dimension count0 means rank-only; otherwise dimensions0..4096).
The step validates every actual, fixed shapes, and mutable overlap before the
next instruction. Empty or unused uninitialized arrays need no dummy values.

`src/quantum-classical-array-view-request-test.py` exercises both engines,
permission loss/regain, undefined geometry, empty shapes, fixed-shape mismatch,
measurement-dependent selectors, disjoint strided overlap, older-version
rejection, and every truncation of a valid view request. Existing array protocol
checks remain regression controls.
