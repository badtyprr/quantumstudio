"""Provenance/accounting only: IBM026 contains no mathematical examples."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
source = (root / 'source.ipynb').read_bytes()
expected = 'ce4e2e6a9fa01f1d6a65551f0dff19740e524620bb41c434f9bd9e3f1f310787'
if sha(source) != expected:
    raise AssertionError('source hash')
inventory = json.loads((root / 'inventory.json').read_bytes())
counts = inventory['counts']
if counts != {'math': 0, 'images': 0, 'figures': 0, 'headings': 2,
              'links': 2, 'video_embeds': 1, 'code_cells': 0}:
    raise AssertionError('inventory accounting')
result = {'status': 'source/accounting checks passed; no mathematical validation claimed',
          'source_sha256': expected, 'plan_before_execution_sha256': sha((root / 'research.md').read_bytes()),
          'reference_script_sha256': sha(Path(__file__).read_bytes()),
          'mathematical_case_count': 0, 'counts': counts, 'media_acquired': False,
          'limitations': ['No mathematical examples in this body', 'Video/slides uninspected',
                          'No native/SDK/GUI execution or whole-lesson acceptance']}
(root / 'reference-results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
