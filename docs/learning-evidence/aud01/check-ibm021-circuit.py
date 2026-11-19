"""Execute the IBM-021 figure with the printed three-input-bit, five-output-bit table."""
import argparse
import base64
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess


def run(command, data):
    return subprocess.run(command, input=data, capture_output=True, check=True, timeout=120).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("notebook", "figure", "import_python", "adapter", "worker", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    source = args.notebook.read_bytes()
    assert digest(source) == "2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a"
    figure_hash = digest(args.figure.read_bytes())
    assert figure_hash == "d310a30cf1768134b0105f0dfa757cc2346a1a41b6ab3e03fc42724a1e3d8e8f"
    text = "".join(json.loads(source)["cells"][0]["source"])
    assert "/quantum-query-algorithms/Simon.svg)" in text
    table = re.findall(r"f\(([01]{3})\)\s*&\s*=\s*([01]{5})", text)
    assert [int(x, 2) for x, _ in table] == list(range(8))
    values = [int(value, 2) for _, value in table]
    fixture = Path(__file__).with_name("ibm021-simon.qasm")
    importer = fixture.parents[3] / "windows" / "qasm-import.py"

    def compile_source(qasm):
        return json.loads(run([args.import_python, "-E", "-s", "-B", importer, "--classical"], qasm))

    def execute(document):
        package = json.loads(run([args.adapter], json.dumps(document).encode()))
        result = json.loads(run([args.worker, "--exact-circuit"], base64.b64decode(package["exact"])))
        assert result["bits"] == document["OutputBits"] and result["qubits"] == 8
        return {label: Fraction(value) for label, value in result["probabilities"].items()}, package["source"]

    qasm = fixture.read_bytes()
    diagram = compile_source(qasm)
    # The first three wires are the measured input. The remaining five
    # start at zero and leave the oracle without further gates in the figure.
    assert diagram["Qubits"] == 8 and diagram["OutputBits"] == [2, 1, 0]
    steps = diagram["Steps"]
    hadamards = [dict(Kind="Gate", Expression="H", Wires=[i]) for i in range(3)]
    measurements = [dict(Kind="Measure", Wires=[i], ClassicalBit=i) for i in range(8)]
    assert steps[:3] == steps[-6:-3] == hadamards and steps[-3:] == measurements[:3]
    oracle = steps[3:-6]
    assert oracle and all(g["Kind"] == "Gate" and g["Expression"] in ("X", "CNOT", "CCX") for g in oracle)

    # Inspect every basis input to the compiled oracle, including nonzero
    # target registers. The expected permutation comes from the notebook.
    full = dict(diagram, Registers=[dict(Name="readout", Size=8)], OutputBits=list(reversed(range(8))))
    for basis in range(256):
        prepare = [dict(Kind="Gate", Expression="X", Wires=[i]) for i in range(8) if basis >> i & 1]
        probabilities, _ = execute(dict(full, Steps=prepare + oracle + measurements))
        target = basis ^ (values[basis & 7] << 3)
        assert probabilities == {format(target, "08b"): 1}, (basis, target, probabilities)

    # Measuring the output as well is a diagnostic variant. Its distribution
    # resolves all 256 cells before the marginal discards the lower register.
    joint = {}
    marginal = {}
    for y in range(8):
        for z in range(32):
            amplitude = sum((-1) ** ((x & y).bit_count() % 2) for x in range(8) if values[x] == z)
            if amplitude:
                probability = Fraction(amplitude**2, 64)
                joint[f"{z:05b}{y:03b}"] = probability
                marginal[f"{y:03b}"] = marginal.get(f"{y:03b}", 0) + probability
    assert execute(dict(full, Steps=steps[:-3] + measurements))[0] == joint
    actual, exported = execute(diagram)
    assert actual == marginal == {bits: Fraction(1, 4) for bits in ("000", "011", "100", "111")}
    assert execute(compile_source(exported.encode()))[0] == marginal
    report = dict(notebook_sha256=digest(source), figure_sha256=figure_hash, qasm_sha256=digest(qasm),
                  worker_sha256=digest(args.worker.read_bytes()), adapter_sha256=digest(args.adapter.read_bytes()),
                  figure="Input Hadamards, one reversible oracle call, input Hadamards, then input-only measurement. Both registers start at zero.",
                  realization="The figure leaves the oracle abstract. The OpenQASM gate realizes the lesson table by XORing its Boolean output functions into five target bits.",
                  input_bits=3, target_bits=5, oracle_calls=1, primitive_oracle_gates=len(oracle),
                  oracle_basis_inputs=256, joint_cells_checked=256, nonzero_joint_cells=len(joint),
                  input_probabilities={bits: str(marginal.get(bits, 0)) for bits in map("{:03b}".format, range(8))},
                  exported_qasm_sha256=digest(exported.encode()), export_reimport_verified=True)
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
