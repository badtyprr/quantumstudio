"""Replay the 14 illustrated entanglement protocols and verify the original artwork."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("figures", type=Path, help="Directory of original figures from the pinned notebooks")
parser.add_argument("--record", action="store_true", help="Write the reference report")
args = parser.parse_args()
directory = Path(__file__).resolve().parent
report = directory / "ibm048-figures.json"
checks = {}
bits = (0, 1)

# Project Q and A onto their measured bits after CNOT(Q,A) and H(Q).
# Keep the reference index throughout. Bob applies X controlled by A then Z by Q.
for dimension in (1, 2, 3):
    state = [complex(q + r + 1, 2*q - r) for q, r in itertools.product(bits, range(dimension))]
    norm = math.sqrt(sum(abs(z)**2 for z in state))
    state = [z/norm for z in state]
    for m_q, m_a in itertools.product(bits, repeat=2):
        branch = [0j] * len(state)
        for q, b, r in itertools.product(bits, bits, range(dimension)):
            if b ^ q == m_a:
                corrected = b ^ m_a
                phase = (-1)**(q*m_q + corrected*m_q)
                branch[corrected*dimension+r] += phase*state[q*dimension+r]/2
        assert all(abs(2*z-w) < 1e-13 for z, w in zip(branch, state))
for name in ("teleportation.svg", "teleportation-time-steps.svg", "teleportation-with-entanglement.svg"):
    checks[name] = "Q controls CNOT onto A, then H on Q. A controls Bob's X and Q controls his Z. Each branch has probability 1/4 and preserves the complex input including its reference."

for c, d in itertools.product(bits, repeat=2):
    output = [0.] * 4
    for bell, top in itertools.product(bits, repeat=2):
        alice = bell ^ c
        bottom = bell ^ alice
        output[2*bottom + top] += (-1)**(bell*d + alice*top)/2
    assert output[2*c+d] == (-1)**(c*d)
    assert sum(z*z for z in output) == 1
for name in ("superdense-coding.svg", "superdense-coding.avif"):
    checks[name] = "d controls Z then c controls X. The transmitted wire controls CNOT and passes through H. Read d on that wire and c on the target. All four messages decode."

wins = []
for a0, a1, b0, b1 in itertools.product(bits, repeat=4):
    wins.append(sum(((a0,a1)[x] ^ (b0,b1)[y]) == (x & y) for x,y in itertools.product(bits,repeat=2)))
assert max(wins) == 3
checks["nonlocal-game.avif"] = "Separate local response functions receive x and y. The best of 16 deterministic strategies wins three of four inputs."
checks["nonlocal-game-entanglement.avif"] = "The players receive a shared state before the referee sends separate inputs. The Bell-state strategy below beats 3/4."
checks["CHSH.avif"] = "Open and filled controls select Bob's angles +pi/8 and -pi/8 and Alice's angles 0 and pi/4."
for x,y in itertools.product(bits, repeat=2):
    alpha, beta = x*math.pi/4, (1-2*y)*math.pi/8
    def basis(theta, bit):
        angle = theta + bit*math.pi/2
        return math.cos(angle), math.sin(angle)
    probability = 0
    for a,b in itertools.product(bits, repeat=2):
        amplitude = sum(u*v for u,v in zip(basis(alpha,a), basis(beta,b))) / math.sqrt(2)
        if a ^ b == x & y:
            probability += amplitude**2
    assert abs(probability - (2+math.sqrt(2))/4) < 1e-14
    checks[f"strategy{x}{y}.avif"] = f"Alice angle {x}*pi/4 and Bob angle {1-2*y}*pi/8. The illustrated bases win with probability (2+sqrt(2))/4."
for name, angle in (("alpha-basis.avif", math.pi/4), ("beta-basis.avif", math.pi/8)):
    assert abs(sum(u*v for u,v in zip(basis(angle,0), basis(angle,1)))) < 1e-14
    checks[name] = "The second vector is a positive quarter-turn from the first and their dot product is zero."

records = []
for lesson in range(48,53):
    inventory = json.loads((directory/f"ibm{lesson:03}-inventory.json").read_bytes())
    for figure in inventory["figures"]:
        name = Path(figure["path"]).name
        digest = hashlib.sha256((args.figures/name).read_bytes()).hexdigest()
        records.append(dict(lesson=lesson, path=figure["path"], sha256=digest, check=checks.pop(name)))
assert not checks and len(records) == 14
if args.record:
    report.write_text(json.dumps(records, indent=2)+"\n", encoding="utf-8")
else:
    assert records == json.loads(report.read_bytes())
print("Verified 14 source figures and their protocol checks.")
