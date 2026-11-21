"""Read illustrated edge errors and compare their calculated syndromes with the shaded tiles."""
import collections, hashlib, json, re, sys
from pathlib import Path
import xml.etree.ElementTree as ET

def diagram(path):
    paths=[p for p in ET.parse(path).iter() if p.tag.endswith("path")]
    # Legend samples have their own transforms; lattice markers share the grid transform.
    grid=collections.Counter(p.get("transform") for p in paths if "fill:#78a9ff" in p.get("style","")).most_common(1)[0][0]
    errors,corrections,tiles=set(),set(),set()
    for p in paths:
        style=p.get("style","")
        if p.get("transform")!=grid:continue
        d=p.get("d","")
        match=re.match(r"[Mm]\s*([-\d.]+)\s*,\s*([-\d.]+)",d)
        if not match:continue
        x,y=(round(float(v)/10.63038) for v in match.groups())
        if " c " in d:
            if "fill:#ee5396;" in style:errors.add((x%18,y%18))
            if "fill:#fff200;" in style:corrections.add((x%18,y%18))
        elif "fill:#e0e0e0;" in style and "stroke:none" in style:
            cx,cy=(float(v) for v in match.groups())
            xs,ys=[cx],[cy]
            for axis,val in re.findall(r"([HhVv])\s*([-\d.]+)",d[match.end():]):
                n=float(val)
                if axis.lower()=="h":cx=n if axis=="H" else cx+n
                else:cy=n if axis=="V" else cy+n
                xs.append(cx);ys.append(cy)
            tiles.add((round((min(xs)+max(xs))/21.26076)%18,round((min(ys)+max(ys))/21.26076)%18))
    return errors,corrections,tiles

def syndrome(edges):
    ends=set()
    for x,y in edges:
        assert (x+y)%2==1
        dx,dy=(1,0) if x%2==0 else (0,1)
        ends.symmetric_difference_update([((x-dx)%18,(y-dy)%18),((x+dx)%18,(y+dy)%18)])
    return ends

def winding(edges):
    return sum(x==0 for x,y in edges)%2,sum(y==0 for x,y in edges)%2


def rank(rows):
    pivots = {}
    for row in rows:
        while row:
            pivot = row.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = row
                break
            row ^= pivots[pivot]
    return len(pivots)


def lattice():
    edges = [(x, y) for x in range(18) for y in range(18) if (x+y) % 2]
    def incident(x, y):
        return sum(1 << edges.index(((x+dx) % 18, (y+dy) % 18))
                   for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)))
    stars = [incident(x,y) for x in range(0,18,2) for y in range(0,18,2)]
    faces = [incident(x,y) for x in range(1,18,2) for y in range(1,18,2)]
    assert all((s & f).bit_count() % 2 == 0 for s in stars for f in faces)
    ranks = [rank(stars), rank(faces)]
    assert ranks == [80,80] and len(edges) - sum(ranks) == 2
    return dict(edges=len(edges), stars=len(stars), faces=len(faces), ranks=ranks, logical_qubits=2)


# Errors, correction edges, negative checks, and residual winding for closed chains.
cases = {
    "toric-code-bit-flip": (1, 0, 2, None),
    "X-error-chain": (6, 0, 2, None),
    "X-error-loop": (10, 0, 0, (0,0)),
    "X-error-loop-generated": (10, 0, 0, (0,0)),
    "X-error-logical": (13, 0, 0, (0,1)),
    "X-error-correction": (6, 4, 2, (0,0)),
    "correction-complete-error": (7, 4, 2, (1,0)),
    "multiple-correction-chains": (0, 10, 8, None),
}


if __name__ == "__main__":
    result = {"lattice": lattice(), "figures": {}}
    for name, (ne, nc, nt, expected_winding) in cases.items():
        path = Path(sys.argv[1]) / (name + ".svg")
        errors, corrections, tiles = diagram(path)
        assert (len(errors), len(corrections), len(tiles)) == (ne, nc, nt), name
        if errors:
            assert syndrome(errors) == tiles, name
        if corrections:
            assert syndrome(corrections) == tiles, name
        if expected_winding is not None:
            assert not syndrome(errors ^ corrections), name
            assert winding(errors ^ corrections) == expected_winding, name
        result["figures"][name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            errors=ne, corrections=nc, negative_checks=nt, closed_chain_winding=expected_winding)
    print(json.dumps(result, indent=2))
