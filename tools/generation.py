"""Capture only allowlisted generation settings; never serialize credentials/configs."""
from pathlib import Path
import datetime as dt
import json
import os
import re
import subprocess

PARAMETERS={'variant','reasoning_effort','temperature','top_p','max_output_tokens'}
SOURCES={'host_process','historical_job_monitor','historical_log'}

def safe_text(value):
    return isinstance(value,str) and 0<len(value.strip())<=160 and not re.search(r'[\x00-\x1f<>|]',value)

def validate(value):
    if value is None:return None
    if not isinstance(value,dict) or not safe_text(value.get('harness')) or not safe_text(value.get('model')):
        raise ValueError('Invalid generation provenance')
    for key in ('harness_version','run_id'):
        if value.get(key) is not None and not safe_text(value[key]):raise ValueError('Invalid generation '+key)
    if value.get('source') not in SOURCES or not isinstance(value.get('parameters'),dict):raise ValueError('Invalid generation source/settings')
    for key,setting in value['parameters'].items():
        if key not in PARAMETERS or not (safe_text(setting) or isinstance(setting,bool) or isinstance(setting,(int,float)) and __import__('math').isfinite(setting)):
            raise ValueError('Invalid generation parameter')
    return {k:value.get(k) for k in ('harness','harness_version','model','parameters','source','run_id')}

def invocation(argv,config,version=None):
    """Only a /reproduce authoring invocation is generation, not /validate-t4."""
    def arg(flag):
        try:return argv[argv.index(flag)+1]
        except (ValueError,IndexError):return None
    if arg('--command')!='reproduce' or not safe_text(arg('--model')):return None
    model=arg('--model');variant=arg('--variant');parameters={}
    if safe_text(variant):parameters['variant']=variant
    provider,sep,model_name=model.partition('/')
    if sep:
        entry=config.get('provider',{}).get(provider,{}).get('models',{}).get(model_name,{})
        options={**entry.get('options',{}),**entry.get('variants',{}).get(variant,{})}
        for old,new in [('reasoningEffort','reasoning_effort'),('temperature','temperature'),('topP','top_p'),('maxTokens','max_output_tokens')]:
            value=options.get(old)
            if safe_text(value) or isinstance(value,(bool,int,float)):parameters[new]=value
    return validate({'harness':'OpenCode','harness_version':version if safe_text(version) else None,'model':model,'parameters':parameters,'source':'host_process','run_id':None})

def read_current():
    """Walk bounded Linux ancestry; no environment values or full commands are saved."""
    pid=os.getppid()
    for _ in range(12):
        try:
            directory=Path('/proc')/str(pid)
            argv=directory.joinpath('cmdline').read_bytes().decode().split('\0')
            if '--model' in argv and '--command' in argv and any('opencode' in Path(a).name.lower() for a in argv[:2]):
                config_path=os.environ.get('OPENCODE_CONFIG')
                config=json.loads(Path(config_path).read_text()) if config_path else {}
                try:
                    r=subprocess.run([argv[0],'--version'],text=True,capture_output=True,timeout=5)
                    version=r.stdout.strip() if r.returncode==0 else None
                except (OSError,subprocess.TimeoutExpired):version=None
                return invocation(argv,config,version)
            status=directory.joinpath('status').read_text()
            pid=int(re.search(r'^PPid:\s+(\d+)',status,re.M)[1])
            if pid<=1:break
        except (OSError,ValueError,TypeError,json.JSONDecodeError):break
    return None

def for_run(run_dir):
    """Keep the original authoring record across validation-only publication."""
    path=run_dir/'generation.json'
    if path.exists():return validate(json.loads(path.read_text()))
    value=read_current()
    if value is not None:
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    return value

def summary(value):
    value=validate(value)
    if value is None:return 'Generation conditions not recorded'
    harness=value['harness']+(' '+value['harness_version'] if value['harness_version'] else '')
    return ' · '.join([harness,value['model'],*(key.replace('_',' ')+': '+str(v) for key,v in value['parameters'].items())])
