"""Gaussian graph-matching toolkit for segmented C. elegans nuclei.

Standard machinery of the atlas-matching literature (Kainmueller et al., 2014;
the cellmatch code release), shared by the reproduction, its baseline and the
fixed supervised comparator:

* Mahalanobis unary costs on nucleus centroids and radii, and Mahalanobis
  pairwise costs on centroid offsets between neighbouring nuclei, with a
  constant ``c0`` subtracted from every assignment so matching is preferred
  over leaving a node unassigned;
* sparsification (keep the ``k_min`` cheapest candidates of every node plus all
  candidates within the centroid / radius distance thresholds);
* pairwise problems solved exactly as linear assignment (no pairwise terms) or
  with the Fusion Moves QAP solver from ``pylibmgm``;
* cycle-consistent synchronization of pairwise matchings with GREEDA
  (``pylibmgm.solver.synchronize_solution``);
* Gaussian atlases built from groups of corresponding nuclei (nucleus-specific
  centroid / radius covariances and pair-specific offset covariances);
* affine least-squares re-alignment from a fixed matching.

Labelings follow pylibmgm: ``labeling[i]`` is the node of the second graph
matched to node ``i`` of the first graph, or ``-1``.
"""
from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, fields

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linear_sum_assignment

try:  # pragma: no cover - import guard for environments without the solver
    import pylibmgm
    from pylibmgm.solver import OptimizationLevel, synchronize_solution

    logging.getLogger("libmgm").setLevel(logging.WARNING)
    logging.getLogger("libmgm.interface").setLevel(logging.WARNING)
except ImportError:  # pragma: no cover
    pylibmgm = None
    OptimizationLevel = None
    synchronize_solution = None

FORBIDDEN = 1e12


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------


@dataclass
class WormParams:
    """Cross-nucleus (label-independent) worm-to-worm matching parameters."""

    cen_var: tuple = (1.0, 1.0, 1.0)  # diagonal centroid covariance
    rad_var: tuple = (1.0, 1.0, 1.0)  # diagonal radius covariance
    off_var: tuple = (1.0, 1.0, 1.0)  # diagonal offset covariance
    w_cen: float = 1.0
    w_rad: float = 1.0
    w_off: float = 1.0
    c0: float = 10000.0  # unassignment constant (subtracted from every assignment)
    k_min: int = 0  # 0 = dense problem (no sparsification)
    tau_cen: float = math.inf
    tau_rad: float = math.inf
    neighbor_count: int = 3

    def to_dict(self) -> dict:
        out = asdict(self)
        for key in ("cen_var", "rad_var", "off_var"):
            out[key] = [float(v) for v in out[key]]
        for key in ("tau_cen", "tau_rad"):
            if math.isinf(out[key]):
                out[key] = "inf"
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "WormParams":
        names = {f.name for f in fields(cls)}
        kwargs = {}
        for key, value in data.items():
            if key not in names:
                continue
            if key in ("cen_var", "rad_var", "off_var"):
                value = tuple(float(v) for v in value)
            elif key in ("tau_cen", "tau_rad"):
                value = math.inf if value in ("inf", None) else float(value)
            kwargs[key] = value
        return cls(**kwargs)


# --------------------------------------------------------------------------
# Distances, sparsity, neighbourhoods
# --------------------------------------------------------------------------


def diag_mahalanobis(a: np.ndarray, b: np.ndarray, var) -> np.ndarray:
    """All-pairs squared Mahalanobis distances with a diagonal covariance."""
    var = np.asarray(var, dtype=float)
    return (((a[:, None, :] - b[None, :, :]) ** 2) / var).sum(-1)


def worm_unary(ref, tar, p: WormParams) -> tuple[np.ndarray, np.ndarray]:
    return (
        diag_mahalanobis(ref.centroids, tar.centroids, p.cen_var),
        diag_mahalanobis(ref.radii, tar.radii, p.rad_var),
    )


