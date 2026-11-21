"""Replay literal formulas from pinned, IBM quantum lessons."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("revision", help="Revision used to build the worker")
parser.add_argument("--lesson", help="Require this pinned lesson")
args = parser.parse_args()
worker = args.worker.resolve()
data = args.notebook.read_bytes()
digest = hashlib.sha256(data).hexdigest()
lessons = {
    "c6594e782df4c62b653d6e571b96f6fed6a9c2783991d6f998cc9db65baff427": ("IBM074", "introduction", 0, 0),
    "7f001ec597b80e45be630d4d77f00c26607588bccb334712507f786f1a5392c1": ("IBM075", "running-quantum-circuits", 0, 2),
    "b057ac805e3f1d9be6c25dac689b9eff8435046fa77bd0c02258c63560a30b23": ("IBM076", "utility-scale-qaoa", 37, 6),
    "eb362a21d29dbdd06382b9a572bdd9a0100aaa3707541b43a8df6a9856742d9f": ("IBM077", "applications-of-qc", 2, 5),
    "c73c951ff00e85b24a28f6bb4ef9fe5237a5eba375ff174639a14918e1ce01a4": ("IBM078", "mapping", 76, 2),
    "7325643fd9a6a6b68e8c1c68c9acce43b064be2474dbffeb9d07920edd09742a": ("IBM079", "simulating-nature", 61, 12),
    "e77ac6b0cce54e7f5264122591a9532a502a4a10e05d5fa5d3545275832e3155": ("IBM069", "build-and-run-your-first-quantum-program", 16, 0),
    "70686bafd5486949decd0166944c52ad02c55ea183f4e7ef4d6ded3ad5ef709d": ("IBM070", "quantum-mechanics-basics", 92, 0),
    "07ed4dc2bc61a2b36515bba6f8fb9b3ed0d2ad41b6265f1be17ad6b31bb6698c": ("IBM071", "your-first-quantum-experiment", 20, 0),
    "96b3ab669c676704e53032e82d552263b315b3d35e881142ad9eaa668fe571e5": ("IBM072", "quantum-computing-context", 2, 1),
    "b01c624b43a681fd0035f7ab6f8c9908b0571d174c4ab5c5ca3d8680fb69ecfa": ("IBM073", "continue-your-learning-journey", 0, 0),
    "c79165e211e3669c87b20fc1f7018571ba734f5d4b11bb3e6c004d3037211de4": ("IBM065", "introduction", 0, 0),
    "e774a7223c3a5b4473198591f1c3a29863178b4b0b92055a6cfb185403214c96": ("IBM066", "approach-to-fault-tolerance", 1, 2),
    "86969cf39e501273ae90ccf63633bbe71e30ce976458af053dd97449d0220305": ("IBM067", "controlling-error-propagation", 87, 8),
    "8712a2075639c675ded5b842dce3ccbf2288e32eaf5a3db494151d67e2581289": ("IBM068", "threshold-theorem", 31, 0),
    "2ff07f29f923364ca6d47b07a36266bebe64e335cce6d50cdeed2d1cbf39af4e":
        ("IBM028", "phase-estimation-procedure", 396, 17),
    "9ea5aee35aea5a33049ce593ef683ad2dcfc3bfff96f058d9ca8dbe0422c8681":
        ("IBM029", "shor-algorithm", 438, 0),
    "7cd1ba3b4697d4bde922918a060234374ca4fa8137ef221d54944e6c53c24e83":
        ("IBM030", "introduction", 0, 0),
    "9bc1492a52076f45c99e20d10be00d847a3901be147f56caf2a1ba0849a981fc":
        ("IBM031", "unstructured-search", 45, 0),
    "d60b500f57ce51007665c53daae3a04cfc3fef6054af2e6abe27297d2d91151a":
        ("IBM032", "grover-algorithm-description", 59, 3),
    "cf35c6409842268e9913008e61df569cf875bb209765682689bb590b6ed36ebe":
        ("IBM033", "analysis", 117, 3),
    "94ee62dd84ab644d5ba22ba1675fdb29afb0ddc777505af0461f469c9649077b":
        ("IBM034", "number-of-iterations", 155, 0),
    "fb35d58b14dfd991da94ea11ef5e72bcd384287217182ddfebe1a2129b3e254a":
        ("IBM035", "concluding-remarks", 1, 0),
    "ae48ca76386dbd5c315cd993a18f2480ab0480d05a1f1c9f5642b20399e6e3c6":
        ("IBM036", "introduction", 0, 0),
    "bb350db44104e0d9c25b66b09cc4162b32caff52f0853faa31fbda73e8f019aa":
        ("IBM037", "classical-information", 150, 0),
    "9193becddf7f8f9943aa24057a5666195b2f70d946ccd104033164ed6125e79b":
        ("IBM038", "quantum-information", 161, 0),
    "071bde2b6b2b044a08f3cbbf813d7fd8d93d3e4819faf8b4543147ef9797639a":
        ("IBM039", "qiskit-implementation", 20, 0),
    "3bfb6f099daae3385bb1fd1d5e2a28eac844a1f95dbbd6024749efc6a3a4f676":
        ("IBM040", "introduction", 0, 0),
    "624fe895b052089a6afaf5a2ca6849918cd7291dba8932b444827ac042494249":
        ("IBM041", "classical-information", 376, 0),
    "1173c31c7f1a9be7194647118d80d11c734f4412d5f41642fc381f986295e8f5":
        ("IBM042", "quantum-information", 332, 0),
    "971002d918d25f489f4b51e4a1bb1c8a675e5f220f6823a640517d77387bf840":
        ("IBM043", "qiskit-implementation", 16, 0),
    "453512b0cc2393c251c129824aac06bd162fa096937cf83fb8bbbef197e15010":
        ("IBM044", "introduction", 0, 0),
    "6b5989521e76ced735050fe1780acaa60c01452629fedc6612867673b409df7b":
        ("IBM045", "circuits", 76, 17),
    "3c1262a55ec7ddcc7f4b650f16b1ab45c65b8f6c529b7f736a1a43f438f762bb":
        ("IBM046", "inner-products-and-projections", 239, 0),
    "f45266235639d924711d7f3a57bd39db1e99a3705cb2c3401117d68a75d477e2":
        ("IBM047", "limitations-on-quantum-information", 146, 2),
    "7a1e4999246cae78a4bae99822fcb4fae29e556a6b1358249d611ae102db7a57":
        ("IBM048", "introduction", 17, 0),
    "a126b0f66b405b79c3829c598cd7688075e91a80d002ab5dcb5d9194dacbf023":
        ("IBM049", "quantum-teleportation", 147, 3),
    "278c63dd661ff599c943d5fe0fb4303b12efe6c0067e33a39256f9189d9ddc1d":
        ("IBM050", "superdense-coding", 57, 1),
    "78add11029d2c92c9b1b48a163202b97d393dec9481320cd14b1938baa282ce6":
        ("IBM051", "chsh-game", 225, 9),
    "4710386ae5132269bef68865323170020d169b002601db142d2bd3160c77ec30":
        ("IBM052", "qiskit-implementation", 75, 1),
    "bff12f864adf9f56a0e17f5cdacf3087a19336a12c51db1f5e4d34126fa04ff1":
        ("IBM053", "introduction", 0, 0),
    "1338b8f7c27667ecf3b15be528e9903a9972752a2fb4586f954300243f15361b":
        ("IBM054", "repetition-codes", 82, 14),
    "8b549b58df4680202abea8df49626546f181312d295097193be00c2ef34c8cbe":
        ("IBM055", "shor-code", 109, 11),
    "d76193c45a2764e34600f9339932793c49bf9aef6c2fcc504f34b11e56c6b8dc":
        ("IBM056", "discretization-of-errors", 50, 0),
    "6a7b20516a4f377e7a6ffcd43d38792cd5a427d1d45b781d736da0631a70f306":
        ("IBM057", "introduction", 0, 0),
    "0433727528907ded030073bbbf7ee5a0660767aa7be20eccaf62fd6607f59f7b":
        ("IBM058", "pauli-operations-and-observables", 105, 4),
    "8c130abce137e248aa0e3bf1ee7cffacefd66ccd8700cf8cbe31a321d2ae333a":
        ("IBM059", "repetition-code-revisited", 79, 2),
    "3d9008806bedf42d297a5206c86df441a937583cbe8336d8c1e41728928b6d07":
        ("IBM060", "stabilizer-codes", 286, 2),
    "68783d5d9bff267c13bdbf6373323ea5b2a62dfbd722e13d236e8e4de4b0316c":
        ("IBM061", "introduction", 0, 0),
    "41cd48f6fa424f1ebd9b8821826ae61b80da341d3b32e9cd1889f456c28d7646":
        ("IBM062", "css-codes", 274, 0),
    "cec837552067f7ac49ceb6f1e012acfc42d2c53cbdd74869209135f23b83efff":
        ("IBM063", "toric-code", 134, 14),
    "74ead1b72d7283a14c0c3cf9049a4a2ec0b85dbab8f1ad66812ab6530037ee65":
        ("IBM064", "other-code-families", 15, 4),
}
lesson, slug, math_count, image_count = lessons[digest]
if args.lesson and lesson != args.lesson:
    parser.error(f"Expected {args.lesson}, got {lesson}")
cells = json.loads(data)["cells"]
types = Counter(c["cell_type"] for c in cells)
single_systems = lesson in {"IBM036","IBM037","IBM038","IBM039"}
multiple_systems = lesson in {"IBM040","IBM041","IBM042","IBM043"}
# Most lessons consist of a single Markdown cell.
expected_cells = {
    "IBM037": (2,0), "IBM038": (2,0), "IBM039": (19,18),
    "IBM041": (2,0), "IBM042": (2,0), "IBM043": (10,10),
    "IBM046": (2,0), "IBM047": (2,0), "IBM049": (2,0), "IBM050": (2,0),
    "IBM051": (2,0), "IBM052": (22,19), "IBM068": (2,0),
    "IBM069": (10,7), "IBM070": (5,1), "IBM071": (11,13), "IBM072": (11,0),
    "IBM073": (2,0), "IBM074": (10,0), "IBM078": (4,0), "IBM079": (12,0),
}.get(lesson, (1,0))
assert (types["markdown"],types["code"]) == expected_cells and sum(expected_cells) == len(cells)
math = re.compile(r"(?<!\\)(\$\$|\$).*?(?<!\\)\1", re.DOTALL)
rows, figures, cache = [], [], {}
panels = []
for index, cell in enumerate(cells):
    if cell["cell_type"] != "markdown":
        continue
    body = "".join(cell["source"])
    for match in math.finditer(body):
        i = len(rows)+1
        literal = match.group()
        if literal not in cache:
            result = subprocess.run([worker, "--json"], input=("quantum:" + literal).encode(),
                                    capture_output=True, timeout=60)
            if result.returncode == 0:
                try:
                    value = json.loads(result.stdout)
                except UnicodeDecodeError as error:
                    cache[literal] = dict(status="invalid-encoding", offset=error.start,
                                          output_hex=result.stdout.hex())
                else:
                    cache[literal] = dict(status="approximate" if value["approximate"] else "exact",
                                          display=value["display_text"], copy=value["copy_text"])
            elif result.returncode == 2 and result.stderr.strip():
                cache[literal] = dict(status="diagnostic", message=result.stderr.decode().strip())
            else:
                raise RuntimeError((literal, result.returncode, result.stderr))
        rows.append(dict(id=f"{lesson}-{digest[:8]}-M{i:03d}", cell=index, start=match.start(),
                         end=match.end(), literal=literal, **cache[literal]))
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", body):
        figures.append(dict(cell=index, start=match.start(), end=match.end(), alt=match[1], path=match[2]))
    cell_panels = [dict(title=m[1],cell=index,start=m.start(),end=m.end())
                   for m in re.finditer(r'<Figure title="([^"]+)">(.*?)</Figure>', body, re.DOTALL)]
    assert len(cell_panels) == body.count("<Figure")
    panels.extend(cell_panels)
assert len(rows) == math_count and len(figures) == image_count
chapter = "phase-estimation-and-factoring" if lesson in ("IBM028", "IBM029") else "grover-algorithm"
course = "fundamentals-of-quantum-algorithms"
if single_systems:
    course,chapter = "basics-of-quantum-information","single-systems"
if multiple_systems:
    course,chapter = "basics-of-quantum-information","multiple-systems"
if lesson in {"IBM044","IBM045","IBM046","IBM047"}:
    course,chapter = "basics-of-quantum-information","quantum-circuits"
if lesson in {"IBM048","IBM049","IBM050","IBM051","IBM052"}:
    course,chapter = "basics-of-quantum-information","entanglement-in-action"
if lesson in {"IBM053","IBM054","IBM055","IBM056"}:
    course,chapter = "foundations-of-quantum-error-correction","correcting-quantum-errors"
if lesson in {"IBM057","IBM058","IBM059","IBM060"}:
    course,chapter = "foundations-of-quantum-error-correction","stabilizer-formalism"
if lesson in {"IBM061","IBM062","IBM063","IBM064"}:
    course,chapter = "foundations-of-quantum-error-correction","quantum-code-constructions"
if lesson in {"IBM065","IBM066","IBM067","IBM068"}:
    course,chapter = "foundations-of-quantum-error-correction","fault-tolerant-quantum-computing"
if "IBM069" <= lesson <= "IBM073":
    course,chapter = "use-a-qc-today",""
elif "IBM074" <= lesson <= "IBM079":
    course,chapter = "quantum-computing-in-practice",""
path = "/".join(part for part in (course,chapter,slug) if part)
source = ("https://github.com/Qiskit/documentation/blob/f842259423a7adc9adeafd54153cdb5d3c5b680b/"
          f"learning/courses/{path}.ipynb")
counts = Counter(row["status"] for row in rows)
report = dict(source=source, source_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              revision=args.revision, mode="Quantum notation", markdown_cells=types["markdown"], code_cells=types["code"],
              summary=counts, figures=figures, rows=rows)
if panels:
    report["panels"] = panels
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
print(dict(counts))

