"""Immutable, resumable real-project handoff experiment. No automatic retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys

import bank
import protocol
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent/'v3'))
import storage
import transport


def sources():
    files = [HERE/n for n in ('bank.py','protocol.py','run.py','DESIGN.md','test_v4.py')]
    files += list((HERE/'sources').glob('*'))
    files += [HERE.parent/'v3'/n for n in ('storage.py','transport.py')]
    return {str(p.relative_to(HERE.parent)):bank.digest(p.read_text()) for p in files}


def artifact(root, j):
    r=storage.latest(root,j)
    if not r or r['status']!='ok' or r.get('truncated') or not r.get('text','').strip():return None
    return r['text']


def plan(root, m, stage):
    path=root/(stage+'.json')
    if path.exists():return storage.frozen(path)
    jobs=[]; meta={}
    for task in m['tasks']:
        for author in ('gpt-sol','claude-opus'):
            cid=task['id']+'--'+author
            other='claude-opus' if author=='gpt-sol' else 'gpt-sol'
            base=dict(chain=cid,task=task['id'],stage=stage)
            prev=None
            if stage!='h1':
                prior='h2' if stage=='h3' else 'h1' if stage=='h2' else 'h3'
                p=storage.frozen(root/(prior+'.json'))
                candidates=[j for j in p['jobs'] if j['chain']==cid]
                prev=artifact(root,candidates[0]) if candidates else None
                if prev is None:
                    meta[cid]={'excluded':'invalid prerequisite '+prior}
                    continue
            if stage.startswith('h'):
                hop=int(stage[1:])
                jobs.append(dict(base,model_id=other if hop==2 else author,
                    prompt=protocol.handoff(task,hop,prev)))
            else:
                first=next(j for j in storage.frozen(root/'h1.json')['jobs'] if j['chain']==cid)
                variants={'full':task['dossier'],'first':artifact(root,first),'last':prev}
                _,count=protocol.rename(prev,task['id'])
                meta[cid]={'rename_occurrences':count}
                if count:variants['opaque']=prev
                for variant,context in variants.items():
                    for executor in ('gpt-sol','claude-opus'):
                        for rep in range(2):
                            jobs.append(dict(base,model_id=executor,variant=variant,rep=rep,
                                prompt=protocol.review(task,context,cid,rep,variant=='opaque')))
    jobs.sort(key=lambda j:bank.digest(['v4-job-order',j]))
    p=dict(stage=stage,jobs=jobs,meta=meta,created=storage.now())
    storage.freeze(path,p)
    return p


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('action',choices=['init','run','export'])
    ap.add_argument('--root',type=Path,default=HERE/'runs/pilot-2026-09-21-v4')
    ap.add_argument('--config',type=Path,default=HERE.parent/'v2/runs/config.private.json')
    ap.add_argument('--live',action='store_true')
    a=ap.parse_args();root=a.root
    if a.action=='init':
        models=storage.read(a.config)['models']
        for model in models:transport.validate_model(model)
        assert {x['id'] for x in models}=={'gpt-sol','claude-opus'} and len(models)==2
        storage.freeze(root/'manifest.json',dict(created=storage.now(),sources=sources(),models=models,tasks=bank.build_bank()))
        print('Frozen two project dossiers, 32 proposals, four chains; maximum 76 calls.')
        return
    m=storage.frozen(root/'manifest.json')
    if m['sources']!=sources():raise ValueError('source changed after freeze')
    if a.action=='export':
        plans={s:storage.frozen(root/(s+'.json')) for s in ('h1','h2','h3','review') if (root/(s+'.json')).exists()}
        records=[]
        allowed={'status','started','finished','attempt','text','finish_reason','usage','truncated','latency_s','error'}
        for p in sorted((root/'calls').glob('*.json')):
            r=storage.read(p)
            records.append(dict(job=r['job'],attempts=[{k:v for k,v in at.items() if k in allowed} for at in r['attempts']]))
        public=dict(created=m['created'],sources=m['sources'],tasks=m['tasks'],plans=plans,records=records,
                    models=[{'id':x['id'],'max_tokens':x['max_tokens'],'temperature':x.get('temperature'),'thinking':x.get('thinking')} for x in m['models']])
        out=HERE/'results/data.json';storage.write(out,public)
        print('Exported',len(records),'records without provider envelopes or private configuration.')
        return
    if not a.live:raise ValueError('--live required')
    original=transport.credential
    cached={x['id']:original(x) for x in m['models']}
    transport.credential=lambda model:cached[model['id']]
    models={x['id']:x for x in m['models']}
    with storage.lock(root):
        for stage in ('h1','h2','h3','review'):
            p=plan(root,m,stage)
            pending=[j for j in p['jobs'] if storage.latest(root,j) is None]
            print(stage,':',len(pending),'pending /',len(p['jobs']),'planned',flush=True)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures={pool.submit(storage.call,root,j,models[j['model_id']],transport.complete):j for j in pending}
                for f in as_completed(futures):
                    j=futures[f]
                    try:r=f.result()
                    except Exception as e:
                        print('Interrupted call:',type(e).__name__,flush=True)
                        raise SystemExit(2)
                    print(stage,j['chain'],j['model_id'],j.get('variant',''),j.get('rep',''),r['status'],flush=True)
            if any(storage.latest(root,j)['status']!='ok' for j in p['jobs']):
                raise SystemExit('Stage contains a transport/response failure; retained without retry.')


if __name__=='__main__':main()
