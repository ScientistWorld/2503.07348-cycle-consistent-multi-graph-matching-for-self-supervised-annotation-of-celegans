# Hardening report — 2503.07348 (cycle-consistent MGM, label-free C. elegans atlas)

**Bottom line.** Better results now score higher and worse ones lower, by margins far above the test's noise:
- An atlas-covariance-shrinkage variant beats the reference by **+4.9 to +5.9 accuracy points** on every one of three seeds. Each comparison is paired: same pool correspondences, same hidden worms.
- The reference's own seed range is **0.38 points**.
- Every major shortcut from REDTEAM.md and the two new ones found during hardening are closed. Each now scores the worst value or ties the reference with zero gain.
- The reference is now the paper's own pipeline, rebuilt on the authors' solver library (`pylibmgm`). On 10 hidden worms it scores **0.892**. The supervised comparator (same data, all pool names) scores 0.917; the unlearned baseline scores 0.798.

All numbers below come from the unmodified, no-argument `bash scripts/evaluate_test.sh`; evidence is in `hardening/cases/<case>/`. A case marked "failed" received the evaluator's worst value in every metric.
- Rank gain = Σ |coef| · Δ / SD_cohort over the two ranked metrics. SD_cohort is the spread across all audited cases. The zero-score shortcuts inflate it, so compare a rank gain against the seed rank range (0.006), not against 1.

## 1. What changed in the gym

| Area | Before (REDTEAM.md) | After |
|---|---|---|
| Answers | Names in column 2 of every visible worm table (`data/cellmatch_sample`), including the test worms. | Visible tables hold `x y z r1 r2 r3` only, rows shuffled per worm. Pool and test names live only in `eval/test/keys.json`. |
| Test inputs | Visible, so a submission could train on them. | The 10 hidden worms live only in `eval/test/worms/`. |
| Submission | One JSON with labelings, flags and metadata. | `outputs/<name>/predictions.json` (pool groups) plus `annotate.sh`. Both evaluators call `annotate.sh` on one worm per call, 900 s limit. A submission still supplies its own procedure. |
| Naming of identities | Done inside `method/` with training names. | Done by the evaluator. Hidden side: greedy maximum voting over the hidden pool names, paper Sec. 3.3. Visible side: leave-one-out over dev worms. |
| Visible labels | All training and test names. | 4 dev worms, labels for a fixed random **10 %** of identities (56 of 558). |
| Comparators | Oracle and baseline predictions were part of the editable artifact; the gap used them. | Frozen in `eval/test/fixed/`. The visible side stores only their frozen scores, because raw supervised labelings would hand out correspondences. |
| Constraint metrics | Self-reported `semantic_labels_used_for_training` flag (accepted −1e6). `invalid_assignment_rate` only penalised. | Flag removed. Label-freeness is enforced structurally. Any invalid, duplicate, missing or crashed output fails the run. |
| Failed runs | Exception, no fresh scores, missing entries skipped by the rank. | Always written. Each failed method gets the worst value of every metric. The ranked entry `our_unsupervised_atlas` is always emitted. |
| Method enumeration | Whitelisted by the editable `scores_train.json`. | Every directory under `outputs/` plus the frozen comparators; nothing else is read. |
| Hidden test size | 3 worms. | 10 worms; the visible side has 4. |

### Restored paper method (the reference)
REDTEAM.md listed the reproduction's departures from the paper. All of them are restored except scale:

- **Pairwise GM:** Fusion Moves, via `pylibmgm.QAPSolver`. Uses the cellmatch cost model: Mahalanobis unary and offset costs, unassignment constant c0, sparsification K_min/τ, and k = 3 symmetric neighbourhoods.
- **MGM:** dense GREEDA synchronisation of the independent pairwise solutions.
- **Realignment:** the star-centre target worm (dense unlearned matching plus dense sync) and 7 affine re-alignment iterations before BO and 7 after. Held-out worms get the same steps inside `annotate.sh`.
- **BO:** three stages with Optuna TPE and the synchronisation loss. Stage 2 is multi-objective and uses the paper's Pareto rule (mean allowed assignments < 12000, within 0.05 % of the best loss, then the fewest assignments). Parameter bounds follow the authors' code.
- **c0:** 10000 for learning and atlas matching, 40 for the final MGM (App. B).
- **Atlas:** nucleus-specific means and full covariances, plus pair-specific offset covariances. IQR outlier removal, sparse-label removal and determinant-based neighbours follow cellmatch's AtlasBuilder.
- **Atlas weights:** λ = ‖diag Σ‖, normalised to length √3 (Sec. 3.3).
- **Supervised comparator:** paper App. E, simplified.
  - Matches the paper: ground-truth affine alignment to the best base worm, a supervised Gaussian atlas, and λ = (0.48, 0.34, 0.81).
  - Simplified: held-out worms get iterative atlas re-alignment in place of [12]'s procedure.