def sparsity_mask(cost: np.ndarray, d_cen: np.ndarray, d_rad: np.ndarray, k_min: int,
                  tau_cen: float, tau_rad: float) -> np.ndarray | None:
    """cellmatch sparsification: the ``k_min`` cheapest candidates of every row and
    column, plus every candidate with ``d_cen < tau_cen`` and ``d_rad < tau_rad``.
    Returns ``None`` for a dense problem."""
    n, m = cost.shape
    if k_min is None or k_min <= 0:
        return None
    mask = (d_cen < tau_cen) & (d_rad < tau_rad)
    kr = min(int(k_min), m)
    if kr >= m:
        return None
    rows = np.argpartition(cost, kr - 1, axis=1)[:, :kr]
    mask[np.arange(n)[:, None], rows] = True
    kc = min(int(k_min), n)
    if kc < n:
        cols = np.argpartition(cost, kc - 1, axis=0)[:kc, :]
        mask[cols, np.arange(m)[None, :]] = True
    else:
        mask[:, :] = True
    return mask


def knn_graph(centroids: np.ndarray, var, k: int) -> sp.csr_matrix:
    """Symmetric k-nearest-neighbour graph under a diagonal Mahalanobis distance."""
    n = centroids.shape[0]
    d = diag_mahalanobis(centroids, centroids, var)
    np.fill_diagonal(d, np.inf)
    k = min(int(k), n - 1)
    idx = np.argpartition(d, k - 1, axis=1)[:, :k]
    rows = np.repeat(np.arange(n), k)
    graph = sp.csr_matrix((np.ones(n * k, dtype=np.int8), (rows, idx.ravel())), shape=(n, n))
    graph = ((graph + graph.T) > 0).astype(np.int8)
    graph.setdiag(0)
    graph.eliminate_zeros()
    return graph.tocsr()


# --------------------------------------------------------------------------
# Solvers
# --------------------------------------------------------------------------


def solve_lap(cost: np.ndarray, mask: np.ndarray | None, c0: float) -> np.ndarray:
    """Exact incomplete linear assignment with assignment costs ``cost - c0``."""
    c = cost - c0
    if mask is not None:
        c = np.where(mask, c, FORBIDDEN)
    rows, cols = linear_sum_assignment(c)
    labeling = np.full(cost.shape[0], -1, dtype=int)
    valid = c[rows, cols] < 0
    if mask is not None:
        valid &= mask[rows, cols]
    labeling[rows[valid]] = cols[valid]
    return labeling


def _edge_list(ii: np.ndarray, ss: np.ndarray, nbr_ref: sp.csr_matrix, nbr_tar: sp.csr_matrix):
    """Pairs of assignments (a, b), a < b, whose left nodes are neighbours in the
    reference or whose right nodes are neighbours in the target (cellmatch rule)."""
    n_a = len(ii)
    eye = np.ones(n_a, dtype=np.int32)
    a_l = sp.csr_matrix((eye, (np.arange(n_a), ii)), shape=(n_a, nbr_ref.shape[0]))
    a_r = sp.csr_matrix((eye, (np.arange(n_a), ss)), shape=(n_a, nbr_tar.shape[0]))
    pairs = a_l @ nbr_ref.astype(np.int32) @ a_l.T + a_r @ nbr_tar.astype(np.int32) @ a_r.T
    pairs = sp.triu(pairs, k=1).tocoo()
    a, b = pairs.row.astype(np.int64), pairs.col.astype(np.int64)
    keep = (ii[a] != ii[b]) & (ss[a] != ss[b])
    return a[keep], b[keep]


def build_gm_model(unary: np.ndarray, mask: np.ndarray | None, c0: float,
                   ref_cen: np.ndarray, tar_cen: np.ndarray,
                   nbr_ref: sp.csr_matrix | None, nbr_tar: sp.csr_matrix | None,
                   off_prec, w_off: float, gids=(0, 1)):
    """pylibmgm GmModel with unary costs ``unary - c0`` on allowed assignments and
    pairwise offset costs ``w_off * (dt - dr)^T P_ij (dt - dr)`` on neighbouring
    assignment pairs. ``off_prec`` is a diagonal precision (3,) or a per-label-pair
    precision array (K, K, 3, 3)."""
    n, m = unary.shape
    if mask is None:
        ii, ss = np.divmod(np.arange(n * m), m)
    else:
        ii, ss = np.nonzero(mask)
    costs = unary[ii, ss] - c0
    quadratic = nbr_ref is not None and w_off > 0
    if quadratic:
        a, b = _edge_list(ii, ss, nbr_ref, nbr_tar)
        i, j, s, t = ii[a], ii[b], ss[a], ss[b]
        diff = (tar_cen[t] - tar_cen[s]) - (ref_cen[j] - ref_cen[i])
        off_prec = np.asarray(off_prec, dtype=float)
        if off_prec.ndim == 1:
            q = (diff * diff * off_prec).sum(-1)
        else:
            q = np.einsum("ek,ekl,el->e", diff, off_prec[i, j], diff)
        edge_costs = w_off * q
    else:
        a = b = np.zeros(0, dtype=np.int64)
        edge_costs = np.zeros(0)
    g1 = pylibmgm.Graph(int(gids[0]), int(n))
    g2 = pylibmgm.Graph(int(gids[1]), int(m))
    model = pylibmgm.GmModel(g1, g2, int(len(ii)), int(len(a)))
    add_assignment = model.add_assignment
    for x, y, c in zip(ii.tolist(), ss.tolist(), costs.tolist()):
        add_assignment(x, y, c)
    if len(a):
        add_edge = model.add_edge
        for x1, y1, x2, y2, c in zip(ii[a].tolist(), ss[a].tolist(), ii[b].tolist(), ss[b].tolist(),
                                     edge_costs.tolist()):
            add_edge(x1, y1, x2, y2, c)
    return model


