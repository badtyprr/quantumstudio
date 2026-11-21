"""Reconstruct IBM-120 cell 30 from the six-spin Hamiltonian and the original initial state."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
raw = args.notebook.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == "d3185448e3387a0d92d8e09abc2d7490c27a69cb8f6993ff8ffddc07ce5b0fd5"
source = json.loads(raw)["cells"]
assert 'prepare_state("001100")' in "".join(source[13]["source"])
tables = {}
for stmt in ast.parse("".join(source[30]["source"])).body:
    if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
        name = stmt.targets[0].id
        if name in ("exact_times", "exact_energy", "exact_magnetization", "exact_correlation"):
            tables[name] = np.array(ast.literal_eval(stmt.value.args[0]))

times = np.linspace(0, 30, 101)
np.testing.assert_allclose(tables["exact_times"], times, atol=1e-14, rtol=0)
basis = np.arange(64)
spin = 1 - 2 * ((basis[:, None] >> np.arange(6)) & 1)
mag = spin.mean(axis=1)
corr = (spin[:, :-1] * spin[:, 1:]).mean(axis=1)
angle = np.pi / 8
hamiltonian = np.diag(-0.2 * 5 * corr - 1.2 * np.sin(angle) * 6 * mag)
for q in range(6):
    hamiltonian[basis, basis ^ (1 << q)] = -1.2 * np.cos(angle)
levels, modes = np.linalg.eigh(hamiltonian)
states = modes @ (modes[int("001100", 2), :, None] * np.exp(-1j * levels[:, None] * times))
prob = abs(states) ** 2
np.testing.assert_allclose(prob.sum(axis=0), 1, atol=1e-13, rtol=0)
actual = {"energy": (states.conj() * (hamiltonian @ states)).sum(axis=0).real,
          "magnetization": mag @ prob, "correlation": corr @ prob}
for name, values in actual.items():
    np.testing.assert_allclose(values, tables["exact_" + name], atol=1e-10, rtol=0)
report = dict(source_sha256=digest, cell=30, initial_state="001100", times=len(times),
              observables=list(actual), comparisons=303, absolute_tolerance=1e-10)
args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
