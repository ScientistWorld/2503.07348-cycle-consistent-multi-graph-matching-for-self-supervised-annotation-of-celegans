"""Descriptive rank for this audit cohort; no claim about unknown future scale.

Uses the user-specified metric directions, abs(coefficient), experiment weight,
and across-attempt population standard deviations. Zero-variance metrics give
zero contribution. Missing scored values are skipped as specified by the user.
Only successful official hidden-test executions enter the cohort. Dominance
checks are independent of this particular cohort normalization.
"""
import json
from pathlib import Path
import numpy as np
from redteam.quality_methods import EXP, PROPOSED


def main():
    root = Path('redteam')
    config = json.loads(Path('scoring/reference.json').read_text())['experiments'][EXP]
    metrics = {k:v for k,v in config['metrics'].items() if abs(v.get('coefficient',0)) > 0}
    reference = json.loads((root/'reference/scores_test.json').read_text())['experiments'][EXP]['results'][PROPOSED]
    attempts = {}
    failures = {}
    for evidence_path in sorted(root.glob('*/evidence.json')):
        folder = evidence_path.parent
        evidence = json.loads(evidence_path.read_text())
        path = folder/'scores_test.json'
        if evidence.get('test_returncode') != 0 or not path.exists():
            failures[folder.name] = evidence
            continue
        data = json.loads(path.read_text())
        attempts[folder.name] = data.get('experiments',{}).get(EXP,{}).get('results',{}).get(PROPOSED,{})
    scales = {metric:float(np.std([x[metric] for x in attempts.values() if metric in x]))
              for metric in metrics}
    entries = {}
    for name, scores in attempts.items():
        contributions = {}
        raw = {}
        compared = []
        for metric, cfg in metrics.items():
            if metric not in scores or metric not in reference:
                continue
            direction = 1 if cfg['higher_is_better'] else -1
            improvement = direction * (scores[metric]-reference[metric])
            raw[metric] = improvement
            compared.append(improvement)
            contributions[metric] = (config['weight'] * abs(cfg['coefficient']) * improvement / scales[metric]) if scales[metric] else 0.0
        entries[name] = {'metrics':scores,'audit_cohort_rank_gain':sum(contributions.values()),
            'contributions':contributions,'directional_metric_gains':raw,
            'weakly_dominates_reference_on_reported_metrics':bool(compared) and all(v>=0 for v in compared),
            'strictly_dominates_reference_on_reported_metrics':bool(compared) and all(v>=0 for v in compared) and any(v>0 for v in compared),
            'missing_scored_metrics':[k for k in metrics if k not in scores]}
    seeds = {name:entry for name,entry in entries.items() if name.startswith('reference_seed')}
    spread = {}
    for metric in metrics:
        vals = [entry['metrics'][metric] for entry in seeds.values() if metric in entry['metrics']]
        spread[metric] = {'values':vals,'range':max(vals)-min(vals),'std':float(np.std(vals))} if vals else {}
    ranks = [entry['audit_cohort_rank_gain'] for entry in seeds.values()]
    out = {'reference':reference, 'normalization':'population std across successful audited attempts, missing values excluded',
           'metric_std':scales, 'attempts':entries,'failed_runs':failures,'seed_spread':spread,
           'seed_rank_range':max(ranks)-min(ranks) if ranks else None}
    (root/'summary.json').write_text(json.dumps(out,indent=2))
    print('name\tmean\tmin\tstd\tinvalid\tgap\tflag\trank_gain')
    for name,entry in entries.items():
        vals = entry['metrics']
        numbers = [vals.get(k) for k in ('atlas_accuracy_mean','atlas_accuracy_min','atlas_accuracy_std',
            'invalid_assignment_rate','gap_to_supervised_oracle','semantic_labels_used_for_training')]
        print(name, *[f'{v:.6f}' if v is not None else 'MISSING' for v in numbers],
              f"{entry['audit_cohort_rank_gain']:.6f}", sep='\t')
    print('SEED SPREAD',json.dumps(spread))
    print('FAILED RUNS',','.join(failures))


if __name__ == '__main__':
    main()
