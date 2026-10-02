#!/usr/bin/env python3
"""Publish incomplete notebook references and a failure-only attempt log."""
from pathlib import Path
import argparse,datetime as dt,fcntl,hashlib,html,json,re,subprocess,sys
import publication as verified
REPO=verified.REPO
MANIFEST=REPO/'unverified.json'
PAGE=REPO/'UNVERIFIED.md'
FAILURES=REPO/'failures.json'
FAILED_PAGE=REPO/'FAILED.md'
README=verified.README


def clean(value):
    return str(value).replace('\x00','').strip()[:1600]


def load_failures():
    if FAILURES.exists():
        data=json.loads(FAILURES.read_text())
        if data.get('schema_version')!=1 or not isinstance(data.get('failures'),list):
            raise ValueError('failures.json must have schema_version 1 and failures array')
        return data
    return {'schema_version':1,'failures':[]}


def render(data):
    verified_ids={e['public_id'] for e in verified.load_manifest()['notebooks']}
    rows=[]
    for e in data['notebooks']:
        if e['public_id'] in verified_ids:continue
        notebook_path=Path(e.get('notebook_path',''))
        if notebook_path.is_absolute() or '..' in notebook_path.parts or not (REPO/notebook_path).is_file():continue
        notebook=e['notebook_path'];colab=f'https://colab.research.google.com/github/phytometrics/phenopaper-colab-notebooks/blob/main/{notebook}'
        reason=html.escape(e['reason']).replace('|','&#124;').replace('\n','<br>')
        title=html.escape(e['title']).replace('|','&#124;')
        rows.append(f'| **{title}**<br>`{e["public_id"]}`<br>[Open in Colab]({colab}) · [Notebook]({notebook}) · [PhenoPaper](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{e["public_id"]}) | **Unverified / incomplete** · {e["created_on"]}<br>Attempt: {e["status"]}<br>{reason} |')
    return '# Unverified and incomplete notebooks\n\nThis page lists every saved draft notebook that has not passed full execution verification, including drafts from attempts that ended in failure. Use the recorded attempt status and stopping reason to interpret each artifact; a saved draft is not evidence of successful execution. Failed attempts with no saved notebook are listed on [Failed reproduction attempts](FAILED.md).\n\n未検証または途中までのNotebookを、実行結果にかかわらずここに集約しています。作成済みであることは実行成功を意味しません。Notebookを残せなかった失敗試行は[失敗一覧](FAILED.md)を参照してください。\n\n[Execution-verified notebooks](README.md#notebooks)\n\n| Paper / notebook | Status and stopping reason |\n| --- | --- |\n'+'\n'.join(rows)+'\n'


def render_failed(failures, unverified):
    verified_ids={e['public_id'] for e in verified.load_manifest()['notebooks']}
    draft_ids=set()
    for item in unverified['notebooks']:
        notebook_path=Path(item.get('notebook_path',''))
        if not notebook_path.is_absolute() and '..' not in notebook_path.parts and (REPO/notebook_path).is_file():
            draft_ids.add(item['public_id'])
    # A paper with a saved draft belongs only on UNVERIFIED.md; FAILED.md is
    # reserved for failed attempts that produced no public draft artifact.
    by_id={}
    candidates=[*failures['failures'], *(item for item in unverified['notebooks'] if item.get('status')=='failed')]
    candidates.sort(key=lambda e:e.get('created_on',''))
    for entry in candidates:
        if entry['public_id'] in verified_ids or entry['public_id'] in draft_ids:
            continue
        merged={**by_id.get(entry['public_id'],{}),**entry}
        if not merged.get('notebook_path'):
            merged.pop('notebook_path',None)
        by_id[entry['public_id']]=merged
    entries=list(by_id.values())
    entries.sort(key=lambda e:(e.get('created_on',''),e['public_id']),reverse=True)
    rows=[]
    for e in entries:
        public_id=e['public_id'];title=html.escape(e.get('title') or public_id).replace('|','&#124;')
        reason=html.escape(e.get('reason') or 'No detailed reason was recorded.').replace('|','&#124;').replace('\n','<br>')
        links=[f'[PhenoPaper](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{public_id})']
        attempt=e.get('investigation_run_id') or e.get('run_id') or 'run ID not recorded'
        rows.append(f'| **{title}**<br>`{public_id}`<br>{" · ".join(links)} | {e.get("created_on","date unknown")}<br>`{html.escape(str(attempt))}` | {reason} |')
    if not rows:
        rows=['| No failed attempts have been recorded yet. | — | — |']
    return '# Failed reproduction attempts\n\nThis page lists failed attempts that did not leave a saved draft notebook for reference. When a draft exists, the paper appears only on [Unverified and incomplete notebooks](UNVERIFIED.md), with its failure reason and Colab link. A failed attempt does not establish that the paper is irreproducible. Failure details are drawn from queue reports and captured tool diagnostics.\n\nNotebook草稿を残せなかった失敗試行を掲載しています。草稿を保存できた論文は重複させず、未検証一覧に理由とColabリンクをまとめています。失敗は論文が再現不可能であることを意味しません。\n\n[Execution-verified notebooks](README.md#notebooks) · [Unverified and incomplete notebooks](UNVERIFIED.md)\n\n| Paper / record | Failed date / investigation run | Recorded failure reason |\n| --- | --- | --- |\n'+'\n'.join(rows)+'\n'