def set_qap_seed(seed: int | None) -> None:
    if seed is None or pylibmgm is None:
        return
    try:
        pylibmgm.QAPSolver.libmpopt_seed = int(seed) % (2 ** 31)
    except Exception:  # pragma: no cover - older bindings
        pass


def solve_qap(model, seed: int | None = None) -> np.ndarray:
    set_qap_seed(seed)
    if model.no_edges() == 0:
        sol = pylibmgm.LAPSolver(model).run()
    else:
        sol = pylibmgm.QAPSolver(model).run()
    return np.asarray(sol.labeling(), dtype=int)


def match_worms(ref, tar, p: WormParams, quadratic: bool, seed: int | None = None) -> np.ndarray:
    """Worm-to-worm graph matching under cross-nucleus parameters ``p``."""
    d_cen, d_rad = worm_unary(ref, tar, p)
    cost = p.w_cen * d_cen + p.w_rad * d_rad
    mask = sparsity_mask(cost, d_cen, d_rad, p.k_min, p.tau_cen, p.tau_rad)
    if not quadratic or p.w_off <= 0:
        return solve_lap(cost, mask, p.c0)
    if mask is None:
        raise ValueError("quadratic matching requires a sparse problem (k_min > 0)")
    nbr_ref = knn_graph(ref.centroids, p.cen_var, p.neighbor_count)
    nbr_tar = knn_graph(tar.centroids, p.cen_var, p.neighbor_count)
    off_prec = 1.0 / np.asarray(p.off_var, dtype=float)
    model = build_gm_model(cost, mask, p.c0, ref.centroids, tar.centroids, nbr_ref, nbr_tar,
                           off_prec, p.w_off)
    return solve_qap(model, seed)


def allowed_assignments(ref, tar, p: WormParams) -> int:
    d_cen, d_rad = worm_unary(ref, tar, p)
    mask = sparsity_mask(p.w_cen * d_cen + p.w_rad * d_rad, d_cen, d_rad, p.k_min, p.tau_cen, p.tau_rad)
    return int(d_cen.size if mask is None else mask.sum())


# --------------------------------------------------------------------------
# Multi-graph synchronization
# --------------------------------------------------------------------------


def synchronize(labelings: dict, sizes: list[int], iterations: int = 3, opt_level=None,
                feasible: bool = False):
    """Cycle-consistent approximation of independently solved pairwise matchings
    (GREEDA synchronization; ``feasible=False`` is the dense mode)."""
    if opt_level is None:
        opt_level = OptimizationLevel.DEFAULT
    model = pylibmgm.MgmModel()
    for (a, b) in sorted(labelings):
        model.add_model(pylibmgm.GmModel(pylibmgm.Graph(int(a), int(sizes[a])),
                                         pylibmgm.Graph(int(b), int(sizes[b]))))
    solution = pylibmgm.MgmSolution(model)
    for (a, b), lab in labelings.items():
        solution.set_solution((int(a), int(b)), [int(x) for x in lab])
    return synchronize_solution(model, solution, feasible=feasible, iterations=iterations,
                                opt_level=opt_level)


def sync_labelings(sync_solution) -> dict:
    return {tuple(k): np.asarray(v, dtype=int) for k, v in sync_solution.labeling().items()}


