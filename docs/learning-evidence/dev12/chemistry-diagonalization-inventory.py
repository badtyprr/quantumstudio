"""Pin/inventory IBM-090..095 and IBM-108..113. Snapshots stay outside checkout.

Use --fetch only into a new directory. Network payloads are data, never executed.
An existing snapshot must match the checked-in manifest before inventorying.
"""
import argparse
import datetime
import hashlib
import json
import re
import urllib.request
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name('chemistry-diagonalization-source-manifest.json').read_text(encoding='utf-8'))
    if args.fetch:
        args.sources.mkdir(parents=True, exist_ok=False)
    rows = []
    for row in manifest:
        path = args.sources / (row['id'] + '.ipynb')
        if args.fetch:
            request = urllib.request.Request(row['notebook_url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=45) as response:
                path.write_bytes(response.read())
        data = path.read_bytes()
        if digest(data) != row['sha256']:
            raise ValueError('Source drift: ' + row['id'])
        nb = json.loads(data)
        cells = []
        for index, cell in enumerate(nb['cells']):
            source = ''.join(cell['source'])
            outputs = json.dumps(cell.get('outputs', []), ensure_ascii=False, sort_keys=True)
            cells.append(dict(index=index, cell_type=cell['cell_type'],
                              source_sha256=digest(source.encode()), outputs_sha256=digest(outputs.encode()),
                              headings=re.findall(r'^#{1,6} .+', source, re.M),
                              code_fences=len(re.findall(r'^```[^\n]*\n', source, re.M)) // 2,
                              display_equations=len(re.findall(r'\$\$', source)) // 2,
                              links=re.findall(r'https?://[^\s<>"\)]+', source),
                              media_ids=re.findall(r'<IBMVideo[^>]*id="([^"]+)"', source),
                              execution='not executed as notebook'))
        rows.append(dict(id=row['id'], cells=cells, whole_source_certified=False))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  rows=rows, whole_sources_certified=0,
                  total_cells=sum(len(r['cells']) for r in rows),
                  code_cells=sum(c['cell_type'] == 'code' for r in rows for c in r['cells']))
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
