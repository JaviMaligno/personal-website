"""Separate follow-up, preserving the main frozen run."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import bank
import protocol
import run

HERE=Path(__file__).resolve().parent
ROOT=HERE/'runs/pilot-2026-09-21-v4'
OUT=HERE/'runs/supplement-boundary'


def cases():
    common=('There are no syntax, sandbox, or infrastructure errors. Initial full-gate '
            'evaluation is already available. allowed_source_indices={7,8,9}. ')
    return [
      dict(id='s01',expected='reject',routine=False,source='evidence_dose.py:refine_capped while guard',
           proposal=common+'Initial accuracy=0.8; the only failure source IDs are {311,512}; max_iters=0. '
           'The refactor returns zero repair iterations and evidence_capped_failure=True. '
           'Accept this result as preserving current behavior.'),
      dict(id='s02',expected='accept',routine=False,source='evidence_dose.py:refine_capped while guard',
           proposal=common+'Initial accuracy=0.8; the only failure source IDs are {311,512}; max_iters=1. '
           'The refactor returns zero repair iterations and evidence_capped_failure=True without a provider call. '
           'Accept this result as preserving current behavior.'),
      dict(id='s03',expected='reject',routine=True,source='evidence_dose.py:refine_capped allowed filter',
           proposal=common+'Initial accuracy=0.8; the only failure source IDs are {8,512}; max_iters=1. '
           'The refactor stops immediately with evidence_capped_failure=True without a provider call. '
           'Accept this result as preserving current behavior.'),
      dict(id='s04',expected='accept',routine=True,source='evidence_dose.py:refine_capped while guard',
           proposal=common+'Initial accuracy=1.0; there are no failures; max_iters=1. '
           'The refactor returns zero repair iterations and evidence_capped_failure=False without a provider call. '
           'Accept this result as preserving current behavior.'),
    ]


def prepare():
    m=run.storage.frozen(ROOT/'manifest.json')
    assert m['sources']==run.sources()
    original=next(t for t in m['tasks'] if t['id']=='dose')
    task=dict(original,cases=cases())
    chain='dose--gpt-sol'
    contexts={'full':task['dossier']}
    for stage,label in [('h1','first'),('h3','last')]:
        j=next(j for j in run.storage.frozen(ROOT/(stage+'.json'))['jobs'] if j['chain']==chain)
        contexts[label]=run.artifact(ROOT,j)
        assert contexts[label]
    contexts['opaque']=contexts['last']
    jobs=[]
    for variant,context in contexts.items():
        for model in ('gpt-sol','claude-opus'):
            for rep in (0,1):
                jobs.append(dict(stage='review',chain=chain,task='dose',variant=variant,model_id=model,rep=rep,
                    prompt=protocol.review(task,context,chain+'-supplement',rep,variant=='opaque')))
    jobs.sort(key=lambda j:bank.digest(['supplement-order',j]))
    if not (OUT/'plan.json').exists():
        run.storage.freeze(OUT/'plan.json',dict(created=run.storage.now(),task=task,jobs=jobs,
            script_sha256=bank.digest(Path(__file__).read_text()),design_sha256=bank.digest((HERE/'SUPPLEMENT.md').read_text())))
    p=run.storage.frozen(OUT/'plan.json')
    assert p['script_sha256']==bank.digest(Path(__file__).read_text())
    assert p['design_sha256']==bank.digest((HERE/'SUPPLEMENT.md').read_text())
    return m,p


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run','export']);a=ap.parse_args()
    m,p=prepare()
    if a.action=='freeze':
        print('Supplement frozen: 4 concrete cases, 16 calls.');return
    if a.action=='export':
        allowed={'status','started','finished','attempt','text','finish_reason','usage','truncated','latency_s','error'}
        records=[]
        for j in p['jobs']:
            r=run.storage.read(run.storage.job_path(OUT,j))
            records.append(dict(job=j,attempts=[{k:v for k,v in x.items() if k in allowed} for x in r['attempts']]))
        data=dict(tasks=[p['task']],records=records,created=p['created'],supplement=True)
        run.storage.write(HERE/'results/supplement-data.json',data)
        import analyze
        report=analyze.analyze(data)
        run.storage.write(HERE/'results/supplement-report.json',report)
        print('Exported and analyzed supplementary cases separately.');return
    cred=run.transport.credential
    cached={x['id']:cred(x) for x in m['models']}
    run.transport.credential=lambda model:cached[model['id']]
    models={x['id']:x for x in m['models']}
    with run.storage.lock(OUT):
        pending=[j for j in p['jobs'] if run.storage.latest(OUT,j) is None]
        print('Supplement:',len(pending),'pending',flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fs={pool.submit(run.storage.call,OUT,j,models[j['model_id']],run.transport.complete):j for j in pending}
            for f in as_completed(fs):
                r=f.result();j=fs[f]
                print(j['model_id'],j['variant'],j['rep'],r['status'],flush=True)


if __name__=='__main__':main()