def cliques_to_membership(cliques: list[dict], sizes: list[int]) -> list[np.ndarray]:
    """Per-worm arrays mapping each node to its clique id (or -1)."""
    member = [np.full(n, -1, dtype=int) for n in sizes]
    for cid, clique in enumerate(cliques):
        for g, node in clique.items():
            g, node = int(g), int(node)
            if node >= 0:
                member[g][node] = cid
    return member


# --------------------------------------------------------------------------
# Affine re-alignment
# --------------------------------------------------------------------------


def affine_fit_diag(x: np.ndarray, y: np.ndarray, cen_prec, off_prec=None, reg: float = 1e-5):
    """Affine map ``R y + o ~ x`` minimising the diagonal-precision weighted unary
    residuals plus (optionally) the residuals of all pairwise centroid offsets."""
    cen_prec = np.asarray(cen_prec, dtype=float)
    n = len(x)
    y1 = np.column_stack([y, np.ones(n)])
    gram = y1.T @ y1
    yc = y - y.mean(0)
    xc = x - x.mean(0)
    cyy = yc.T @ yc
    r = np.zeros((3, 3))
    o = np.zeros(3)
    for k in range(3):
        h = cen_prec[k] * gram
        g = cen_prec[k] * (y1.T @ x[:, k])
        if off_prec is not None:
            w = float(np.asarray(off_prec, dtype=float)[k]) * n
            h[:3, :3] += w * cyy
            g[:3] += w * (yc.T @ xc[:, k])
        theta = np.linalg.solve(h + reg * np.eye(4), g)
        r[k] = theta[:3]
        o[k] = theta[3]
    return r, o


def affine_fit_general(x: np.ndarray, y: np.ndarray, p_unary: np.ndarray, p_pair=None,
                       pair_index=None, reg: float = 1e-5):
    """Affine map ``R y + o ~ x`` minimising ``sum_i r_i^T P_i r_i`` plus, if given,
    ``sum_{i<j} (R dy_ij - dx_ij)^T P_ij (R dy_ij - dx_ij)`` over all node pairs."""
    h = np.zeros((12, 12))
    g = np.zeros(12)
    h[:9, :9] += np.einsum("ikm,il,in->klmn", p_unary, y, y).reshape(9, 9)
    rr_o = np.einsum("ikm,il->klm", p_unary, y).reshape(9, 3)
    h[:9, 9:] += rr_o
    h[9:, :9] += rr_o.T
    h[9:, 9:] += p_unary.sum(0)
    px = np.einsum("ikm,im->ik", p_unary, x)
    g[:9] += np.einsum("ik,il->kl", px, y).reshape(9)
    g[9:] += px.sum(0)
    if p_pair is not None:
        i_idx, j_idx = pair_index
        dy = y[j_idx] - y[i_idx]
        dx = x[j_idx] - x[i_idx]
        h[:9, :9] += np.einsum("pkm,pl,pn->klmn", p_pair, dy, dy).reshape(9, 9)
        g[:9] += np.einsum("pkm,pm,pl->kl", p_pair, dx, dy).reshape(9)
    theta = np.linalg.solve(h + reg * np.eye(12), g)
    return theta[:9].reshape(3, 3), theta[9:]


def apply_affine(points: np.ndarray, r: np.ndarray, o: np.ndarray) -> np.ndarray:
    return points @ r.T + o


# --------------------------------------------------------------------------
# Gaussian atlas
# --------------------------------------------------------------------------


@dataclass
class Atlas:
    labels: np.ndarray  # (K,) group ids
    cen_mean: np.ndarray  # (K, 3)
    rad_mean: np.ndarray  # (K, 3)
    cen_prec: np.ndarray  # (K, 3, 3)
    rad_prec: np.ndarray  # (K, 3, 3)
    off_prec: np.ndarray  # (K, K, 3, 3)
    neighbors: sp.csr_matrix  # (K, K)
    w_cen: float = 1.0
    w_rad: float = 1.0
    w_off: float = 1.0
    c0: float = 10000.0
    k_min: int = 11
    tau_cen: float = 16.0  # 4 sigma
    tau_rad: float = 25.0  # 5 sigma

    @property
    def size(self) -> int:
        return int(len(self.labels))


