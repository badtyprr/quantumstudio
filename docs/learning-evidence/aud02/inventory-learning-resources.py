"""Index auditable learning resources in a complete pinned Qiskit documentation learning tree."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin,urlsplit

from markdown_it import MarkdownIt

args=argparse.ArgumentParser()
args.add_argument("cache",type=Path,help="directory containing sources/, tree.json and manifest.json")
args.add_argument("output",type=Path)
a=args.parse_args()
manifest=json.loads((a.cache/"manifest.json").read_bytes())
tree=json.loads((a.cache/"tree.json").read_bytes())
assert not tree["truncated"] and tree["sha"]==manifest["revision"]
parser=MarkdownIt("commonmark")
registry={}
origins=[]
tasks={
    "overview":"Audit the overview, navigation and linked lesson sequence.",
    "exam":"Verify the exam instructions and authorized assessment route.",
    "practice":"Review the question, its answer or rubric, and reproduce any calculation.",
    "video":"Review the video or transcript and audit its worked examples.",
    "notebook":"Verify the original notebook cells, dependencies, execution and outputs.",
    "tutorial":"Follow the referenced tutorial and reproduce its worked examples.",
    "reference":"Verify the linked material and classify any additional learning content.",
    "image":"Inspect the figure and verify any information needed to reproduce the example."}
def add(kind,target,cell):
    key=kind+"\n"+target
    id="LR-"+hashlib.sha256(key.encode()).hexdigest()[:16]
    if id not in registry:registry[id]=dict(kind=kind,target=target,uses=[])
    item=registry[id]
    assert item["kind"]==kind and item["target"]==target
    loc=[len(origins)-1,cell]
    if loc not in item["uses"]:item["uses"].append(loc)
def linked(raw,cell,image=False):
    if not raw or raw.startswith(("#","data:","mailto:","javascript:")):return
    url=urljoin(page,raw)
    url=re.sub(r"^https://quantum\.cloud\.ibm\.com/learning/(courses|modules)(?=/|$)",r"https://quantum.cloud.ibm.com/learning/en/\1",url)
    parts=urlsplit(url)
    if parts.scheme not in ("http","https"):return
    path=parts.path.lower()
    if image:kind="image"
    elif path.endswith(".ipynb"):kind="notebook"
    elif "youtu" in parts.netloc or "video.ibm.com" in parts.netloc:kind="video"
    elif "/tutorial" in path:kind="tutorial"
    elif "/training/course/" in path or path.endswith("/exam"):kind="exam"
    else:kind="reference"
    add(kind,url,cell)
class Components(HTMLParser):
    def __init__(self,cell):super().__init__();self.cell=cell
    def handle_starttag(self,tag,attrs):
        props=dict(attrs)
        if tag=="ibmvideo" and props.get("id"):
            add("video","ibm-video:"+props["id"],self.cell)
        if tag=="iframe" and props.get("src"):
            add("video",urljoin(page,props["src"]),self.cell)
        if tag=="launchexambutton" and props.get("href"):
            add("exam",urljoin(page,props["href"]),self.cell)
        if tag=="a":linked(props.get("href"),self.cell)
        if tag in ("img","figure"):linked(props.get("src"),self.cell,True)
def walk(tokens):
    for token in tokens:
        yield token
        if token.children:yield from walk(token.children)
listed={r["path"]:r for r in manifest["sources"]}
expected={r["path"] for r in tree["tree"] if r["type"]=="blob" and r["path"].startswith("learning/") and Path(r["path"]).suffix in (".mdx",".md",".ipynb",".json")}
assert set(listed)==expected
for path,meta in sorted(listed.items()):
    p=a.cache/"sources"/path
    raw=p.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==meta["sha256"]
    origins.append([path,meta["sha256"]])
    page="https://quantum.cloud.ibm.com/"+str(Path(path).with_suffix("")).replace("\\","/").replace("learning/","learning/en/",1)
    if page.endswith("/index"):page=page[:-6]
    if p.name=="_toc.json":
        def visit(node):
            if isinstance(node,list):
                for x in node:visit(x)
            elif isinstance(node,dict):
                linked(node.get("url"),0);visit(node.get("children",[]))
        visit(json.loads(raw));continue
    if p.stem=="index":add("overview",page,0)
    if p.stem=="exam":add("exam",page,0)
    if p.suffix==".ipynb":
        add("notebook","github:Qiskit/documentation/"+path,0)
        cells=[(i,"".join(c["source"])) for i,c in enumerate(json.loads(raw)["cells"]) if c["cell_type"]=="markdown"]
    else:cells=[(0,raw.decode("utf8"))]
    seen={}
    for i,text in cells:
        # Markdown inside a JSX accordion is still lesson prose. Exclude fenced code.
        lines=text.splitlines();tokens=parser.parse(text)
        for token in tokens:
            if token.type in ("fence","code_block"):
                for j in range(*token.map):lines[j]=""
        clean="\n".join(lines)
        Components(i).feed(clean)
        plain=re.sub(r"</?[A-Z][\w.]*\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>","",clean)
        parsed=parser.parse(plain)
        for tok in walk(parsed):
            if tok.type=="link_open":linked(tok.attrGet("href"),i)
            elif tok.type=="image":linked(tok.attrGet("src"),i,True)
        # Include individually labelled exercises and questions within a practice section.
        for line in plain.splitlines():
            heading=re.match(r"^\s*(?:#{1,6}\s+|\*\*|__)(.{1,180})",line)
            if heading and re.search(r"^(?:exercises?|practice(?:\s+problems?)?|quiz|questions?|problems?\s+\d+|check your (?:understanding|knowledge)|try it yourself)\b",heading[1],re.I):
                label=heading[1].strip("*_ #")
                pos=seen.get(label,0)+1;seen[label]=pos
                add("practice",path+"#"+label+(f" ({pos})" if pos>1 else ""),i)
report=dict(revision=tree["sha"],source_digest_algorithm="SHA-256",tasks=tasks,origins=origins,resources=dict(sorted(registry.items())))
def compact(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",": "))
with a.output.open("w",encoding="utf8",newline="\n") as output:
    output.write("{\n")
    for key in ("revision","source_digest_algorithm","tasks"):
        output.write("  "+compact(key)+": "+compact(report[key])+",\n")
    output.write('  "origins": [\n'+",\n".join("    "+compact(row) for row in origins)+"\n  ],\n")
    output.write('  "resources": {\n'+",\n".join("    "+compact(k)+": "+compact(v) for k,v in report["resources"].items())+"\n  }\n}\n")
from collections import Counter
print(len(origins),dict(Counter(x["kind"] for x in registry.values())))
