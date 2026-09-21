"""Join accounting, without pooling the three different experimental questions."""
from collections import defaultdict, Counter
from datetime import datetime
import json
from pathlib import Path
import protocol

HERE=Path(__file__).resolve().parent
OUT=HERE/'results'


def main():
    main_data=json.loads((OUT/'data.json').read_text())
    supplementary=json.loads((OUT/'supplement-data.json').read_text())
    factor=json.loads((OUT/'factor-data.json').read_text())
    records=main_data['records']+supplementary['records']+factor['records']
    usage=defaultdict(Counter);stamps=[]
    for rec in records:
        for a in rec['attempts']:
            u=a.get('usage',{});g=usage[rec['job']['model_id']]
            g['calls']+=1;g['input']+=u.get('input_tokens',u.get('prompt_tokens',0))
            g['output']+=u.get('output_tokens',u.get('completion_tokens',0))
            stamps.append(a)
    accounting=[]
    for model,g in usage.items():
        a,b=(4,20) if model=='gpt-sol' else (5,25)
        accounting.append(dict(model=model,**g,reference_usd=(g['input']*a+g['output']*b)/1e6))
    boundary=[]
    for rec in supplementary['records']:
        j=rec['job'];r=rec['attempts'][-1]
        try:obs=protocol.parse(r['text'],supplementary['tasks'][0]['cases'])
        except (ValueError,TypeError,KeyError):obs=None
        boundary.append(dict(model=j['model_id'],variant=j['variant'],rep=j['rep'],
            s01=obs['s01'] if obs else None))
    rows=json.loads((OUT/'factor-report.json').read_text())['rows']
    cells=[]
    for variant in sorted({r['variant'] for r in rows}):
        rr=[r for r in rows if r['variant']==variant]
        cells.append(dict(variant=variant,calls=len(rr),valid=sum(r['valid'] for r in rr),
            target_pair_correct=sum(r['valid'] and r['p07']['decision']=='reject' and r['p08']['decision']=='accept' for r in rr),
            target_wrong_decisions=sum(sum(r[k]['decision'] not in (want,'needs_context') for k,want in [('p07','reject'),('p08','accept')]) for r in rr if r['valid']),
            target_abstentions=sum(sum(r[k]['decision']=='needs_context' for k in ('p07','p08')) for r in rr if r['valid']),
            all_wrong=sum(len(r['wrong']) for r in rr if r['valid']),
            all_abstain=sum(len(r['abstain']) for r in rr if r['valid'])))
    result=dict(calls=len(records),attempts=len(stamps),accounting=accounting,
        reference_total_usd=sum(x['reference_usd'] for x in accounting),
        elapsed_first_to_last_seconds=(max(datetime.fromisoformat(a['finished']) for a in stamps)-min(datetime.fromisoformat(a['started']) for a in stamps)).total_seconds(),
        boundary=sorted(boundary,key=lambda x:(x['model'],x['variant'],x['rep'])),factor_cells=cells)
    (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('calls','attempts','reference_total_usd','elapsed_first_to_last_seconds','factor_cells')},indent=2))


if __name__=='__main__':main()
