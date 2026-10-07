#!/usr/bin/env python3
"""Publish a completed, deliberately reduced Colab demonstration."""
from pathlib import Path
import argparse,datetime as dt,fcntl,hashlib,html,json,re,subprocess,sys
import generation
import publication as verified
REPO=verified.REPO
MANIFEST=REPO/'partially_verified.json'
PAGE=REPO/'PARTIALLY_VERIFIED.md'
README=verified.README
PUBLIC_ID=verified.PUBLIC_ID

def clean(value,field):
    if not isinstance(value,str) or not value.strip() or len(value)>1800 or any(c in value for c in '\\r\\n<>|'):
        raise ValueError(f'Invalid {field}')
    return value.strip()

def render(data):
    verified_ids={e['public_id'] for e in verified.load_manifest()['notebooks']}
    rows=[]
    for e in sorted((x for x in data['notebooks'] if x['public_id'] not in verified_ids),key=lambda x:(x['validated_on'],x['public_id']),reverse=True):
        pid=e['public_id'];title=html.escape(e['title']).replace('|','&#124;')
        reason=html.escape(e['limitation']).replace('|','&#124;')
        demo=html.escape(e['demonstration']).replace('|','&#124;')
        path=f'notebooks/partially-verified/{pid}.ipynb'
        colab=f'https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/{path}'
        paper=f'https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{pid}'
        rows.append(f'| **{title}**<br>`{pid}`<br>[Open in Colab]({colab}) · [GitHub notebook]({path}) · [PhenoPaper]({paper}) | **Partially verified** · {e["validated_on"]} · {e["compute"]}<br><b>Generated with:</b> {html.escape(generation.summary(e.get('generation')))}<br>{demo}<br><b>Limitation:</b> {reason} |')
    if not rows: rows=['| No partially verified notebooks have been published yet. | — |']
    return '# Partially verified notebooks\\n\\nThese notebooks completed a fresh Colab run for the stated reduced scope. They do not verify omitted training conditions or paper-level results. The recorded limitation is part of each result.\\n\\n| Paper / notebook | Executed scope and limitation |\\n| --- | --- |\\n'+'\\n'.join(rows)+'\\n'

def main():
    ap=argparse.ArgumentParser()
    for name in ('public-id','run-dir','executed-output','cli-log','compute','validated-on','demonstration','limitation'):
        ap.add_argument('--'+name,required=True,type=Path if name in ('run-dir','executed-output','cli-log') else str)
    a=ap.parse_args()
    if not PUBLIC_ID.fullmatch(a.public_id): raise ValueError('Invalid public_id')
    run=a.run_dir.resolve();final=run/'deliverables'/f'{a.public_id}.ipynb';api=run/'sources/paper_api.json';report=run/'deliverables/report.md'
    if not all(x.is_file() for x in (final,api,report,a.executed_output,a.cli_log)): raise ValueError('Partial run artifacts are incomplete')
    record=json.loads(api.read_text())['data']
    if record.get('public_id')!=a.public_id: raise ValueError('Saved PhenoPaper public_id mismatch')
    f=verified.check_notebook(final);o=verified.check_notebook(a.executed_output.resolve())
    if verified.notebook_sources(f['notebook'])!=verified.notebook_sources(o['notebook']): raise ValueError('Notebook source differs from executed output')
    if [c.get('outputs',[]) for c in f['notebook']['cells'] if c.get('cell_type')=='code'] != [c.get('outputs',[]) for c in o['notebook']['cells'] if c.get('cell_type')=='code']: raise ValueError('Notebook output differs from archived execution')
    count=len(verified.notebook_sources(f['notebook']));log=a.cli_log.read_text(errors='replace')
    records=re.findall(r'^\\[colab\\] Executing cell (\\d+)/(\\d+) -',log,re.M)
    if records != [(str(i),str(count)) for i in range(1,count+1)] or not re.search(r'^\\[colab\\] Saving notebook with outputs to ',log,re.M): raise ValueError('Colab log does not show successful full notebook execution')
    compute=clean(a.compute,'compute')
    if compute not in {'CPU','T4 GPU','CPU + T4 GPU'}: raise ValueError('Invalid compute label')
    date=clean(a.validated_on,'validated_on');dt.date.fromisoformat(date)
    entry={'generation':generation.for_run(run),'public_id':a.public_id,'title':clean(record['title'],'title'),'compute':compute,'validated_on':date,'demonstration':clean(a.demonstration,'demonstration'),'limitation':clean(a.limitation,'limitation')}
    with (REPO/'.git/publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if verified.git('status','--porcelain'): raise ValueError('Publication checkout has uncommitted changes')
        verified.ensure_github_access();verified.git('pull','--ff-only','origin','main')
        if any(x['public_id']==a.public_id for x in verified.load_manifest()['notebooks']): raise ValueError('Fully verified notebook already exists; use the verified publication path')
        data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':1,'notebooks':[]}
        data['notebooks']=[x for x in data['notebooks'] if x['public_id']!=a.public_id]+[entry]
        path=Path('notebooks/partially-verified')/f'{a.public_id}.ipynb';target=REPO/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(final.read_bytes());MANIFEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\\n');PAGE.write_text(render(data))
        readme=README.read_text();link='[Partially verified notebooks](PARTIALLY_VERIFIED.md)'
        if link not in readme: readme=readme.replace('## Notebooks',f'## Partially verified\\n\\n{link} — executed reduced-scope examples with limitations. Excluded from the verified count.\\n\\n## Notebooks',1)
        README.write_text(readme)
        README.write_text(verified.render(verified.load_manifest()),encoding='utf-8')
        unv=REPO/'unverified.json'
        if unv.exists():
            u=json.loads(unv.read_text());u['notebooks']=[x for x in u.get('notebooks',[]) if x['public_id']!=a.public_id];unv.write_text(json.dumps(u,ensure_ascii=False,indent=2)+'\\n')
        failures=REPO/'failures.json'
        if failures.exists():
            q=json.loads(failures.read_text());q['failures']=[x for x in q.get('failures',[]) if x['public_id']!=a.public_id];failures.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\\n')
        if unv.exists() or failures.exists(): subprocess.run([sys.executable,str(REPO/'tools/publish_unverified.py'),'render'],check=True)
        files=[str(path),'partially_verified.json','PARTIALLY_VERIFIED.md','README.md']
        for fn in ('unverified.json','UNVERIFIED.md','failures.json','FAILED.md'):
            if (REPO/fn).exists(): files.append(fn)
        verified.git('add','--',*files);verified.git('commit','-m',f'Publish partially verified notebook {a.public_id}');verified.git('push','origin','main')
        commit=verified.git('rev-parse','HEAD')
        if verified.git('ls-remote','origin','refs/heads/main').split()[0]!=commit: raise ValueError('Remote publication commit mismatch')
    print(json.dumps({'public_id':a.public_id,'repository_commit':commit,'notebook_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'notebook_path':str(path)}))
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,json.JSONDecodeError,subprocess.CalledProcessError) as e: print(str(e),file=sys.stderr);sys.exit(1)
