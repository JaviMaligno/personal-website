import json
import random
import re
from bank import digest, TERMS

PRECEDENCE = ('The current implementation and regression tests take precedence over '
              'the earlier design/plan where they differ. Maintain existing behavior; '
              'a deliberate redesign is outside this ticket. ')


def handoff(task, hop, previous=None):
    content = task['dossier'] if hop == 1 else previous
    work = ('evidence-dose sampling and refinement' if task['id'] == 'dose' else
            'geometry metrics and artifact classification')
    tasks = {
        1: f'Prepare the maintenance handoff for a teammate taking over {work}. '
           'The next work is review of a batch-run performance refactor. Include the '
           'implementation decisions they need, relevant terminology, and pending risks. '
           'Aim for 650 words.',
        2: f'You are taking over {work}. Prepare a reviewer brief for another session '
           'that will assess proposed maintenance changes. Its priorities are reducing '
           'batch-run overhead, consistent result reporting, and avoiding regressions. '
           'Use the handoff below; aim for 450 words.',
        3: f'The next session will review changes to {work}. Write its session-start '
           'note from the current brief. Make it useful for deciding whether proposed '
           'changes can be merged. Aim for 350 words.',
    }
    return (tasks[hop]+' '+PRECEDENCE+
            'The next session receives only your note, without access to these source '
            'files or earlier conversations. Return the note as plain text.\n\n'+content)


def rename(text, domain):
    # One pass, longest match first; replacements never get replaced a second time.
    mapping = dict(TERMS[domain])
    pattern = '|'.join(re.escape(s) for s in sorted(mapping, key=len, reverse=True))
    lookup = {k.casefold(): v for k,v in mapping.items()}
    return re.subn(pattern, lambda m: lookup[m[0].casefold()], text, flags=re.I)


def review(task, instructions, chain, rep, opaque=False):
    cases = [{'id': c['id'], 'proposal': c['proposal']} for c in task['cases']]
    random.Random(digest([chain, rep])).shuffle(cases)
    if opaque:
        instructions, _ = rename(instructions, task['id'])
        for c in cases:
            c['proposal'], _ = rename(c['proposal'], task['id'])
    return ('Review these independent maintenance proposals against the supplied project '
            'context. '+PRECEDENCE+
            'Decide accept, reject, or needs_context for each proposal. If the supplied '
            'context does not settle a decision, use needs_context. Give the decisive '
            'reason in one sentence. Do not use knowledge of other proposals as an '
            'authoritative source of project requirements.\n\nPROJECT CONTEXT:\n'+instructions+
            '\n\nPROPOSALS:\n'+json.dumps(cases, ensure_ascii=False)+
            '\nReturn ONLY a JSON object {"reviews":{"p01":{"decision":"accept|reject|'
            'needs_context","reason":"..."},...}} with all IDs exactly once.')


def parse(text, cases):
    def pairs(items):
        d = {}
        for k,v in items:
            if k in d: raise ValueError('duplicate key')
            d[k]=v
        return d
    s=text.strip()
    if s.startswith('```json\n') and s.endswith('\n```'): s=s[8:-4]
    d=json.loads(s, object_pairs_hook=pairs)
    if set(d) != {'reviews'} or set(d['reviews']) != {c['id'] for c in cases}:
        raise ValueError('wrong keys')
    for row in d['reviews'].values():
        if set(row) != {'decision','reason'} or row['decision'] not in ('accept','reject','needs_context'):
            raise ValueError('invalid row')
        if not isinstance(row['reason'],str) or not row['reason'].strip(): raise ValueError('reason')
    return d['reviews']
