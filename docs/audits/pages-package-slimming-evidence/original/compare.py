import json,hashlib
from pathlib import Path
from collections import defaultdict
root=Path('/workspace/mtgo-data');out=Path('/workspace/scratch/pages-slimming');site=out/'extracted';online=out/'online/site'
baseline=json.loads((out/'baseline.json').read_bytes());changed=[];missing=[]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for name,item in baseline['files'].items():
 p=root/name
 if not p.is_file():missing.append(name)
 elif p.stat().st_size!=item['bytes'] or digest(p)!=item['sha256']:changed.append(name)
assert not changed and not missing,(changed,missing)
removed={'data','data_raw','reports','fetched.txt'}
retained=[n for n in baseline['selected'] if n.split('/')[0] not in removed]
for name in retained:assert digest(site/name)==baseline['files'][name]['sha256'],name
candidate={p.relative_to(site).as_posix():p for p in site.rglob('*') if p.is_file()}
assert not any(n.split('/')[0] in removed for n in candidate)
for name,p in candidate.items():
 if name not in retained and name not in {'.nojekyll','.product-version.json'}:
  assert name.startswith(('assets/card-cache/v1/','assets/card-localization/'))
  assert digest(p)==digest(online/name),name
bydir=defaultdict(lambda:{'files':0,'bytes':0})
for name,p in candidate.items():
 d=bydir[name.split('/')[0]];d['files']+=1;d['bytes']+=p.stat().st_size
manifest=json.loads((out/'candidate/manifest.json').read_bytes());total=sum(d['bytes'] for d in bydir.values())
assert total==manifest['expanded_bytes'];assert len(candidate)==manifest['file_count']
oldselected=sum(baseline['files'][n]['bytes'] for n in baseline['selected']);retainedbytes=sum(baseline['files'][n]['bytes'] for n in retained)
online_differences=[n for n in retained if not (online/n).is_file() or digest(online/n)!=digest(site/n)]
report={'base_head':baseline['head'],'all_baseline_files_checked':len(baseline['files']),'changed':changed,'missing':missing,'retained_files':len(retained),'retained_bytes':retainedbytes,'old_selected_bytes':oldselected,'old_selected_files':len(baseline['selected']),'same_inputs_full_old_package_bytes':oldselected+total-retainedbytes,'same_inputs_full_old_package_files':len(baseline['selected'])+len(candidate)-len(retained),'removed_bytes':oldselected-retainedbytes,'expanded_bytes':total,'file_count':len(candidate),'by_directory':dict(bydir),'maximum_bytes':1000000000,'remaining_bytes':1000000000-total,'online_retained_differences':online_differences,'archive_bytes':(out/'candidate/product.tar.gz').stat().st_size,'id':manifest['id']}
(out/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
