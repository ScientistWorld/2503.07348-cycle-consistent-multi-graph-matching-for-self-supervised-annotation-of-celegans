"""Algebraically identical vectorization of the reproduction's matching loop.

Only training/inference uses this module. The evaluator is never patched.
The offset-neighbor accumulation order and the exclusion matched==target are
preserved; small-loop and seed-7 artifact equivalence are recorded by the job.
"""
import numpy as np
from method import cycle_mgm as m


def pairwise_match(a, b, params, sparse=True, quadratic=True):
    base = m.unary_cost(a, b, params, sparse=sparse)
    labeling = m.solve_assignment(base)
    if not quadratic:
        return labeling
    neigh = np.asarray(m.nearest_neighbors(a, params.neighbor_count, params))
    target_indices = np.arange(len(b.names))[None, :]
    for _ in range(params.quadratic_iters):
        accum = np.zeros_like(base)
        used = np.zeros_like(base)
        mapping = np.asarray(labeling)
        for neighbor_slot in range(neigh.shape[1]):
            neighbors = neigh[:, neighbor_slot]
            matched = mapping[neighbors]
            off_a = a.centroids - a.centroids[neighbors]
            off_b = b.centroids[None, :, :] - b.centroids[np.maximum(matched, 0)][:, None, :]
            distances = m.mahalanobis(off_a[:, None, :], off_b, params.off_cov)
            valid = (matched[:, None] >= 0) & (matched[:, None] != target_indices)
            accum += np.where(valid, distances, 0.0)
            used += valid
        qcost = base + params.w_off * np.divide(accum, used, out=np.zeros_like(accum), where=used > 0)
        labeling = m.solve_assignment(qcost)
    return labeling


def install():
    m.pairwise_match = pairwise_match


def validate_equivalence():
    from data.cellmatch_data import load_split, limit_cells_by_input_order
    worms = limit_cells_by_input_order(load_split('data/cellmatch_sample/train', 2), 18)
    original = m.pairwise_match
    tests = []
    for sparse in (False, True):
        for quadratic in (False, True):
            params = m.Params()
            expected = original(*worms, params, sparse=sparse, quadratic=quadratic)
            actual = pairwise_match(*worms, params, sparse=sparse, quadratic=quadratic)
            assert actual == expected, (sparse, quadratic)
            tests.append({'sparse': sparse, 'quadratic': quadratic, 'identical_assignments': True})
    return tests
