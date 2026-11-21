"""Replay the code parameters and error counts illustrated in IBM's 34-slide lecture."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("pdf",type=Path)
parser.add_argument("--record",action="store_true")
args=parser.parse_args()

def masks(word):
    return (int("".join(str(int(g in "XY")) for g in word),2),
            int("".join(str(int(g in "ZY")) for g in word),2))

def syndrome(word,checks):
    x,z=word
    return tuple(((x&b)^(z&a)).bit_count()%2 for a,b in checks)

def group(checks):
    elements={(0,0)}
    for a,b in checks:
        elements.update([(x^a,z^b) for x,z in elements])
    return elements

families={
    "bit repetition":["ZZI","IZZ"], "phase repetition":["XXI","IXX"],
    "Bell":["ZZ","XX"], "GHZ":["ZZI","IZZ","XXX"],
    "Shor":["ZZIIIIIII","IZZIIIIII","IIIZZIIII","IIIIZZIII","IIIIIIZZI","IIIIIIIZZ","XXXXXXIII","IIIXXXXXX"],
    "Steane":["ZZZZIII","ZZIIZZI","ZIZIZIZ","XXXXIII","XXIIXXI","XIXIXIX"],
    "five qubit":["XZZXI","IXZZX","XIXZZ","ZXIXZ"]}
dimensions={}
for name,words in families.items():
    checks=list(map(masks,words))
    assert all(not any(syndrome(w,checks)) for w in checks)
    size=len(group(checks))
    assert size==2**len(words)
    dimensions[name]=2**len(words[0])//size
assert dimensions=={"bit repetition":2,"phase repetition":2,"Bell":1,"GHZ":1,"Shor":2,"Steane":2,"five qubit":2}

checks=list(map(masks,families["Steane"]))
stabilizer=group(checks)
counts=Counter()
distance=8
for x,z in itertools.product(range(128),repeat=2):
    s=syndrome((x,z),checks)
    counts[s]+=1
    if not any(s) and (x,z) not in stabilizer:
        distance=min(distance,(x|z).bit_count())
assert distance==3 and len(counts)==64 and set(counts.values())=={256}
assert len(stabilizer)==64 and 256//len(stabilizer)==4
for logical in ("IIIIXXX","IIIIZZZ"):
    word=masks(logical)
    assert not any(syndrome(word,checks)) and word not in stabilizer

report=dict(source="https://ibm.box.com/public/static/umposbds8d27cv8rnpsayyaj1k2aw88o.pdf",slides=34,sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
            topics={"1":"Title","2–7":"Pauli operations, finite groups and projective measurement",
                    "8–13":"Repetition parity circuits, bit flips and syndrome eigenspaces",
                    "14–20":"Stabilizer conditions, code examples and dimensions",
                    "21–23":"Projection products and the dimension proof",
                    "24–26":"Clifford operations and the Steane encoder",
                    "27–34":"Three error classes, Steane distance and minimum-weight correction"},
            dimensions=dimensions,steane_paulis=128**2,steane_syndromes=len(counts),
            steane_paulis_per_syndrome=256,steane_classes_per_syndrome=4,steane_distance=distance)
out=Path(__file__).with_name("ibm057-slides.json")
if args.record:out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
else:assert report==json.loads(out.read_bytes())
print("Verified seven code spaces and all 16,384 Steane Pauli error patterns.")