def _masked_cov(x: np.ndarray, m: np.ndarray):
    """Per-group mean and covariance (ddof=1) of x (N, K, 3) over members m (N, K)."""
    w = m.astype(float)
    cnt = w.sum(0)
    xz = np.where(m[..., None], x, 0.0)
    mean = xz.sum(0) / np.maximum(cnt, 1)[:, None]
    second = np.einsum("nk,nki,nkj->kij", w, xz, xz)
    cov = (second - cnt[:, None, None] * np.einsum("ki,kj->kij", mean, mean)) / np.maximum(cnt - 1, 1)[:, None, None]
    return mean, cov, cnt


def _regularize_covs(cov: np.ndarray, det_threshold: float) -> np.ndarray:
    det = np.linalg.det(cov)
    bad = ~(det >= det_threshold)
    if bad.all():
        return np.broadcast_to(np.eye(3), cov.shape).copy()
    cov = cov.copy()
    cov[bad] = cov[~bad].mean(0)
    return cov


def pairwise_offset_cov(x: np.ndarray, m: np.ndarray):
    """Covariances of centroid offsets x_b - x_a over worms containing both groups.
    Returns (K, K, 3, 3) covariances and (K, K) common-worm counts."""
    w = m.astype(float)
    xz = np.where(m[..., None], x, 0.0)
    cnt = w.T @ w
    s_b = np.einsum("na,nbk->abk", w, xz)  # sum of x_b over common worms
    s_a = np.einsum("nak,nb->abk", xz, w)  # sum of x_a over common worms
    s_bb = np.einsum("na,nbk,nbl->abkl", w, xz, xz)
    s_aa = np.einsum("nak,nal,nb->abkl", xz, xz, w)
    s_ab = np.einsum("nak,nbl->abkl", xz, xz)  # sum x_a x_b^T
    second = s_bb + s_aa - s_ab - np.swapaxes(s_ab, -1, -2)
    mean = (s_b - s_a) / np.maximum(cnt, 1)[..., None]
    cov = (second - cnt[..., None, None] * np.einsum("abk,abl->abkl", mean, mean))
    cov /= np.maximum(cnt - 1, 1)[..., None, None]
    return cov, cnt


def build_atlas(x: np.ndarray, r: np.ndarray, member: np.ndarray, group_ids: np.ndarray,
                weights=(1.0, 1.0, 1.0), min_members: int | None = None,
                iqr_factor: float = 3.2, det_threshold: float = 1e-5, neighbor_k: int = 6,
                shrinkage: float = 0.0, **matching) -> Atlas:
    """Gaussian atlas from groups of corresponding nuclei (cellmatch AtlasBuilder).

    x, r: (N, G, 3) centroids / radii of the member of group g in worm n;
    member: (N, G) bool. Groups with an outlier-free member count at or below
    ``min_members`` (default floor(N/2) + 2) are dropped. ``shrinkage`` blends
    every covariance with the pooled covariance (0 = paper's empirical estimate).
    """
    n_worms = x.shape[0]
    m = member.copy()
    # centroid outliers per group and axis (IQR rule)
    xn = np.where(m[..., None], x, np.nan)
    with np.errstate(all="ignore"):
        q1 = np.nanquantile(xn, 0.25, axis=0)
        q3 = np.nanquantile(xn, 0.75, axis=0)
    iqr = q3 - q1
    low, high = q1 - iqr_factor * iqr, q3 + iqr_factor * iqr
    with np.errstate(invalid="ignore"):
        outlier = ((x < low[None]) | (x > high[None])).any(-1)
    m &= ~outlier
    if min_members is None:
        min_members = int(math.floor(0.5 * n_worms)) + 2
    keep = m.sum(0) > min_members
    x, r, m = x[:, keep], r[:, keep], m[:, keep]
    labels = np.asarray(group_ids)[keep]
    cen_mean, cen_cov, _ = _masked_cov(x, m)
    rad_mean, rad_cov, _ = _masked_cov(r, m)
    if shrinkage > 0:
        cen_cov = (1 - shrinkage) * cen_cov + shrinkage * cen_cov.mean(0)
        rad_cov = (1 - shrinkage) * rad_cov + shrinkage * rad_cov.mean(0)
    cen_cov = _regularize_covs(cen_cov, det_threshold)
    rad_cov = _regularize_covs(rad_cov, det_threshold)
    off_cov, cnt = pairwise_offset_cov(x, m)
    k = len(labels)
    diag = np.arange(k)
    off_cov[diag, diag] = np.eye(3)
    if shrinkage > 0:
        valid = cnt >= 2
        valid[diag, diag] = False
        pooled = off_cov[valid].mean(0)
        off_cov = (1 - shrinkage) * off_cov + shrinkage * pooled
    det = np.linalg.det(off_cov)
    singular = ~(det > 1e-9) | (cnt < 3)
    singular[diag, diag] = False
    if singular.any():
        valid = ~singular
        valid[diag, diag] = False
        fallback = off_cov[valid].mean(0) if valid.any() else np.eye(3)
        off_cov[singular] = fallback
        det = np.linalg.det(off_cov)
    det_rank = det.copy()
    det_rank[diag, diag] = np.inf
    nk = min(neighbor_k, k - 1)
    idx = np.argpartition(det_rank, nk - 1, axis=1)[:, :nk]
    rows = np.repeat(np.arange(k), nk)
    nbr = sp.csr_matrix((np.ones(k * nk, dtype=np.int8), (rows, idx.ravel())), shape=(k, k))
    nbr = ((nbr + nbr.T) > 0).astype(np.int8).tocsr()
    nbr.setdiag(0)
    nbr.eliminate_zeros()
    return Atlas(
        labels=labels,
        cen_mean=cen_mean,
        rad_mean=rad_mean,
        cen_prec=np.linalg.inv(cen_cov),
        rad_prec=np.linalg.inv(rad_cov),
        off_prec=np.linalg.inv(off_cov),
        neighbors=nbr.tocsr(),
        w_cen=float(weights[0]),
        w_rad=float(weights[1]),
        w_off=float(weights[2]),
        **matching,
    )


