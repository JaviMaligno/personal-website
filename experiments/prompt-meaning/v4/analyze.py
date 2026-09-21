"""Descriptive analysis, with abstentions and invalid outputs separate."""
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import bank
import protocol

HERE=Path(__file__).resolve().parent


def analyze(data):
    tasks={t['id']:t for t in data['tasks']}
    groups=defaultdict(Counter); parsed={}; invalid=[]; notes=[]; usage=defaultdict(Counter); times=[]
    for record in data['records']:
        j=record['job']; r=record['attempts'][-1]
        for a in record['attempts']:
            times.append(a)
            u=a.get('usage',{})
            usage[j['model_id']]['input']+=u.get('input_tokens',u.get('prompt_tokens',0))
            usage[j['model_id']]['output']+=u.get('output_tokens',u.get('completion_tokens',0))
        if j['stage']!='review':
            notes.append(dict(chain=j['chain'],stage=j['stage'],model=j['model_id'],
                              words=len(r.get('text','').split()),text=r.get('text',''),status=r['status'],
                              finish_reason=r.get('finish_reason'),valid=bool(r.get('text','').strip()) and not r.get('truncated',False) and r['status']=='ok'))
            continue
        cases=tasks[j['task']]['cases']
        keys=[(j['model_id'],j['variant'],s) for s in ('all','routine','boundary')]
        for key in keys:
            groups[key]['expected']+=len(cases) if key[2]=='all' else sum(c['routine']==(key[2]=='routine') for c in cases)
        try:
            if r['status']!='ok' or r.get('truncated'):raise ValueError('incomplete')
            decisions=protocol.parse(r['text'],cases)
        except (ValueError,KeyError,TypeError):
            invalid.append(dict(chain=j['chain'],model=j['model_id'],variant=j['variant'],rep=j['rep'],text=r.get('text',''),finish_reason=r.get('finish_reason')))
            continue
        parsed[(j['chain'],j['model_id'],j['variant'],j['rep'])]=decisions
        for c in cases:
            d=decisions[c['id']]['decision']
            for subset in ('all','routine' if c['routine'] else 'boundary'):
                g=groups[(j['model_id'],j['variant'],subset)]
                g['valid']+=1
                g['correct']+=d==c['expected']
                g['abstain']+=d=='needs_context'
                g['wrong']+=d not in (c['expected'],'needs_context')
    chains=sorted({r['job']['chain'] for r in data['records']})
    loss=[]; initial=[]; lexical=[]; masked=[]; unstable=[]
    for chain in chains:
        task=tasks[chain.split('--')[0]]
        for model in ('gpt-sol','claude-opus'):
            for c in task['cases']:
                ds={v:[parsed.get((chain,model,v,rep),{}).get(c['id']) for rep in range(2)] for v in ('full','first','last','opaque')}
                labels={v:[r['decision'] if r else None for r in rows] for v,rows in ds.items()}
                stable={v:ls[0] is not None and ls[0]==ls[1] for v,ls in labels.items()}
                good=lambda v: stable[v] and labels[v][0]==c['expected']
                wrong=lambda v: stable[v] and labels[v][0] not in (c['expected'],'needs_context')
                item=dict(chain=chain,model=model,case=c,observations=ds)
                if good('full') and good('first') and wrong('last'):loss.append(item)
                if good('full') and wrong('first'):initial.append(item)
                if stable['last'] and stable['opaque'] and labels['last'][0]!=labels['opaque'][0]:lexical.append(item)
                if wrong('last') and good('full') and not c['routine'] and all(
                    parsed.get((chain,model,'last',rep),{}).get(x['id'],{}).get('decision')==x['expected']
                    for rep in range(2) for x in task['cases'] if x['routine']):masked.append(item)
                for v,ls in labels.items():
                    if None not in ls and ls[0]!=ls[1]:unstable.append(dict(chain=chain,model=model,id=c['id'],variant=v,labels=ls))
    costs=[]
    for model,u in usage.items():
        a,b=(4,20) if model=='gpt-sol' else (5,25)
        costs.append(dict(model=model,**u,reference_usd=(u['input']*a+u['output']*b)/1e6))
    return dict(calls=len(data['records']),attempts=len(times),invalid=invalid,notes=notes,
        groups=[dict(model=k[0],variant=k[1],subset=k[2],**v) for k,v in sorted(groups.items())],
        stable_later_errors=loss,stable_initial_errors=initial,stable_lexical_changes=lexical,
        routine_success_boundary_errors=masked,unstable=unstable,costs=costs,
        wall_seconds=(max(datetime.fromisoformat(a['finished']) for a in times)-min(datetime.fromisoformat(a['started']) for a in times)).total_seconds())


def main():
    data=json.loads((HERE/'results/data.json').read_text());r=analyze(data)
    (HERE/'results/report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    lines=['# Real-project handoff replay','',
           'Two maintenance areas from one existing research project; four generated chains. '
           'Review proposals are constructed probes, not historical PRs. Coinage provenance is unverified. '
           'Repeated decisions are not independent discoveries.','',
           f"Calls: {r['calls']}; attempts: {r['attempts']}; invalid reviews: {len(r['invalid'])}; invalid handoffs: {sum(not n['valid'] for n in r['notes'])}.",'',
           '| Model | Context | Correct | Wrong | Abstain | Valid / expected |',
           '|---|---|---:|---:|---:|---:|']
    for g in r['groups']:
        if g['subset']=='all':lines.append(f"| {g['model']} | {g['variant']} | {g.get('correct',0)} | {g.get('wrong',0)} | {g.get('abstain',0)} | {g.get('valid',0)} / {g['expected']} |")
    for title,key in [('Stable errors introduced after first handoff','stable_later_errors'),
                      ('Stable errors already in first handoff','stable_initial_errors'),
                      ('Stable decisions changed by opaque renaming','stable_lexical_changes'),
                      ('All routine probes pass, but a boundary fails','routine_success_boundary_errors')]:
        lines += ['',f'## {title}: {len(r[key])}','']
        for x in r[key]:
            lines += [f"- {x['chain']} / {x['model']} / {x['case']['id']}: {x['case']['proposal']}",
                      '  '+json.dumps({v:[z['decision'] if z else None for z in rows] for v,rows in x['observations'].items()})]
    lines += ['','## Handoff lengths','']+[f"- {n['chain']} {n['stage']}: {n['words']} words" for n in r['notes']]
    lines += ['','## Accounting','',f"Wall time: {r['wall_seconds']:.1f} s. Reference cost only, using prior-run rates:"]
    lines += [f"- {c['model']}: {c['input']} input, {c['output']} output tokens; ${c['reference_usd']:.6f}." for c in r['costs']]
    (HERE/'results/report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:len(r[k]) for k in ('stable_later_errors','stable_initial_errors','stable_lexical_changes','routine_success_boundary_errors','invalid')}))


if __name__=='__main__':main()
