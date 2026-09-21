import json
import unittest
from copy import deepcopy
import bank
import protocol
import analyze


class ProtocolTests(unittest.TestCase):
    def test_no_answer_leak_and_consistent_renaming(self):
        for task in bank.build_bank():
            self.assertEqual(len(task['cases']),16)
            self.assertEqual(sum(c['expected']=='accept' for c in task['cases']),8)
            for hop in (1,2,3):
                prompt=protocol.handoff(task,hop,'previous note')
                self.assertNotIn('PROPOSALS:',prompt)
                if hop>1:self.assertNotIn('FILE:',prompt)
            p=protocol.review(task,'evidence_capped_failure endpoint-space','x',0,opaque=True)
            before,proposals=p.split('PROPOSALS:\n')
            self.assertNotIn('"expected"',proposals)
            self.assertNotIn('"source"',proposals)
            if task['id']=='dose':self.assertNotIn('evidence_capped_failure',p)
            else:self.assertNotIn('endpoint-space',p)

    def test_scoring_separates_loss_abstention_and_lexical_change(self):
        task=bank.build_bank()[0];records=[]
        for v in ('full','first','last','opaque'):
            for rep in (0,1):
                rows={c['id']:{'decision':c['expected'],'reason':'test fixture'} for c in task['cases']}
                if v in ('last','opaque'):rows['p05']['decision']='accept'
                if v=='opaque':rows['p06']['decision']='needs_context'
                records.append(dict(job=dict(stage='review',chain='dose--gpt-sol',task='dose',model_id='gpt-sol',variant=v,rep=rep),
                    attempts=[dict(status='ok',text=json.dumps({'reviews':rows}),started='2026-09-21T00:00:00+00:00',finished='2026-09-21T00:00:01+00:00')]))
        r=analyze.analyze(dict(tasks=[task],records=records))
        self.assertEqual(len(r['stable_later_errors']),1)
        self.assertEqual(len(r['stable_initial_errors']),0)
        self.assertEqual(len(r['stable_lexical_changes']),1)
        self.assertEqual(len(r['routine_success_boundary_errors']),1)
        self.assertEqual(sum(g['abstain'] for g in r['groups'] if g['subset']=='all'),2)
        broken=deepcopy(records);broken[-1]['attempts'][0]['text']='{"reviews":{}}'
        self.assertEqual(len(analyze.analyze(dict(tasks=[task],records=broken))['invalid']),1)


if __name__=='__main__':unittest.main()
