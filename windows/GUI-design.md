# QuantumStudio workspace design

The expression and result are the primary workflow. Circuit construction,
examples, named states and session storage remain explicit actions. Long content
scrolls rather than hiding controls at the minimum window size. Calculation
keeps its existing cancellation, time limit and worker-process boundary.

## Responsibilities

- `MainWindow.xaml` owns workspace layout and labels.
- `WorkspaceTheme.cs` owns semantic colors once, including frozen brushes used
  by diagrams and headless circuit-file tests.
- `WorkspaceTheme.xaml` owns control appearance and keyboard-focus feedback.
  Colors reference semantic resources rather than repeat literal values.
- `NamedStateEditor.cs` owns a private editing draft. Its only workspace mutation
  is a callback carrying a validated copy when Apply succeeds. Cancel discards
  the draft. The shared `SessionStore` validation owns definition limits.
- `SessionStore.cs` owns persistence, history snapshots and worker request framing.
  Exact defining expressions are saved; displayed results are never state data.
- `CircuitComposer.cs` owns circuit editing and its existing undo/redo model.
- `QuantumStudio.cs` connects these components to calculation and result views.
  It still contains legacy rendering and smoke checks; this redesign does not
  claim to have removed all of that coupling.

## Trade-offs and verification

The application uses WPF rather than adding a web runtime or replacing the
mathematics backend. The dark scientific theme is the selected design, not a
partial automatic theme switch. Colors, input controls and diagrams share the
same palette so new views can retain contrast without copying color literals.

Required GUI CI builds the executable and checks persistence, input handling,
circuit preservation, state-editor behavior and responsive circuit layout.
The state-editor regression check runs without the mathematics worker. Full
package smoke and keyboard checks run later against the executable with its
actual worker and dependencies. Release promotion must use the tested package,
not another build. Visual review covers the main workspace at normal/minimum
sizes, circuits, examples, the state editor and representative results.
