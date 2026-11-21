"""Index glossary and formula definitions from the pinned learning-source manifest."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(cache):
    manifest = json.loads((cache / "manifest.json").read_bytes())
    entries = {}
    notebooks = 0
    for source in manifest["sources"]:
        path = source["path"]
        if not path.endswith(".ipynb"):
            continue
        raw = (cache / "sources" / path).read_bytes()
        if digest(raw) != source["sha256"]:
            raise ValueError(f"Notebook digest mismatch for {path}")
        notebooks += 1
        for index, cell in enumerate(json.loads(raw)["cells"]):
            for field in ("gloss", "formulas"):
                for term, definition in cell["metadata"].get(field, {}).items():
                    # Use the notebook cell ID when available so moving a cell preserves its identity.
                    cell_id = cell.get("id") or f"index:{index}"
                    identity = json.dumps([path, cell_id, field, term], ensure_ascii=False)
                    key = "LM-" + digest(identity.encode())[:16]
                    if key in entries:
                        raise ValueError(f"Duplicate metadata identity in {path}: {term}")
                    canonical = json.dumps(definition, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                    entries[key] = dict(path=path, cell=index, cell_id=cell_id, field=field, term=term,
                                        definition_sha256=digest(canonical.encode()))
    return dict(revision=manifest["revision"], notebooks_checked=notebooks, definitions=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inventory(args.cache), indent=2, sort_keys=True) + "\n", encoding="utf8")