def ensure_readme_link():
    text=README.read_text()
    label='[Failed reproduction attempts](FAILED.md)'
    if label not in text:
        heading='## Unverified references'
        if heading in text:
            text=text.replace(heading, '## Failed attempts\n\n'+label+' — failed runs and recorded reasons.\n\n'+heading,1)
        else:
            text=text.replace('## Notebooks','## Failed attempts\n\n'+label+' — failed runs and recorded reasons.\n\n## Notebooks',1)
        README.write_text(text)


def save_pages(unverified):
    verified_ids={e['public_id'] for e in verified.load_manifest()['notebooks']}
    # Verified records leave the draft manifest; failures remain in failures.json
    # and failed papers are rendered only on FAILED.md.
    unverified['notebooks']=[e for e in unverified['notebooks'] if e['public_id'] not in verified_ids]
    MANIFEST.write_text(json.dumps(unverified,ensure_ascii=False,indent=2)+'\n')
    PAGE.write_text(render(unverified))
    FAILED_PAGE.write_text(render_failed(load_failures(),unverified))
    ensure_readme_link()


def git_publish(files, message):
    verified.git('add','--',*files)
    if verified.git('diff','--cached','--name-only'):
        verified.git('commit','-m',message)
    verified.git('push','origin','main')
    commit=verified.git('rev-parse','HEAD')
    if verified.git('ls-remote','origin','refs/heads/main').split()[0]!=commit:
        raise ValueError('Remote publication commit mismatch')
    return commit


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('render');sub.add_parser('reconcile');pub=sub.add_parser('publish')
    pub.add_argument('--public-id',required=True);pub.add_argument('--run-dir',type=Path)
    pub.add_argument('--title');pub.add_argument('--reason',required=True);pub.add_argument('--status',choices=['failed','blocked'],required=True)
    a=p.parse_args()
    if a.command in {'render','reconcile'}:
        if a.command=='reconcile':
            with (REPO/'.git/publication.lock').open('a') as handle:
                fcntl.flock(handle,fcntl.LOCK_EX)
                if verified.git('status','--porcelain'):raise ValueError('Publication checkout has uncommitted changes')
                verified.ensure_github_access();verified.git('pull','--ff-only','origin','main')
                data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':1,'notebooks':[]}
                save_pages(data)
                commit=git_publish(['unverified.json','UNVERIFIED.md','FAILED.md','README.md'], 'Reconcile verified, unverified, and failed notebook lists')
            verified_ids={e['public_id'] for e in verified.load_manifest()['notebooks']}
            draft_ids={e['public_id'] for e in data['notebooks'] if not Path(e.get('notebook_path','')).is_absolute() and '..' not in Path(e.get('notebook_path','')).parts and (REPO/Path(e.get('notebook_path',''))).is_file()}
            failed_ids=({e['public_id'] for e in load_failures()['failures']} | {e['public_id'] for e in data['notebooks'] if e.get('status')=='failed'})-verified_ids-draft_ids
            print(json.dumps({'repository_commit':commit,'unverified':len(draft_ids-verified_ids),'failed':len(failed_ids)}))
            return
        data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':1,'notebooks':[]}
        save_pages(data);return
    if not verified.PUBLIC_ID.fullmatch(a.public_id):raise ValueError('Invalid paper identifier')
    reason=clean(a.reason);run=None;root=Path.home()/'phenotyping-colab'/'runs';api={}
    if a.run_dir:
        run=a.run_dir.resolve()
        if root.resolve() not in run.parents:raise ValueError('Run must be inside the Colab authoring runs directory')
        api_path=run/'sources/paper_api.json'
        if api_path.exists():
            api=json.loads(api_path.read_text())['data']
            if api.get('public_id')!=a.public_id:raise ValueError('Saved paper identity mismatch')
    title=(api.get('title') if api else None) or a.title or a.public_id
    inv=None;sidecar=(run/'queue-result.json') if run else None
    if api:
        investigation=api.get('investigation') or {};inv=investigation.get('id') or investigation.get('run',{}).get('id')
    if sidecar and sidecar.exists():inv=json.loads(sidecar.read_text()).get('investigation_run_id') or inv
    source=(run/'deliverables'/f'{a.public_id}.ipynb') if run else None
    raw=source.read_bytes() if source and source.is_file() else None
    nb=json.loads(raw) if raw else None
    if nb and (nb.get('nbformat')!=4 or not isinstance(nb.get('cells'),list)):raise ValueError('Not a notebook')
    cells=nb['cells'] if nb else []
    code=[c for c in cells if c.get('cell_type')=='code' and ''.join(c.get('source',[])).strip()]
    failure_entry=None
    if a.status=='failed':
        run_id=run.name if run else inv
        failure_entry={'public_id':a.public_id,'title':title,'investigation_run_id':inv,'run_id':run_id,'status':'failed','reason':reason,'created_on':dt.date.today().isoformat()}
        if raw and code and inv:failure_entry['notebook_path']=f'notebooks/unverified/{a.public_id}.ipynb'
    if not raw or not code or (a.status=='failed' and not inv):
        if a.status!='failed':print(json.dumps({'skipped':'no_notebook'}));return
        with (REPO/'.git/publication.lock').open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX)
            if verified.git('status','--porcelain'):raise ValueError('Publication checkout has uncommitted changes')
            verified.ensure_github_access();verified.git('pull','--ff-only','origin','main')
            if any(e['public_id']==a.public_id for e in verified.load_manifest()['notebooks']):print(json.dumps({'skipped':'already_verified'}));return
            failures=load_failures();key=(a.public_id,inv or failure_entry.get('run_id') or '')
            failures['failures']=[item for item in failures['failures'] if (item['public_id'],item.get('investigation_run_id') or item.get('run_id') or '')!=key]
            failures['failures'].append(failure_entry);failures['failures'].sort(key=lambda item:(item.get('created_on',''),item['public_id']),reverse=True)
            FAILURES.write_text(json.dumps(failures,ensure_ascii=False,indent=2)+'\n')
            data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':1,'notebooks':[]}
            save_pages(data)
            commit=git_publish(['failures.json','FAILED.md','UNVERIFIED.md','README.md'],f'Record failed notebook attempt {a.public_id}')
        print(json.dumps({'failure_recorded':True,'public_id':a.public_id,'title':title,'investigation_run_id':inv,'repository_commit':commit}));return
    if len(raw)>10_000_000:raise ValueError('Draft notebook is too large')
    if re.search(r'(?i)Bearer\s+[A-Za-z0-9._~+/-]{8,}',json.dumps(nb)):raise ValueError('Draft contains a bearer credential')
    for c in cells:
        if c.get('cell_type')=='code':c['outputs']=[];c['execution_count']=None
    notice=f'# UNVERIFIED / INCOMPLETE NOTEBOOK\n\n**未検証・途中までの参考Notebookです。** 全セルの実行成功は確認していません。\n\n**Stopping reason:** {reason}\n\nAttempt status: {a.status}. No manual login validation was performed. This draft may require your own authorized access, fail partway, or contain incomplete code. This attempt does not establish that the paper cannot be reproduced.\n\nPaper: {title}\n\n[PhenoPaper record](https://phenopaper.smartbreed-plant-phenotyping-platform.com/papers/{a.public_id})\n'
    cells.insert(0,{'cell_type':'markdown','metadata':{},'source':notice.splitlines(keepends=True)})
    output=(json.dumps(nb,ensure_ascii=False,indent=1)+'\n').encode();digest=hashlib.sha256(output).hexdigest();path=f'notebooks/unverified/{a.public_id}.ipynb'
    if not inv:raise ValueError('Saved investigation identity is missing')
    unverified_entry={'public_id':a.public_id,'title':title,'investigation_run_id':inv,'status':a.status,'reason':reason,'created_on':dt.date.today().isoformat(),'notebook_path':path,'notebook_sha256':digest,'source_sha256':hashlib.sha256(raw).hexdigest(),'code_cells':len(code)}
    with (REPO/'.git/publication.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        if verified.git('status','--porcelain'):raise ValueError('Publication checkout has uncommitted changes')
        verified.ensure_github_access();verified.git('pull','--ff-only','origin','main')
        if any(e['public_id']==a.public_id for e in verified.load_manifest()['notebooks']):print(json.dumps({'skipped':'already_verified'}));return
        data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':1,'notebooks':[]}
        data['notebooks']=[e for e in data['notebooks'] if e['public_id']!=a.public_id]+[unverified_entry]
        target=REPO/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(output)
        MANIFEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        if a.status=='failed':
            failures=load_failures();key=(a.public_id,inv or failure_entry.get('run_id') or '')
            failures['failures']=[item for item in failures['failures'] if (item['public_id'],item.get('investigation_run_id') or item.get('run_id') or '')!=key]
            failures['failures'].append(failure_entry);FAILURES.write_text(json.dumps(failures,ensure_ascii=False,indent=2)+'\n')
        save_pages(data)
        files=[path,'unverified.json','UNVERIFIED.md','FAILED.md','README.md']
        if a.status=='failed':files.append('failures.json')
        commit=git_publish(files,f'Publish unverified notebook reference {a.public_id}')
    print(json.dumps({'repository_commit':commit,'notebook_sha256':digest,'public_id':a.public_id,'investigation_run_id':inv,'notebook_path':path}))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,json.JSONDecodeError,subprocess.CalledProcessError) as e:print(str(e),file=sys.stderr);sys.exit(1)
