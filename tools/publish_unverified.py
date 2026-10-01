#!/usr/bin/env python3
"""Publish incomplete notebook references without executing code or claiming verification."""
from pathlib import Path
import argparse,datetime as dt,fcntl,hashlib,html,json,re,subprocess,sys
import publication as verified
REPO=verified.REPO
MANIFEST=REPO/'unverified.json'
PAGE=REPO/'UNVERIFIED.md'

def clean(value):
    return str(value).replace('\x00','').strip()[:1600]

def render(data):
    verified_ids={e['public_id'] for e in verified.load_manifest()['notebooks']}
    rows=[]
    for e in data['notebooks']:
        if e['public_id'] in verified_ids:continue
        notebook=e['notebook_path'];colab=f'https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/{notebook}'
        reason=html.escape(e['reason']).replace('|','&#124;').replace('\n','<br>')
        title=html.escape(e['title']).replace('|','&#124;')
        rows.append(f'| **{title}**<br>`{e["public_id"]}`<br>[Open in Colab]({colab}) · [Notebook]({notebook}) · [PhenoPaper](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{e["public_id"]}) | **Unverified / incomplete** · {e["created_on"]}<br>Attempt: {e["status"]}<br>{reason} |')
    return '# Unverified and incomplete notebooks\n\nThese are reference drafts, not execution-verified reproductions. They may stop partway, require authenticated data access, contain implementation errors, or be incomplete. No manual login validation was performed. Read each notebook’s opening notice before running it. Saved draft outputs are cleared; failure evidence remains in the DGX run logs. A stopped attempt does not establish that the paper is impossible to reproduce.\n\n未検証・途中までのNotebookです。停止理由を添えて参考資料として公開しています。検証済み件数には含めません。\n\n[Execution-verified notebooks](README.md#notebooks)\n\n| Paper / notebook | Status and stopping reason |\n| --- | --- |\n'+'\n'.join(rows)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('render');pub=sub.add_parser('publish')
    pub.add_argument('--public-id',required=True);pub.add_argument('--run-dir',type=Path,required=True)
    pub.add_argument('--reason',required=True);pub.add_argument('--status',choices=['failed','blocked'],required=True)
    a=p.parse_args()
    if a.command=='render':
        if MANIFEST.exists():PAGE.write_text(render(json.loads(MANIFEST.read_text())))
        return
    if not verified.PUBLIC_ID.fullmatch(a.public_id):raise ValueError('Invalid paper identifier')
    run=a.run_dir.resolve();root=Path.home()/'phenotyping-colab'/'runs'
    if root.resolve() not in run.parents:raise ValueError('Run must be inside the Colab authoring runs directory')
    api=json.loads((run/'sources/paper_api.json').read_text())['data']
    if api.get('public_id')!=a.public_id:raise ValueError('Saved paper identity mismatch')
    source=run/'deliverables'/f'{a.public_id}.ipynb'
    if not source.is_file():print(json.dumps({'skipped':'no_notebook'}));return
    raw=source.read_bytes()
    if len(raw)>10_000_000:raise ValueError('Draft notebook is too large')
    nb=json.loads(raw)
    if nb.get('nbformat')!=4 or not isinstance(nb.get('cells'),list):raise ValueError('Not a notebook')
    cells=nb['cells'];code=[c for c in cells if c.get('cell_type')=='code' and ''.join(c.get('source',[])).strip()]
    if not code:print(json.dumps({'skipped':'no_code_cells'}));return
    reason=clean(a.reason)
    if re.search(r'(?i)Bearer\s+[A-Za-z0-9._~+/-]{8,}',json.dumps(nb)):raise ValueError('Draft contains a bearer credential')
    for c in cells:
        if c.get('cell_type')=='code':c['outputs']=[];c['execution_count']=None
    notice=f'# UNVERIFIED / INCOMPLETE NOTEBOOK\n\n**未検証・途中までの参考Notebookです。** 全セルの実行成功は確認していません。\n\n**Stopping reason:** {reason}\n\nAttempt status: {a.status}. No manual login validation was performed. This draft may require your own authorized access, fail partway, or contain incomplete code. This attempt does not establish that the paper cannot be reproduced.\n\nPaper: {api["title"]}\n\n[PhenoPaper record](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{a.public_id})\n'
    cells.insert(0,{'cell_type':'markdown','metadata':{},'source':notice.splitlines(keepends=True)})
    output=(json.dumps(nb,ensure_ascii=False,indent=1)+'\n').encode()
    digest=hashlib.sha256(output).hexdigest();path=f'notebooks/unverified/{a.public_id}.ipynb'
    investigation=api.get('investigation') or {}
    inv=investigation.get('id') or investigation.get('run',{}).get('id')
    sidecar=run/'queue-result.json'
    if sidecar.exists():inv=json.loads(sidecar.read_text()).get('investigation_run_id') or inv
    if not inv:raise ValueError('Saved investigation identity is missing')
    entry={'public_id':a.public_id,'title':api['title'],'investigation_run_id':inv,'status':a.status,'reason':reason,'created_on':dt.date.today().isoformat(),'notebook_path':path,'notebook_sha256':digest,'source_sha256':hashlib.sha256(raw).hexdigest(),'code_cells':len(code)}
    with (REPO/'.git/publication.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        if verified.git('status','--porcelain'):raise ValueError('Publication checkout has uncommitted changes')
        verified.ensure_github_access();verified.git('pull','--ff-only','origin','main')
        if any(e['public_id']==a.public_id for e in verified.load_manifest()['notebooks']):print(json.dumps({'skipped':'already_verified'}));return
        data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':1,'notebooks':[]}
        data['notebooks']=[e for e in data['notebooks'] if e['public_id']!=a.public_id]+[entry]
        target=REPO/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(output)
        MANIFEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');PAGE.write_text(render(data))
        readme=verified.README.read_text()
        if '[Unverified and incomplete notebooks](UNVERIFIED.md)' not in readme:
            readme=readme.replace('## Notebooks','## Unverified references\n\n[Unverified and incomplete notebooks](UNVERIFIED.md) — drafts and stopped attempts, with reasons. Excluded from the execution-verified count.\n\n## Notebooks',1)
            verified.README.write_text(readme)
        verified.git('add','--',path,'unverified.json','UNVERIFIED.md','README.md')
        if verified.git('diff','--cached','--name-only'):verified.git('commit','-m',f'Publish unverified notebook reference {a.public_id}')
        verified.git('push','origin','main')
        commit=verified.git('rev-parse','HEAD')
        if verified.git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Remote publication commit mismatch')
    print(json.dumps({'repository_commit':commit,'notebook_sha256':digest,'public_id':a.public_id,'investigation_run_id':inv,'notebook_path':path}))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,json.JSONDecodeError,subprocess.CalledProcessError) as e:print(str(e),file=sys.stderr);sys.exit(1)
