"""Check the three pinned IBM-033 diagrams against the released calculator."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def check_figure(path, digest, axes, arrows, worker):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"Unexpected source figure {path.name}")
    paths = {node.get("id"): node for node in ET.fromstring(raw).iter()}
    # The source uses one isotropic transform, with y increasing upwards in
    # these path coordinates. The arrow shafts start at the origin.
    transforms = {paths[key].get("transform") for key in axes + arrows}
    if len(transforms) != 1:
        raise ValueError(f"Different coordinate systems in {path.name}")

    def points(key):
        return list(map(float, re.findall(r"-?\d+(?:\.\d+)?", paths[key].attrib["d"])))

    def direction(x, y):
        length = math.hypot(x, y)
        return x / length, y / length

    operators = []
    axis_angles = []
    for key in axes:
        x, y = direction(*points(key)[:2])
        axis_angles.append(round(math.degrees(math.atan2(y, x)) % 180, 4))
        # Reflection in the line spanned by u is 2 u u^T - I.
        operators.append(f"(2*[{x};{y}]*[{x},{y}]-identity(2))")
    vectors = []
    angles = []
    for key in arrows:
        x0, y0, x, y = points(key)
        assert x0 == y0 == 0
        x, y = direction(x, y)
        vectors.append(f"[{x};{y}]")
        angles.append(round(math.degrees(math.atan2(y, x)), 4))

    def compare(product, initial, target, expected):
        delta = f"(({product})*{initial}-({target}))"
        expression = f"abs(element({delta},1,1))+abs(element({delta},2,1))<1/10000"
        result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                                capture_output=True, check=True, timeout=30,
                                env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data")))
        if json.loads(result.stdout)["copy_text"] != str(int(expected)):
            raise AssertionError(f"{path.name}: {expression}")

    for index, operator in enumerate(operators):
        compare(operator, vectors[index], vectors[index + 1], True)
        compare(operator, vectors[index], vectors[index], False)
    if len(operators) == 2:
        compare("*".join(reversed(operators)), vectors[0], vectors[-1], True)
        compare("*".join(operators), vectors[0], vectors[-1], False)
    return dict(file=path.name, sha256=digest, reflection_axes_degrees=axis_angles,
                state_angles_degrees=angles, worker_checks=2 * len(axes) + (2 if len(axes) == 2 else 0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("figures", type=Path, help="Directory containing the three original SVGs")
    parser.add_argument("worker", type=Path)
    args = parser.parse_args()
    worker = args.worker.resolve()
    sources = [
        ("reflection1.svg", "2bd09c6838febdf9fb881e7b4071b672dd87e34bf11101070e27cf0b94c02931",
         ["path9"], ["path15", "path23"]),
        ("reflection2.svg", "243a98b788cf2879a26c8abbff342626e3db14dafc3aaeec91b50ba139748dd3",
         ["path8"], ["path18", "path32"]),
        ("Grover_rotation.svg", "e9ad67e771dbae4b722b2f11b3bfafee42c26baab8ace144ec2860ecb639c4b9",
         ["path17", "path18"], ["path26", "path34", "path41"]),
    ]
    figures = [check_figure(args.figures / name, digest, axes, arrows, worker)
               for name, digest, axes, arrows in sources]
    print(json.dumps(dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                          figures=figures), indent=2))
