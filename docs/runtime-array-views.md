# Runtime array view foundation

This is an internal DEV-08 foundation, not source-language or release completion.
`ArrayView` resolves selectors against an existing array allocation without
reading its elements. Scalar selectors drop axes; inclusive ranges retain them.
Runtime-varying expressions read the existing copied scalar frame. The importer
must capture those expressions in private activation slots before using them as
reference geometry; an uncaptured expression is intentionally reevaluated.

Views preserve row-major logical order, negative classical indices, reverse and
strided slices, and zero-length shapes. Omitted endpoints select the full axis
in the step direction. Explicit invalid endpoints and zero steps fail even for
empty sources. Endpoint evaluation order is start, step, stop. Resolution is
bounded by the existing 4096-element allocation, seven axes, 32 levels and 512
expanded expression nodes. Geometry never addresses outside its backing array.

Nested views may remove write access but cannot regain it. Indexed stores in
both executors reject readonly selections during structural validation, including
unexecuted branches. Integer and numeric reads retain existing initializedness
and type checks. View extent expressions return unsigned runtime dimensions
without reading array elements.

`validateBindings` checks physical slots in each scalar table, rather than
bounding intervals or allocation IDs. Multiple mutable references may not
overlap; readonly/readonly and readonly/mutable overlap are permitted. Views
must be resolved before this check. The future call preflight must execute it
before any callee effects and validate unused actuals as well.

Remaining integration: explicit call preflight operations, source lowering and
geometry capture, document/protocol representation, source diagnostics, editor
and export/reimport, bulk-copy snapshots, and packaged acceptance. No DEV-08
checkbox or release claim follows from these native APIs alone.
