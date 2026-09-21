"""Frozen exploratory 2x2 follow-up. No additional model or retry loop."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import bank
import protocol
import run

HERE=Path(__file__).resolve().parent
MAIN=HERE/'runs/pilot-2026-09-21-v4'
ROOT=HERE/'runs/factor-check'
SENTENCE='iou_vs_truth returns non_positional with iou=None on failure; otherwise it uses the first velocity sample.'


def prepare():
    m=run.storage.frozen(MAIN/'manifest.json')
    assert m['sources']==run.sources()
    task=next(t for t in m['tasks'] if t['id']=='geometry')
    chain='geometry--gpt-sol'
    j=next(j for j in run.storage.frozen(MAIN/'h3.json')['jobs'] if j['chain']==chain)
    note=run.artifact(MAIN,j)
    assert note.count(SENTENCE)==1
    jobs=[]
    for clarified in (False,True):
        text=note.replace(SENTENCE,SENTENCE.replace('on failure','when preimage_invariant returns False')) if clarified else note
        for opaque in (False,True):
            variant=('explicit' if clarified else 'implicit')+'_'+('opaque' if opaque else 'named')
            for rep in range(5):
                prompt=protocol.review(task,text,chain+'-factor',rep,opaque=False)
                if opaque:
                    assert prompt.count('non_positional')==4
                    prompt=prompt.replace('non_positional','class_q8')
                jobs.append(dict(stage='review',chain=chain,task='geometry',model_id='gpt-sol',variant=variant,rep=rep,prompt=prompt))
    # Verify mechanically that only the predeclared transformations differ.
    for rep in range(5):
        rows={j['variant']:j['prompt'] for j in jobs if j['rep']==rep}
        assert rows['implicit_named'].replace('non_positional','class_q8')==rows['implicit_opaque']
        assert rows['explicit_named'].replace('non_positional','class_q8')==rows['explicit_opaque']
        assert rows['implicit_named'].replace(SENTENCE,SENTENCE.replace('on failure','when preimage_invariant returns False'))==rows['explicit_named']
    jobs.sort(key=lambda j:bank.digest(['factor-order',j]))
    if not (ROOT/'plan.json').exists():
        run.storage.freeze(ROOT/'plan.json',dict(created=run.storage.now(),task=task,jobs=jobs,
            source_sha256=bank.digest(Path(__file__).read_text()),design_sha256=bank.digest((HERE/'FACTOR-CHECK.md').read_text())))
    p=run.storage.frozen(ROOT/'plan.json')
    assert p['source_sha256']==bank.digest(Path(__file__).read_text())
    assert p['design_sha256']==bank.digest((HERE/'FACTOR-CHECK.md').read_text())
    return m,p


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run','export']);a=ap.parse_args()
    m,p=prepare()
    if a.action=='freeze':print('Frozen 20 factor-check prompts; all paired edits verified.');return
    if a.action=='export':
        allowed={'status','started','finished','attempt','text','finish_reason','usage','truncated','latency_s','error'}
        records=[];rows=[]
        for j in p['jobs']:
            rec=run.storage.read(run.storage.job_path(ROOT,j))
            records.append(dict(job=j,attempts=[{k:v for k,v in x.items() if k in allowed} for x in rec['attempts']]))
            r=rec['attempts'][-1]
            try:
                if r['status']!='ok' or r.get('truncated'):raise ValueError('incomplete')
                decisions=protocol.parse(r['text'],p['task']['cases'])
                wrong=[c['id'] for c in p['task']['cases'] if decisions[c['id']]['decision'] not in (c['expected'],'needs_context')]
                abstain=[k for k,v in decisions.items() if v['decision']=='needs_context']
                rows.append(dict(variant=j['variant'],rep=j['rep'],valid=True,p07=decisions['p07'],p08=decisions['p08'],wrong=wrong,abstain=abstain))
            except (ValueError,KeyError,TypeError):rows.append(dict(variant=j['variant'],rep=j['rep'],valid=False))
        data=dict(task=p['task'],created=p['created'],records=records)
        run.storage.write(HERE/'results/factor-data.json',data)
        run.storage.write(HERE/'results/factor-report.json',dict(rows=sorted(rows,key=lambda x:(x['variant'],x['rep']))))
        print('Exported factor-check responses and per-repetition target pairs.');return
    model=next(x for x in m['models'] if x['id']=='gpt-sol')
    credential=run.transport.credential(model)
    run.transport.credential=lambda _:credential
    with run.storage.lock(ROOT):
        pending=[j for j in p['jobs'] if run.storage.latest(ROOT,j) is None]
        print('Factor check:',len(pending),'pending',flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fs={pool.submit(run.storage.call,ROOT,j,model,run.transport.complete):j for j in pending}
            for f in as_completed(fs):
                r=f.result();j=fs[f]
                print(j['variant'],j['rep'],r['status'],flush=True)


if __name__=='__main__':main()
