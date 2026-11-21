"""Replay literal formulas from pinned, IBM quantum lessons."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

def prose_ranges(body):
    """Return offsets outside Markdown fences and matching inline code spans."""
    fence = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})([^\n]*)(?:\n|$)")
    inline = re.compile(r"(?<!`)(`+)(?!`)")
    start = 0
    while start < len(body):
        opening = fence.search(body, start)
        end = opening.start() if opening else len(body)
        part = start
        for marker in inline.finditer(body, start, end):
            if marker.start() < part:
                continue
            close = re.compile(r"(?<!`)"+marker[1]+r"(?!`)").search(body, marker.end(), end)
            if close:
                yield part, marker.start()
                part = close.end()
        yield part, end
        if not opening:
            break
        run = opening[1]
        closing = re.compile(r"(?m)^ {0,3}"+run[0]+"{"+str(len(run))+r",}[ \t]*(?:\n|$)").search(body,opening.end())
        start = closing.end() if closing else len(body)


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
    "ecd16e47b567dcd279cb87bc39377be0faa0e64bb863263654e55e720a7d44e8": ("IBM108", "introduction", 0, 0),
    "0f3a767995ca2b9d4d161107d64bdaf12500687e611b5f16d22292dd67456c6d": ("IBM109", "hamiltonian-construction", 3, 0),
    "3222364ec09800b5b71ca4116ce9a687a17af726ae3bf26f933953bbd7e8485a": ("IBM110", "ansatz", 3, 0),
    "3b4383b5c4827f5f5052a807ce896654aa1d899d0306a11dde48662e4e259bcc": ("IBM111", "classical-optimizers", 2, 0),
    "2047e9348a25dc9b11296a0d4638090409b68f629ffa06b3336256a00641c1bc": ("IBM112", "ground-state", 0, 0),
    "dd8d2e4d69b27a513b2459334485069c212f9070db34992b2fe333ca92cb0510": ("IBM113", "geometry", 2, 0),
    "ee2bde2c607539ab5c8486d074ab30c6f554246452d78a5de08ff1c88a76aa4a": ("IBM101", "variational-algorithms", 52, 1),
    "9861697637e56521556f55ab3154daaa6189f4addef838f4b79b5ec7347194f9": ("IBM102", "reference-states", 24, 2),
    "19874a793666d2b129bb79b9250695273e7f921e6f6f958bb90adc126e131238": ("IBM103", "ansaetze-and-variational-forms", 29, 2),
    "62108930aca4330587cb805357519f56cc57db2e1c651a5d2ad8e529f0a39e58": ("IBM104", "cost-functions", 156, 6),
    "5441242c22ad4d9d40950aab8abf1d2e6b00fcf3063b76ac3e5f08188b12bb3f": ("IBM105", "optimization-loops", 14, 5),
    "ab0d6f7e093c1f04e6095fad2f4d4d651fd4e00aa35baf7f1e2dda220fa310ec": ("IBM106", "instances-and-extensions", 149, 4),
    "0e3777202516059dfac67212bcce290fda4e56db19b3d7f86e8306da3ea33ed0": ("IBM107", "examples-and-applications", 78, 0),
    "aad7521b575bfd6090d4d738b336f1b786d9fce68db4cd7e675b306c200cf381": ("IBM096", "introduction", 19, 2),
    "4b10863c06d14367e736ad245ac715b4d61f3258e7b887ad6c1c46a43d200707": ("IBM097", "classical-ml-review", 65, 10),
    "09806407d3d3d6c7cc24de5f6ea0fd6a0a101f04b37fb8fcfc7eeaafeb2bc2a9": ("IBM098", "data-encoding", 293, 6),
    "76b7eaf248593faf84d322d622c59c40b1cbc9abf897894de0795d422973858b": ("IBM099", "quantum-kernel-methods", 47, 2),
    "1f86ee572a58afff7ba19c7e5f91eb2a0b1e48b1b4b3ae828cd36b678032aad7": ("IBM100", "qvc-qnn", 27, 1),
    "0460de3a26c5a3f217a159e3b479e0a2c717050ccb58aa633483aa9ce8715d8f": ("IBM090", "introduction", 0, 0),
    "868393ba4d27901e99903c1eae71f46b44c333090b546ba70150aa10a8b79b1c": ("IBM091", "vqe", 91, 6),
    "bdde16a26dda202a7be847f4aa4f770fe14edcdee64365c5b6c1cd55b1c6d218": ("IBM092", "krylov", 390, 8),
    "ff65b087e79b955a572000c04e09095e1ebcb9f335b4d96212e40664ba3ee1bf": ("IBM093", "sqd-overview", 117, 3),
    "37477fb6301ec3616c6f1760d58ef621767ddedb8c162f66d7c5b517f3c2e272": ("IBM094", "sqd-implementation", 151, 11),
    "3ed488d16f7bab398f07d32f95853e1767c1de384095e3712598af6309d09f94": ("IBM095", "skqd", 39, 0),
    "087d8957bccb098f16edc550940832756ffa40ad7f70530bb658766fd9b3a29c": ("IBM085", "introduction", 1, 1),
    "e6d3174eb78d569bf79b58972fba0f29e3c6eeb12159a8eeb5f5426e41239760": ("IBM086", "compute-resources", 4, 6),
    "ec12022d6f3dd5b2771dd43f7fb9e4e6c5c4045c27d99198b8dba0923c2c3dbe": ("IBM087", "programming-models", 3, 7),
    "9d14af04bd68ca2df180adbcc18fd95073bdecce98407a8e3bcdc76c146df481": ("IBM088", "sqd-skqd", 31, 4),
    "85d22ff60e747ae7f25d4100e0556721ec291f81a88909d08bdb3a62d3c1c9f2": ("IBM089", "next-steps", 0, 2),
    "472a25ee24bf7f5929d968bb5eb91693207e707ebde0edd2dab3450783b74e7a": ("IBM080", "introduction", 0, 1),
    "7b09f95f2f11ea63b11b77acb937e460060ddcd787a50f65c03abc6ba60fe993": ("IBM081", "noise-and-errors", 309, 9),
    "a3fcfc9e0a84f18267115e9b1597efca99d08deb94a9c5b37b1c8a27eb44dfc5": ("IBM082", "error-suppression", 111, 9),
    "0db143f434dce3c6cf6fc2292c1419efc2fb50402a990306e844069f340072e0": ("IBM083", "error-mitigation", 284, 3),
    "d76bfe7cca292d48e3396c2c1b35c23849ce0e9a22c09b3611f843177811d672": ("IBM084", "error-correction-i", 488, 0),
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
extension = "mdx" if lesson == "IBM080" else "ipynb"
cells = ([{"cell_type": "markdown", "source": data.decode()}] if extension == "mdx"
         else json.loads(data)["cells"])
types = Counter(c["cell_type"] for c in cells)
single_systems = lesson in {"IBM036","IBM037","IBM038","IBM039"}
multiple_systems = lesson in {"IBM040","IBM041","IBM042","IBM043"}
# Most lessons consist of a single Markdown cell.
expected_cells = {
    "IBM108": (1,0),
    "IBM109": (23,19),
    "IBM110": (11,10),
    "IBM111": (4,0),
    "IBM112": (13,12),
    "IBM113": (12,14),
    "IBM101": (7,0),
    "IBM102": (8,4),
    "IBM103": (14,9),
    "IBM104": (31,23),
    "IBM105": (10,6),
    "IBM106": (26,15),
    "IBM107": (55,61),
    "IBM096": (7,1),
    "IBM097": (6,0),
    "IBM098": (45,19),
    "IBM099": (31,30),
    "IBM100": (42,42),
    "IBM090": (3,0),
    "IBM091": (24,15),
    "IBM092": (65,45),
    "IBM093": (34,11),
    "IBM094": (47,11),
    "IBM095": (21,15),
    "IBM085": (10,0),
    "IBM086": (11,0),
    "IBM087": (11,0),
    "IBM088": (7,0),
    "IBM089": (5,0),
    "IBM081": (26,18),
    "IBM082": (41,40),
    "IBM083": (70,74),
    "IBM084": (69,39),
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
    for match in (m for start,end in prose_ranges(body) for m in math.finditer(body,start,end)):
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
elif "IBM080" <= lesson <= "IBM084":
    course,chapter = "tools-for-quantum-advantage",""
elif "IBM085" <= lesson <= "IBM089":
    course,chapter = "integrating-quantum-and-high-performance-computing",""
elif "IBM090" <= lesson <= "IBM095":
    course,chapter = "quantum-diagonalization-algorithms",""
elif "IBM096" <= lesson <= "IBM100":
    course,chapter = "quantum-machine-learning",""
elif "IBM101" <= lesson <= "IBM107":
    course,chapter = "variational-algorithm-design",""
elif "IBM108" <= lesson <= "IBM113":
    course,chapter = "quantum-chem-with-vqe",""
path = "/".join(part for part in (course,chapter,slug) if part)
source = ("https://github.com/Qiskit/documentation/blob/f842259423a7adc9adeafd54153cdb5d3c5b680b/"
          f"learning/courses/{path}.{extension}")
counts = Counter(row["status"] for row in rows)
report = dict(source=source, source_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              revision=args.revision, mode="Quantum notation", markdown_cells=types["markdown"], code_cells=types["code"],
              summary=counts, figures=figures, rows=rows)
if panels:
    report["panels"] = panels
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
print(dict(counts))