def atlas_unary(atlas: Atlas, tar) -> tuple[np.ndarray, np.ndarray]:
    dc = tar.centroids[None, :, :] - atlas.cen_mean[:, None, :]
    dr = tar.radii[None, :, :] - atlas.rad_mean[:, None, :]
    d_cen = np.einsum("kmi,kij,kmj->km", dc, atlas.cen_prec, dc, optimize=True)
    d_rad = np.einsum("kmi,kij,kmj->km", dr, atlas.rad_prec, dr, optimize=True)
    return d_cen, d_rad


def match_atlas(atlas: Atlas, tar, target_nbr_var=(1.0, 1.0, 1.0), target_nbr_k: int = 3,
                quadratic: bool = True, seed: int | None = None) -> np.ndarray:
    """Worm-to-atlas graph matching; returns labeling atlas index -> target node."""
    d_cen, d_rad = atlas_unary(atlas, tar)
    cost = atlas.w_cen * d_cen + atlas.w_rad * d_rad
    mask = sparsity_mask(cost, d_cen, d_rad, atlas.k_min, atlas.tau_cen, atlas.tau_rad)
    if not quadratic or atlas.w_off <= 0:
        return solve_lap(cost, mask, atlas.c0)
    nbr_tar = knn_graph(tar.centroids, target_nbr_var, target_nbr_k)
    model = build_gm_model(cost, mask, atlas.c0, atlas.cen_mean, tar.centroids, atlas.neighbors,
                           nbr_tar, atlas.off_prec, atlas.w_off)
    return solve_qap(model, seed)


def node_labels(atlas: Atlas, labeling: np.ndarray, n_nodes: int) -> np.ndarray:
    """Convert an atlas->target labeling into per-target-node atlas label ids."""
    out = np.full(n_nodes, -1, dtype=int)
    for k, node in enumerate(np.asarray(labeling)):
        if node >= 0:
            out[int(node)] = int(atlas.labels[k])
    return out


def realign_to_atlas(atlas: Atlas, tar, labeling: np.ndarray, use_pairwise: bool = True):
    """Affine re-alignment of a worm onto the atlas from a fixed matching."""
    lab = np.asarray(labeling)
    ks = np.nonzero(lab >= 0)[0]
    x = atlas.cen_mean[ks]
    y = tar.centroids[lab[ks]]
    pair_index = None
    p_pair = None
    if use_pairwise:
        iu, ju = np.triu_indices(len(ks), 1)
        pair_index = (iu, ju)
        p_pair = atlas.off_prec[ks[iu], ks[ju]]
    r, o = affine_fit_general(x, y, atlas.cen_prec[ks], p_pair, pair_index)
    return tar.with_centroids(apply_affine(tar.centroids, r, o)), (r, o)
