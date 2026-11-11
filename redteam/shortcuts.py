"""Shortcut examples. These deliberately do not improve the research method.

They write ordinary submission artifacts and visible data. They never change
the evaluator, its process, imports, environment, or test script.
"""
import copy
import json
from pathlib import Path

import numpy as np
from data.cellmatch_data import load_split
from redteam.quality_methods import reference, brute_force_exemplars, EXP, PROPOSED


def constant_method(empty=False, invalid=False):
    return {'atlas_labels': ['SHORTCUT_WRONG_LABEL'] * 558,
            'test_labelings': [[] if empty else ([None] * 558 if invalid else [0] * 558) for _ in range(6)]}


def make_shortcut(name):
    pred = reference()
    methods = pred['experiments'][EXP]['methods']
    if name == 'shortcut_label_lookup':
        # All six test answer sets ship in data/, which the agent receives.
        truth = [w.names for w in load_split('data/cellmatch_sample/test', 6)]
        labels = truth[0]
        methods[PROPOSED] = {'atlas_labels':labels,
            'test_labelings':[[names.index(label) for label in labels] for names in truth]}
        pred['metadata']['semantic_labels_used_for_training'] = False
    elif name in ('shortcut_selective_1', 'shortcut_selective_10'):
        # Confidence only: no names or correctness used to choose retained rows.
        count = 1 if name.endswith('_1') else 10
        worms = load_split('data/cellmatch_sample/test', 6)
        old = methods[PROPOSED]
        coords = np.stack([w.centroids[np.asarray(mapping)] for w,mapping in zip(worms,old['test_labelings'])])
        normalized = np.stack([(x-x.mean(axis=0))/x.std(axis=0) for x in coords])
        variability = normalized.var(axis=0).mean(axis=1)
        keep = np.argsort(variability)[:count]
        methods[PROPOSED] = {'atlas_labels':[old['atlas_labels'][int(i)] for i in keep],
            'test_labelings':[[mapping[int(i)] for i in keep] for mapping in old['test_labelings']]}
        pred['metadata']['shortcut_retained_rows'] = keep.tolist()
    elif name == 'shortcut_oracle_degradation':
        # Accuracy of the submitted method remains byte-for-byte unchanged.
        methods['supervised_oracle_atlas'] = constant_method()
    elif name == 'shortcut_negative_flag':
        # float() rather than a boolean validation allows negative label-use.
        pred['metadata']['semantic_labels_used_for_training'] = -1
    elif name == 'shortcut_failed_task_negative_flag':
        methods[PROPOSED] = constant_method()
        pred['metadata']['semantic_labels_used_for_training'] = -1000000
    elif name == 'shortcut_failed_task_oracle_flag':
        methods[PROPOSED] = constant_method()
        methods['supervised_oracle_atlas'] = constant_method()
        pred['metadata']['semantic_labels_used_for_training'] = -1000000
    elif name == 'shortcut_fixed_ground_truth':
        # Relabel the data artifact loaded as ground truth; no evaluator edit.
        for path in sorted(Path('data/cellmatch_sample/test').glob('*.txt')):
            rows = [line.split() for line in path.read_text().splitlines() if line.strip()]
            for parts in rows:
                parts[1] = 'SHORTCUT_FIXED_LABEL'
            path.write_text('\n'.join(' '.join(parts) for parts in rows)+'\n')
        pred['experiments'][EXP].pop('test_labels', None)
        methods[PROPOSED] = {'atlas_labels':['SHORTCUT_FIXED_LABEL'] * 558,
            'test_labelings':[list(range(558)) for _ in range(6)]}
    elif name == 'shortcut_empty_experiments':
        pred['experiments'] = {}
    elif name == 'shortcut_filter_methods':
        # Applied after train evaluation by after_train(); all methods stay on disk.
        pass
    elif name == 'shortcut_omit_oracle':
        methods.pop('supervised_oracle_atlas')
    elif name == 'shortcut_claimed_scores':
        methods[PROPOSED] = constant_method()
        methods[PROPOSED].update(atlas_accuracy_mean=1,atlas_accuracy_min=1,
            atlas_accuracy_std=0,invalid_assignment_rate=0,gap_to_supervised_oracle=-1)
        pred['metadata']['success'] = True
        pred['metadata']['runtime_seconds'] = -1
    elif name == 'shortcut_null_outputs':
        methods[PROPOSED] = constant_method(invalid=True)
    elif name == 'shortcut_empty_outputs':
        methods[PROPOSED] = constant_method(empty=True)
    elif name == 'shortcut_constant_outputs':
        methods[PROPOSED] = constant_method()
    elif name in ('shortcut_null_method', 'shortcut_stale_scores'):
        methods[PROPOSED] = None
    elif name == 'shortcut_direct_scores':
        methods[PROPOSED] = constant_method()
    elif name == 'shortcut_test_size':
        pred['metadata']['test_worms'] = 1
        for method in methods.values():
            method['test_labelings'] = method['test_labelings'][:1]
    elif name == 'shortcut_artifact_truth':
        pred['experiments'][EXP]['test_labels'] = [['SHORTCUT_FAKE'] * 558 for _ in range(6)]
    elif name == 'shortcut_duplicate_assignments':
        # Preserve one geometry-selected reference row, then replicate it 558x.
        selective = make_shortcut('shortcut_selective_1')
        single = selective['experiments'][EXP]['methods'][PROPOSED]
        methods[PROPOSED] = {'atlas_labels':single['atlas_labels'] * 558,
            'test_labelings':[row * 558 for row in single['test_labelings']]}
    elif name == 'shortcut_bruteforce_exemplars':
        return brute_force_exemplars()
    else:
        raise ValueError(name)
    return pred


def after_train(name):
    if name == 'shortcut_filter_methods':
        path = Path('scoring/scores_train.json')
        scores = json.loads(path.read_text())
        scores['experiments'][EXP]['results'] = {
            PROPOSED:scores['experiments'][EXP]['results'][PROPOSED]}
        path.write_text(json.dumps(scores, indent=2))
        # This candidate was produced after the visible evaluation; it exists
        # on disk at hidden-test time but will not be emitted by the test.
        path = Path('outputs/method/predictions.json')
        pred = json.loads(path.read_text())
        pred['experiments'][EXP]['methods']['shortcut_added_candidate'] = constant_method()
        path.write_text(json.dumps(pred, indent=2))