**Remaining scale-downs:**
- 12 pool worms instead of 100, and 10 test worms instead of 100. These are the 26 public preprocessed worms; using the full 13 GB Zenodo image set would need the segmentation-to-ellipsoid pipeline re-implemented.
- N_learn = 6 instead of 15.
- 30/30/10 BO trials instead of 500 per stage.
- One GREEDA restart per loss evaluation. Stage 1 uses dense sync, which on dense problems equals the sparse mode; stages 2–3 use the paper's sparse mode.

## 2. Do better results score higher?

Hidden test, 10 worms. The shrinkage variants are paired with their seed's reference: same pool correspondences, same hidden worms. The weaker variants and the 2× BO diagnostic were built on an earlier seed-7 run of the same code (0.887 in the previous layout); `scripts/run.sh` rebuilds them on the final reference.

| Case | Mean acc. | Worst worm | Δ mean vs reference | Rank gain | Before (REDTEAM, old gym) |
|---|---:|---:|---:|---:|---|
| **Reference, seed 7** (`outputs/our_unsupervised_atlas`) | **0.8919** | **0.8172** | — | 0 | 0.7037 / 0.4964 |
| Reference, seed 8 | 0.8946 | 0.8082 | +0.27 | +0.001 | 0.7981 |
| Reference, seed 9 | 0.8957 | 0.8136 | +0.38 | +0.006 | 0.7001 |
| Better: atlas covariance shrinkage 0.3, seed 7 | 0.9511 | 0.8907 | **+5.92** | +0.177 | — |
| Better: shrinkage 0.3, seed 8 (vs ref seed 8) | 0.9530 | 0.9176 | **+5.84** | +0.197 | — |
| Better: shrinkage 0.3, seed 9 (vs ref seed 9) | 0.9450 | 0.9086 | **+4.93** | +0.174 | — |
| Better: shrinkage 0.5, seed 7 | 0.9470 | 0.8943 | +5.50 | +0.170 | — |
| Diagnostic: 2× BO search (60/60/20 trials) | 0.8900 | 0.8047 | −0.19 (tie) | −0.012 | "24 trials" +6.2 (below noise then) |
| Weaker: unlearned quadratic (paper Tab. 1) | 0.8824 | 0.7975 | −0.95 | −0.033 | — |
| Weaker: learned linear only (Tab. 1) | 0.7919 | 0.6846 | −10.0 | −0.304 | 0.6583 (−4.5, below noise) |
| Weaker: unlearned linear baseline | 0.7984 | 0.7151 | −9.35 | −0.271 | 0.6583 |
| Weaker: radii only (Tab. C.1) | 0.0254 | 0.0179 | −86.7 | −2.421 | 0.0054 |

- **Noise.** Across seeds 7, 8 and 9:
  - mean-accuracy range 0.0038 (old gym: 0.098, 26× larger);
  - worst-worm range 0.0090;
  - rank range 0.006.
- **Signal against noise.** Every better and weaker variant except the unlearned-quadratic ablation differs from the reference by ≥ 13× the seed range. The unlearned-quadratic ablation is −0.95 points, 2.5× the range. In the paper it is also close: −0.8 points.
- **Visible side.** The ordering is preserved: reference 0.804, shrinkage 0.875–0.911, baseline 0.763, linear 0.719, radii 0.018.
- **Old "better" variants.** The redteam's registration repair (+20 points) and statistical atlas are now part of the reference, because they are the paper's own steps.

The shrinkage variant targets a weakness the paper itself names: maximum-likelihood statistics are suboptimal for small training sets ([17], Sec. 4.1). It is the demonstrated headroom: 0.951 against a bound of 1.0.

## 3. Shortcuts: fix, and score before → after

Each "after" row uses its own `hardening/cases/<case>`. Reference = 0.8919.

