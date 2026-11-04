"""Inventory the pinned next IBM-019 section without changing source text."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PIN = 'c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f'
URL = 'https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm.ipynb'


def inventory(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError('Source differs from retained IBM-019 snapshot')
    nb = json.loads(raw)
    cell = nb['cells'][0]
    source = ''.join(cell['source'])
    heading = '## Further remarks on the phase kickback'
    start = source.index(heading)
    section = source[start:]
    formulas = []
    # Display math is consumed before inline math, retaining source offsets.
    for match in re.finditer(r'\$\$([\s\S]*?)\$\$|(?<!\\)\$([^$]*?)(?<!\\)\$', section):
        original = match.group(1) if match.group(1) is not None else match.group(2)
        formulas.append(dict(id=f'P{len(formulas)+1:02}',
                             kind='display' if match.group(1) is not None else 'inline',
                             original=original, offset=match.start(),
                             cell_offset=start+match.start(),
                             sha256=hashlib.sha256(original.encode()).hexdigest()))
    images = re.findall(r'!\[([^]]*)\]\(([^)]+)\)', section)
    assert section.count('$') == sum(4 if f['kind'] == 'display' else 2 for f in formulas)
    assert not images and '<Figure' not in section and '```' not in section
    cells = []
    for index, c in enumerate(nb['cells']):
        text = ''.join(c['source'])
        cells.append(dict(index=index, id=c.get('id'), type=c['cell_type'],
                          sha256=hashlib.sha256(text.encode()).hexdigest(),
                          execution='not executed',
                          source=text if c['cell_type'] == 'code' else None))
    return section, dict(section=heading[3:], source_url=URL, notebook_sha256=PIN,
                         cell_id=cell['id'], cell_index=0, start_offset=start,
                         boundary='heading inclusive to end of markdown cell 0',
                         section_sha256=hashlib.sha256(section.encode()).hexdigest(),
                         formulas=formulas, diagrams=images, code_cells=[],
                         notebook_cells=cells,
                         note='Notebook code inventory is routing information, not SDK execution or coverage.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    section, result = inventory(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'section.md').write_text(section, encoding='utf-8', newline='\n')
    (args.output/'inventory.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(formulas=len(result['formulas']), displays=sum(f['kind']=='display' for f in result['formulas']), diagrams=0, code_cells=0)))


if __name__ == '__main__':
    main()
