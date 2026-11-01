"""Retrieve pinned DEV-11 IBM notebooks; report any content drift, never overwrite snapshots."""
import argparse,datetime,hashlib,json,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
manifest=json.loads(Path(__file__).with_name('source-manifest.json').read_text())
a.output.mkdir(parents=True,exist_ok=False);results=[]
for row in manifest:
 entry={'id':row['id'],'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':row['notebook']['url']}
 try:
  with urllib.request.urlopen(urllib.request.Request(entry['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as r:data=r.read();entry['http_status']=r.status
  json.loads(data)['cells'];(a.output/(row['id']+'.ipynb')).write_bytes(data)
  entry['sha256']=hashlib.sha256(data).hexdigest();entry['matches_pinned']=entry['sha256']==row['notebook']['sha256']
 except Exception as e:entry['error']=str(e)
 results.append(entry);print(entry)
(a.output/'retrieval.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
# probe.py reads the adjacent manifest; preserve the pinned provenance separately from this fresh retrieval.
# Source hashes are checked again by probe.py against its checked-in manifest.
raise SystemExit(0 if all(r.get('matches_pinned') for r in results) else 1)
