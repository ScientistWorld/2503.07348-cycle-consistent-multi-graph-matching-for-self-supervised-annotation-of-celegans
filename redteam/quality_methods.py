"""Genuine variants use geometric features only for correspondence and fitting.

Semantic names are read only after fitting to apply the reproduction's fixed
clique-to-name evaluation convention. No held-out names select any setting.
"""
import argparse
import copy
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from data.cellmatch_data import Worm, load_split
from method import cycle_mgm as m
from redteam.fast_method import install

EXP = 'scaled_manual_segmentation'
PROPOSED = 'our_unsupervised_atlas'


def reference():
    return json.loads(Path('redteam/reference/predictions.json').read_text())


def original_training(seed, trials):
    install()
    args = argparse.Namespace(train_dir='data/cellmatch_sample/train',
        test_dir='data/cellmatch_sample/test', output='outputs/method/predictions.json',
        train_worms=12, learn_worms=6, test_worms=6, cells=0, trials=trials,
        seed=seed, loss='sync', sparsity_limit=12000.0)
    m.run(args)
    pred = json.loads(Path(args.output).read_text())
    # Hold the other side of the comparison fixed for all honest variants.
    fixed = reference()['experiments'][EXP]['methods']
    for name in ('supervised_oracle_atlas', 'unlearned_linear_baseline'):
        pred['experiments'][EXP]['methods'][name] = copy.deepcopy(fixed[name])
    return pred


def affine_fit(source, target, labeling):
    """Least-squares affine realignment from feature-derived assignments only."""
    mapping = np.asarray(labeling)
    valid = mapping >= 0
    design = np.column_stack([source.centroids[mapping[valid]], np.ones(np.sum(valid))])
    transform = np.linalg.lstsq(design, target.centroids[valid], rcond=None)[0]
    return Worm(source.worm_id, source.names,
        np.column_stack([source.centroids, np.ones(len(source.names))]) @ transform,
        source.radii)


def realignment():
    """Repair omitted affine registration while retaining learned GM + atlas."""
    install()
    train = load_split('data/cellmatch_sample/train', 12)
    test = load_split('data/cellmatch_sample/test', 6)
    pred = reference()
    learned = m.Params(**pred['metadata']['params'])
    unlearned = m.Params(cen_cov=(1,1,1), rad_cov=(1,1,1), off_cov=(1,1,1), tau_cen=1e9, tau_rad=1e9)
    initial_pairs = m.all_pairwise(train, unlearned, sparse=False, quadratic=False)
    initial_cliques = m.synchronize_cliques(train, initial_pairs)
    # Same agreement criterion as the existing pivot synchronizer.
    n = len(train[0].names)
    scores = [sum(int(m.get_mapping(initial_pairs, i, j, n)[c[i]] == c[j])
                  for c in initial_cliques for j in c if j != i)
              for i in range(len(train))]
    pivot = int(np.argmax(scores))
    target = train[pivot]
    for params, quadratic in ((unlearned, False), (learned, True)):
        for iteration in range(7):
            print('affine registration', quadratic, iteration, flush=True)
            train = [affine_fit(w, target, m.pairwise_match(target, w, params, sparse=quadratic, quadratic=quadratic))
                     if i != pivot else target for i,w in enumerate(train)]
            test = [affine_fit(w, target, m.pairwise_match(target, w, params, sparse=quadratic, quadratic=quadratic)) for w in test]
    pairs = m.all_pairwise(train, learned, sparse=True, quadratic=True)
    cliques = m.synchronize_cliques(train, pairs)
    labels = m.induce_clique_labels(cliques, train)
    atlas = m.build_atlas(cliques, train, labels)
    pred['experiments'][EXP]['methods'][PROPOSED] = {
        'atlas_labels': atlas.names,
        'test_labelings': m.match_atlas(atlas, test, learned, quadratic=True),
        'pre_atlas_accuracies': m.evaluate_pre_atlas(cliques, labels, train)}
    pred['metadata']['audit_variant'] = 'feature-only affine registration, fixed seed-7 costs and fixed oracle'
    pred['metadata']['semantic_labels_used_for_training'] = False
    return pred


def remove_quadratic():
    install()
    pred = reference()
    train = load_split('data/cellmatch_sample/train', 12)
    test = load_split('data/cellmatch_sample/test', 6)
    params = m.Params(**pred['metadata']['params'])
    pairs = m.all_pairwise(train, params, sparse=True, quadratic=False)
    cliques = m.synchronize_cliques(train, pairs)
    labels = m.induce_clique_labels(cliques, train)
    atlas = m.build_atlas(cliques, train, labels)
    pred['experiments'][EXP]['methods'][PROPOSED] = {
        'atlas_labels': labels, 'test_labelings': m.match_atlas(atlas, test, params, quadratic=False)}
    return pred


def brute_force_exemplars():
    """Dense matching to EVERY training exemplar; no covariance learning/MGM.

    This actually enumerates the tractable candidate set, not the 558!
    permutations, whose exhaustive enumeration is infeasible at this scale.
    Names are induced using the reference's clique evaluation convention only.
    """
    install()
    pred = reference()
    train = load_split('data/cellmatch_sample/train', 12)
    test = load_split('data/cellmatch_sample/test', 6)
    params = m.Params(cen_cov=(1,1,1), rad_cov=(1,1,1), tau_cen=1e9, tau_rad=1e9)
    pairs = m.all_pairwise(train, params, sparse=False, quadratic=False)
    cliques = m.synchronize_cliques(train, pairs)
    names = m.induce_clique_labels(cliques, train)
    labelings = []
    diagnostics = []
    for target in test:
        candidates = []
        for wid, worm in enumerate(train):
            costs = m.unary_cost(worm, target, params, sparse=False)
            labeling = m.solve_assignment(costs)
            candidates.append((float(costs[np.arange(len(labeling)), labeling].mean()), wid, labeling))
        cost, wid, labeling = min(candidates)
        labelings.append([labeling[clique[wid]] for clique in cliques])
        diagnostics.append({'exemplar':wid, 'cost':cost, 'enumerated_exemplars':12,
                            'dense_candidate_edges_per_exemplar':558**2})
    pred['metadata']['enumeration'] = diagnostics
    pred['experiments'][EXP]['methods'][PROPOSED] = {'atlas_labels':names, 'test_labelings':labelings}
    return pred
