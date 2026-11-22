"""Replay selected pinned QB-034/035 cells with CUDA-Q 0.17 on a Linux CPU.

Pass the qBraid-CUDAQ source directory. The last output line is a JSON report.
"""
import argparse
from contextlib import chdir
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import cudaq


def notebook(directory, name, digest):
    raw = (directory / (name + ".ipynb")).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Source hash mismatch for " + name)
    return json.loads(raw)["cells"]


def run_cell(cells, index, namespace):
    # The CUDA-Q decorator reads the function's source file during compilation.
    path = Path.cwd() / f"cell-{index}.py"
    source = "".join(cells[index]["source"])
    path.write_bytes(source.encode())
    exec(compile(source, str(path), "exec"), namespace)


def bell_counts(counts, width, shots):
    counts = dict(counts.items())
    assert set(counts) == {"0" * width, "1" * width}
    assert sum(counts.values()) == shots
    assert abs(counts["0" * width] - shots / 2) <= 6 * math.sqrt(shots / 4)
    return counts


def replay(directory):
    quick = notebook(directory, "cuda_quantum_quickstart",
                     "4344899335b2dc8c6c4f5b7d8c83e2373c3c5cc529e15e3d18e4b4d202af863d")
    bench = notebook(directory, "cuda_quantum_qpu_benchmarking",
                     "e22d3caa13116b307f7132d1b51b81cc26027120015cab6276dc87dd1ec35705")
    cudaq.set_target("qpp-cpu")
    cudaq.set_random_seed(731)
    report = dict(target=cudaq.get_target().name, version=cudaq.__version__)
    namespace = dict(__name__=__name__, cudaq=cudaq)
    with TemporaryDirectory() as temp, chdir(temp):
        run_cell(quick, 9, namespace)
        run_cell(quick, 10, namespace)
        report["bell"] = bell_counts(namespace["counts"], 2, 2000)
        run_cell(quick, 13, namespace)
        report["async_bell"] = bell_counts(namespace["counts"], 2, 1000)
        run_cell(quick, 17, namespace)
        expected = 5.907 - 4.2866 * math.sin(0.59) - 6.34329 * math.cos(0.59)
        exact = cudaq.observe(namespace["ansatz"], namespace["hamiltonian"], 0.59).expectation()
        sampled = namespace["result"].expectation()
        assert abs(exact - expected) < 1e-9 and abs(sampled - expected) < 0.40
        report["ansatz"] = dict(exact=exact, sampled=sampled, analytic=expected)
        run_cell(bench, 4, namespace)
        for width in (2, 3, 4, 5):
            counts = bell_counts(cudaq.sample(namespace["ghz"], width, shots_count=1000), width, 1000)
            assert namespace["ghz_fidelity"](counts, width) == 1.0
            report[f"ghz{width}"] = counts
        try:
            run_cell(quick, 15, namespace)
        except RuntimeError as error:
            if str(error) != "Cannot persist a cudaq::future for a local kernel execution.":
                raise
            report["local_handle_error"] = str(error)
        else:
            raise AssertionError("CUDA-Q local handle behavior changed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.source_directory)))