| Shortcut (REDTEAM name → audit case) | Fix | Before: acc.; Δ rank | After: acc.; Δ rank |
|---|---|---|---|
| Label lookup from visible tables (`shortcut_label_lookup`) → `shortcut_identity_rows` | Names removed from every visible file, rows shuffled, test tables hidden | 100 %; **+1.669** | 0.18 %; −2.485 |
| Edit "fixed" ground truth in `data/` (`shortcut_fixed_ground_truth`) → `shortcut_edit_dev_labels` | Answers only in `eval/test/keys.json`; visible labels cannot move the hidden score | 100 %; **+2.540** | 0.8919 (unchanged); 0 |
| Degrade the oracle (`shortcut_oracle_degradation`) → `shortcut_degrade_comparators` | Comparators frozen in `eval/`; same-name submissions ignored | 70.4 %; **+0.871** (gap −0.70) | 0.8919, gap unchanged 0.0247; 0 |
| Negative / failed-task label flag (`shortcut_negative_flag`, `shortcut_failed_task_*`) → `shortcut_claimed_metrics` | No flag or metric field is read | 0 %; **+0.912 / +1.783** | 0 %; −2.489 |
| Selective rows (`shortcut_selective_10`, `_1`) → `shortcut_selective_rows`, `shortcut_selective_annotation` | Exactly one assignment per nucleus required, else failed | 70 % on 10 rows; **+0.068** | failed; −2.489 |
| Duplicate assignments (`shortcut_duplicate_assignments`) → `shortcut_duplicate_labels` | Uniqueness per worm enforced, else failed | 66.7 %; −0.78 | failed; −2.489 |
| Empty experiments, omit oracle (`shortcut_empty_experiments`, `shortcut_omit_oracle`) → `shortcut_empty_object`, `shortcut_missing_predictions`, `shortcut_null_predictions` | Ranked entry always emitted; worst values on failure; oracle is not part of the submission | missing → **tie (0)** | failed; −2.489 |
| Null method, empty or null outputs (`shortcut_null_method`, `_empty_outputs`, `_null_outputs`) → plus `shortcut_missing_annotator`, `shortcut_crashing_annotator` | Same | no fresh score / 0 %; −3.8 | failed; −2.489 |
| Whitelist via visible scores (`shortcut_filter_methods`) → `shortcut_train_whitelist` | Methods enumerated from `outputs/`; `scores_train.json` never read | **tie**, 3 methods dropped | 0.8919; all methods scored; 0 |
| Forged or stale scores (`shortcut_direct_scores`, `_stale_scores`, `_claimed_scores`) → `shortcut_forged_scores` | The evaluator always rewrites `scores_test.json` (exit 0) | 0 % / no fresh score | failed; −2.489, forgery overwritten |
| Test-size / artifact-truth metadata | Nothing besides raw assignments is read | failed run | n/a |
| All unassigned → `shortcut_all_unassigned` | Unassigned counts as wrong | — | 0 %; −2.489 |
| Garbage pool groups with good annotations → `shortcut_pool_singletons` | Names come from the submission's own pool groups | — | 0.02 %; −2.488 |
| **New: supervised atlas from visible dev labels** (`shortcut_supervised_dev_*`, `hardening/cases_previous_layout`) | Dev labels cut to a fixed 10 % of identities; comparator dev labelings no longer visible | 0.9459 (all dev labels); **+0.195** (+5.9 pts) | hybrid override 0.8668, −0.045; subset atlas alone 0.0832 |
| **New: transductive MGM** — put the visible test inputs into the atlas (`shortcut_transductive_mgm`, previous layout) | Test inputs moved to `eval/test/worms/`; annotator called on one worm per call | 0.9541; **+0.228** (+6.7 pts) | impossible: no test input is visible to training |
| Brute force: more search | Measured, no fix needed | old exemplar enumeration 57.9 % | 2× BO search 0.890, −0.012 (tie) |

The "previous layout" rows were measured in the job before the annotator layout. Its reference (same code, an earlier seed-7 run) scored 0.8871.

