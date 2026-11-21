"""Fetch each source from its immutable tree and verify Git blob identity before cataloguing."""
import concurrent.futures,hashlib,json,urllib.request,time
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
parser.add_argument("cache",type=Path)
parser.add_argument("--revision",default="079769d205eb3b60e077820060274c7b0359c123")
args=parser.parse_args()
g=args.cache.resolve();g.mkdir(parents=True,exist_ok=True)
repo="Qiskit/documentation"
head=args.revision
def read(url):
    for i in range(4):
        try:return urllib.request.urlopen(url,timeout=30).read()
        except OSError:
            if i==3:raise
            time.sleep(i+1)
tree=json.loads(read(f"https://api.github.com/repos/{repo}/git/trees/{head}?recursive=1"))
assert tree["sha"]==head and not tree["truncated"]
(g/"tree.json").write_text(json.dumps(tree))
files=[r for r in tree["tree"] if r["type"]=="blob" and r["path"].startswith("learning/") and Path(r["path"]).suffix in (".mdx",".ipynb",".json",".md")]
def fetch(r):
    path=r["path"]
    def matches(buf):return hashlib.sha1(f"blob {len(buf)}\0".encode()+buf).hexdigest()==r["sha"]
    dest=g/"sources"/path
    for root in [g/"sources"]:
        p=root/path
        if p.exists():
            buf=p.read_bytes()
            if matches(buf): break
    else:buf=read(f"https://raw.githubusercontent.com/{repo}/{head}/{path}")
    assert matches(buf),path
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists() or not matches(dest.read_bytes()):dest.write_bytes(buf)
    return dict(path=path,blob=r["sha"],size=len(buf),sha256=hashlib.sha256(buf).hexdigest())
with concurrent.futures.ThreadPoolExecutor(5) as pool:rows=list(pool.map(fetch,files))
(g/"manifest.json").write_text(json.dumps(dict(revision=head,sources=rows),indent=2))
print(head,len(rows))
