"""Pre-call maintenance probes, keyed to existing source behavior."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def build_bank():
    # Four routine cases + twelve boundary probes, balanced accept/reject overall.
    specs = {
        'dose': [
            ('accept', 'Keep measuring accuracy on all gate_transitions even though the model sees only the controlled sample.', 'evidence_dose.py:refine_capped'),
            ('reject', 'Speed up the experiment by measuring gate accuracy only on the 40 controlled observations.', 'evidence_dose.py:refine_capped'),
            ('accept', 'Use the original source_index as the identity when filtering correction feedback after the sample has been shuffled.', 'test_evidence_dose.py:test_capped_failure_uses_source_indices'),
            ('reject', 'When matching negative examples, allow one negative to be reused for several positive examples.', 'test_evidence_dose.py:test_fixed_size_and_distinct_negatives'),
            ('reject', 'A syntax error yields a single failure with source_index=None. Since None is not in allowed_source_indices, immediately return evidence_capped_failure=True without asking for a repair.', 'test_evidence_dose.py:test_infra_failure_is_not_reported_as_evidence_capped'),
            ('accept', 'For a global sandbox failure with source_index=None, send the diagnostic for repair and continue up to max_iters, leaving evidence_capped_failure False.', 'evidence_dose.py:refine_capped'),
            ('reject', 'Fill background from every transition not already selected, including contact=True transitions that were not among the selected m positives.', 'test_evidence_dose.py:test_background_excludes_all_positives'),
            ('accept', 'Build background from unused contact=False transitions only, excluding both the selected positives and the matched negative examples.', 'evidence_dose.py:build_dose_sample'),
            ('reject', 'To estimate penetration depth for matching, project the recorded positive next_state onto the shape boundary instead of computing the proposed endpoint before the clamp.', 'evidence_dose.py:_proposed_endpoint'),
            ('accept', 'Measure boundary-normal matching distance from the raw integrator endpoint before the contact response has changed that position.', 'evidence_dose.py:_proposed_endpoint'),
            ('reject', 'Refresh the 40-example set after each repair so the initial prompt and each repair prompt remain within 40 examples independently.', 'evidence_dose.py module docstring'),
            ('accept', 'Retain one fixed allowed_source_indices set for initial synthesis and every repair; limit the displayed failures to the first 20 eligible failures.', 'evidence_dose.py:refine_capped'),
            ('accept', 'When there are enough positives and distinct matching negatives but too few unused non-contact backgrounds, return the smaller sample and record the actual n_background.', 'evidence_dose.py:build_dose_sample'),
            ('reject', 'Enforce the phrase fixed 40 by raising an exception whenever unused non-contact backgrounds cannot fill all 40 slots, replacing the current short-background fallback.', 'evidence_dose.py:build_dose_sample'),
            ('reject', 'When max_iters=0, label any imperfect artifact evidence_capped_failure=True even though no capped-feedback iteration was entered.', 'evidence_dose.py:refine_capped while guard'),
            ('accept', 'If accuracy is already 1.0, return with zero repairs and evidence_capped_failure=False even though the failure list has no member of the allowed set.', 'evidence_dose.py:refine_capped while guard'),
        ],
        'geometry': [
            ('accept', 'Keep reporting disagreement separately for inside, outside, band, uniform and planner, with band designated as the primary stratum.', 'metrics_geom.py:disagreement_scores'),
            ('reject', 'Replace the boundary-band probes with a single uniform sample because most states do not contact the shape and total accuracy is higher.', 'metrics_geom.py module docstring'),
            ('accept', 'For inside/outside probes, increase the boundary-normal offset until env.contact agrees with the requested label, subject to a finite retry cap.', 'metrics_geom.py:_grow_until'),
            ('reject', 'Treat candidate code that cannot execute its step function as gate_failing rather than invalid.', 'test_artifact_class.py:test_missing_step_is_invalid_not_gate_failing'),
            ('reject', 'Construct forbidden_mask by using each grid point directly as the previous position with the chosen velocity, without inverting the integrator.', 'test_metrics_geom.py:test_true_guard_is_positional_and_invariant_across_velocity'),
            ('accept', 'For each endpoint-space grid point, solve for the previous state with invert_integrator and run the model from that state.', 'metrics_geom.py:forbidden_mask'),
            ('reject', 'When velocity samples produce non-invariant masks, report the IoU at the first velocity and classify the guard as non_positional.', 'test_metrics_geom.py:test_velocity_guard_is_non_positional'),
            ('accept', 'For a non_positional guard, set iou to None while retaining its non_positional classification.', 'metrics_geom.py:iou_vs_truth'),
            ('reject', 'Replace the 0.98 Jaccard tolerance in preimage_invariant with bit-for-bit mask equality, preserving all other behavior.', 'metrics_geom.py:preimage_invariant'),
            ('accept', 'Two empty masks have Jaccard similarity 1.0, rather than an undefined 0/0 score.', 'metrics_geom.py:_jaccard'),
            ('reject', 'For the freeze signature, checking that both next-state velocities are zero is enough; remove the checks that next position equals previous position.', 'metrics_geom.py:_model_contact'),
            ('accept', 'Recognize the freeze signature only when both velocities are zero and the next position exactly equals the previous position.', 'metrics_geom.py:_model_contact'),
            ('accept', 'In balanced disagreement, if a stratum has only one truth class, average only the defined recall/specificity rates.', 'metrics_geom.py:disagreement_scores'),
            ('reject', 'For a stratum with no true positives, replace undefined recall by zero before averaging recall with specificity.', 'metrics_geom.py:disagreement_scores'),
            ('reject', 'Run a gate-failing candidate in-process to compute its whole dynamic mask faster, while retaining the sandbox for its preflight.', 'artifact_class.py module docstring'),
            ('accept', 'Evaluate an untrusted dynamic mask inside one sandbox invocation and return the packed bits in a JSON envelope for decoding by the caller.', 'artifact_class.py:dynamic_metrics_sandboxed'),
        ],
    }
    tasks = []
    for domain, items in specs.items():
        names = ['2026-07-19-curvature-sweep-design.md', '2026-07-19-repair-vs-geometry-phase-a.md']
        names += (['evidence_dose.py', 'test_evidence_dose.py'] if domain == 'dose' else
                  ['metrics_geom.py', 'artifact_class.py', 'test_metrics_geom.py', 'test_artifact_class.py'])
        packet = '\n\n'.join('FILE: '+n+'\n'+(HERE/'sources'/n).read_text() for n in names)
        tasks.append(dict(id=domain, dossier=packet, cases=[dict(id=f'p{i+1:02}', expected=a,
            proposal=b, source=c, routine=i<4) for i,(a,b,c) in enumerate(items)]))
    return tasks


TERMS = {
    'dose': [('evidence_capped_failure', 'flag_q7'), ('evidence-capped failure', 'velun status'),
             ('evidence capped failure', 'velun status'), ('evidence-capped', 'velun'),
             ('evidence capped', 'velun')],
    'geometry': [('preimage_invariant', 'check_q7'), ('endpoint-space', 'velun-space'),
                 ('endpoint space', 'velun space'), ('freeze signature', 'navic signature'),
                 ('non_positional', 'class_q8'), ('non-positional', 'class-q8'),
                 ('positional', 'class-q9'), ('dynamic mask', 'sorel mask')],
}