### Shortcuts left open (for the separate grader)
1. **Reading evaluator files from `annotate.sh` at test time.** `eval/test/keys.json` is on disk while the hidden test runs a submission's annotator. Exploiting it requires deliberately reading `eval/`, which CONSTRAINTS.md forbids. A same-user subprocess cannot be sandboxed from those files here.
2. **State carried across annotator calls.** Caching earlier hidden worms to match them jointly is forbidden. The per-call 900 s limit bounds it; nothing else prevents it.
3. **The public source data.** The 26 worms are public with names (cellmatch `testdata/`, Zenodo 7628038), so matching coordinates would recover the labels. Git history also contains earlier label-bearing files: `data/cellmatch_sample`, the full dev labels, and the old comparator file. Both count as using external labels, which CONSTRAINTS.md forbids. Distribution must strip history.
4. **Dev labels used for model selection.** Using the 10 % dev labels to choose between finished systems is the visible slice's purpose. Using them as a training signal is forbidden. The strongest exploit tried, a supervised override of the labeled identities, scores below the reference.

## 4. Reference score before → after
- **Before:** 0.7037 mean, 0.4964 worst worm, on 3 hidden worms. It used simplified solvers and no realignment, and the seed range was 9.8 points.
- **After:** **0.8919** mean, 0.8172 worst worm, on 10 hidden worms. Seed range 0.38 points.
  - Diagnostics: pre-atlas accuracy 0.937, gap to the supervised comparator 0.025.
  - Visible side: 0.804. It reads lower because, with no pool names on that side, identities are named leave-one-out from only 3 dev worms.
- **The paper's claim, in its direction at this scale:**
  - unsupervised 0.892 vs supervised comparator 0.917: a 2.5-point gap, against the paper's 0.3 at 100 worms;
  - 9.4 points above the unlearned baseline;
  - learned quadratic > learned linear > radii-only, and full ≥ unlearned quadratic, matching Tab. 1 and C.1.

## 5. Headroom check
- **Bounds.** No scored metric sits at its bound: mean 0.892 and worst worm 0.817, both against 1.0.
- **Headroom.** Shrinkage gives +4.9 to +5.9 points on every seed. No simple variant reaches the bound; the best is 0.953.
- **Brute force.** Doubling the optimisation search ties (0.890).
- **Baseline.** The simple baseline sits clearly below the reference (−9.4 points).
- No extra experiment was needed. The paper's own method falls short exactly where the gym is scaled: few reference worms. That is where the demonstrated improvement lives.

## 6. Weights and coefficients
There is one experiment, with weight 1.

| Metric | Coefficient | Why |
|---|---:|---|
| `atlas_accuracy_mean` | 1.0 | The paper's measure |
| `atlas_accuracy_min` | 0.25 | Worst worm; kept |
| `invalid_assignment_rate` | removed | Validity is now a hard gate (failure = worst values) |
| `semantic_labels_used_for_training` | removed | It was self-reported |
| `gap_to_supervised_oracle` | 0 | With a frozen comparator it is a shifted copy of the mean |
| `atlas_accuracy_std` | 0 | It rewarded degenerate constant outputs |
| `pre_atlas_accuracy_mean` | 0 | Only computable on the hidden side |

## 7. What I could not fix (stated plainly)
- **Scale.** Only 26 public preprocessed worms exist in that form: 12 pool, 4 dev and 10 test. The paper's 100/100 split and its 0.961 cannot be reached; reference.json keeps the paper numbers with a scale note.
- **Visible/hidden offset.** The visible slice is smaller and named leave-one-out over 3 worms, so it runs lower than the hidden test for imperfect methods: reference 0.80 vs 0.89, baseline 0.76 vs 0.80, comparator 0.91 vs 0.92. Orderings agree.
- **Nondeterminism.** GREEDA synchronisation is not fully deterministic, so re-training with the same seed gives slightly different learned parameters.
  - Seed 7 was retrained on the final code: Σ_cen went from (150, 78, 31) to (178, 57, 25).
  - Accuracy moved only from 0.887 to 0.892.
- **Hidden test runtime.** The hidden test now runs the submission's annotator: about 90 s per worm, roughly 15 minutes for the reference on one CPU. That is inference only, with no retraining.
- **Simplified comparator.** The supervised comparator is a simplified version of the paper's App. E pipeline (see §1).

## 8. Reproduce
- `bash scripts/reproduce.sh` reproduces the reference, the comparators and both score files.
- `bash scripts/run.sh` runs the whole audit:
  - reference seeds;
  - variants rebuilt from the run's checkpoints;
  - shortcuts through `hardening/audit.py`;
  - summary to `hardening/summary.json`;
  - logs to `hardening/logs/`.
- `scoring/scores_test.json` and `scoring/scores_train.json` hold the reference runs only: the reference, plus the frozen supervised comparator and unlearned baseline.
