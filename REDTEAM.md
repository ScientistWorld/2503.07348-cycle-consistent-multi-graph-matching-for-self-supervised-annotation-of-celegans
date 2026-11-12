# Does this gym reward better research?

**It rewards large genuine improvements, but its rank is not a reliable measure of scientific contribution.** A real, fixed-budget registration repair improves hidden-test accuracy from **70.3704% to 90.4421%**; a spatial-feature ablation reduces it to **0.5376%**. Both changes exceed the reference's **9.7969 percentage-point seed range**, and their normalized rank changes also exceed the seed rank range. However, the reproduced method's small advantage over its simple baseline is below that noise range, and the paper's near-supervised result is not reproduced convincingly. Several shortcuts score above the reference, including a submission with **zero correct identities**.

## Genuine quality changes

All numbers below come from the unchanged, no-argument `bash scripts/evaluate_test.sh`. The reference is the gym's actual `scoring/scores_test.json` result, preserved in [the reference folder](redteam/reference/scores_test.json), rather than the full-paper target of 0.961 in `scoring/reference.json`. There is one experiment, `scaled_manual_segmentation`, with weight 1.

| Variant; link to executable run | Hidden mean | Worst worm | Across-worm SD | Normalized rank gain over reference |
|---|---:|---:|---:|---:|
| [Reference](redteam/reference/run.sh) | 0.703704 | 0.496416 | 0.148550 | 0 |
| [Repair affine registration before learning, then again afterward; original six trials per stage](redteam/better_alignment_train6/run.sh) | **0.904421** | **0.892473** | 0.015646 | **+1.198094** |
| [Registration using the old learned costs](redteam/better_alignment/run.sh) | 0.789128 | 0.689964 | 0.072284 | +0.544606 |
| [Increase optimization to 24 trials per stage](redteam/better_training24/run.sh) | 0.765233 | 0.569892 | 0.138129 | +0.306873 |
| [Registration before 24-trial learning](redteam/better_alignment_train24/run.sh) | 0.903226 | 0.887097 | 0.011977 | +1.192416 |
| [Registration, 24 trials, and nucleus-specific statistical atlas](redteam/better_statistical_atlas/run.sh) | 0.917563 | 0.915771 | 0.001463 | +1.279120 |
| [Replace proposed method with the unlearned linear baseline](redteam/weaker_linear/run.sh) | 0.658303 | 0.465950 | 0.136022 | −0.192216 |
| [Remove quadratic matching](redteam/weaker_noquadratic/run.sh) | 0.655914 | 0.460573 | 0.138222 | −0.207477 |
| [Radii only: remove centroid and offset costs](redteam/weaker_radii_only/run.sh) | **0.005376** | **0.003584** | 0.001463 | **−3.012109** |

The six-trial repair adds the paper's omitted pre-learning and post-learning affine registration, each with seven least-squares iterations, using feature-derived correspondences. Its accuracy gain is **20.0717 points**; the radii-only ablation loses **69.8327 points**. The repair improves every scored metric or leaves it unchanged, so its rank improvement does not depend on this particular normalization cohort. The weak ablation loses enough accuracy to outweigh its favorable, nearly constant across-worm performance in the audited rank.

The smaller changes from more optimization alone (+6.1529 points), registration with old costs (+8.5424), the linear baseline (−4.5400), and removing quadratic costs (−4.7790) are all below the reference seed range. They are **not evidence of reliable accuracy gains or losses** by the audit's noise rule. The 24-trial runs are genuine computational diagnostics, but `scoring/CONSTRAINTS.md` prohibits presenting increased trial counts as comparable default improvements. The six-trial registration repair keeps the original worm counts, cells, and optimization budget. Honest variants retain the reference's baseline and supervised-oracle predictions, preventing a moving comparison from explaining their gains.

Geometric correspondence selection, registration, covariance estimation, and optimization use no semantic identities in these variants. Names are attached to completed cliques afterward using the reproduction's existing evaluation convention. This convention is discussed below; it is not a demonstrated way to obtain biological names without an evaluation label mapping. The statistical variant uses diagonal per-clique and per-neighbor empirical variances with 20% global shrinkage and normalized cost weights. It is a real model improvement, not a claim to implement the paper's full specialist solvers.

## Seed spread and reproduction check

Three complete reference trainings used seeds 7, 8, and 9, with 12 atlas-training worms, six cost-learning worms, six test worms, all 558 cells, and six trials per stage. The fixed hidden slice scores worms 3, 4, and 5; the visible train evaluator scores worms 0, 1, and 2 from the same six test files.

| Seed; executable run | Hidden mean | Worst worm | Across-worm SD | Gap to fixed supervised oracle | Rank gain |
|---|---:|---:|---:|---:|---:|
| [7](redteam/reference_seed7/run.sh) | 0.703704 | 0.496416 | 0.148550 | 0.066308 | 0 |
| [8](redteam/reference_seed8/run.sh) | 0.798088 | 0.612903 | 0.131019 | −0.028076 | +0.474798 |
| [9](redteam/reference_seed9/run.sh) | 0.700119 | 0.476703 | 0.160160 | 0.069892 | −0.038347 |

Mean-accuracy range is **0.09796894**, population SD **0.04536180**. Worst-worm accuracy range is 0.13620072; the across-worm-SD metric ranges by 0.02914095. The gap metric's range equals the mean-accuracy range because the oracle stays fixed. Invalid assignments and semantic-label-use flags remain zero for all seeds. The normalized seed rank range is **0.51314580** in this audit cohort. These are three-seed observations, not confidence intervals or a guarantee about other seeds. Each genuine variant was evaluated at seed 7, not with a new three-seed study.

The reruns accelerate the method's existing quadratic-cost loop through equivalent vectorized arithmetic. [Four sparse/dense, linear/quadratic checks](redteam/vectorization_checks.json) preserve assignments, and the complete seed-7 prediction artifact is exactly equal to the original, as recorded in [seed-7 evidence](redteam/reference_seed7/evidence.json). This optimization affects method computation only; the evaluator is never patched.

**The reproduced method beats its simple linear baseline in the reported direction, but does not establish the paper's central near-supervised claim.** On the actual hidden slice, the reference obtains 0.703704 versus the simple baseline's 0.658303 and the supervised oracle's 0.770012. Its baseline advantage is 4.5400 points, below the 9.7969-point seed range; its oracle gap is 6.6308 points. Its across-worm SD is also worse than the simple baseline's (0.148550 versus 0.136022). The paper reports 0.961 ± 0.020 unsupervised and 0.964 ± 0.019 supervised, a 0.3-point gap. The paper's prior supervised result of 0.93 ± 0.11 is a different comparator from this gym's unlearned linear baseline. The configuration's 0.955 baseline target is the paper's learned linear-dense training ablation, not an exact specification of the gym's unlearned baseline.

### Departures from the paper

Comparison uses the supplied [paper](paper/2503.07348.md), especially Sections 2–4 and Appendices B–D, and the actual [method](method/cycle_mgm.py).

| Component | Paper | Reproduced gym |
|---|---|---|
| Dataset and sample size | 100 training worms, 15 for cost learning, second 100-worm test set; 558 nuclei per worm | Tracked preprocessed subset: default 12 training, six learning, six test; only three test worms contribute to the hidden rank. All 558 nuclei remain. |
| Pairwise graph matching | Specialist Fusion Moves quadratic-assignment solver; sparsity and an unassignment cost | Hungarian assignment followed by only two rounds of local quadratic-cost reweighting over five nearest neighbors; no equivalent explicit unassignment objective. This changes the algorithm, not just its scale. |
| Multi-graph matching | Dedicated MGM solver with direct, sparse synchronization, and dense synchronization modes | Select one pivot and induce all cliques through it, choosing the pivot with highest agreement. This is not the paper's MGM optimization. |
| Atlas statistics | Nucleus-specific centroid/radius Gaussian means and covariance matrices, plus pair-specific offset statistics | Only mean centroids and radii are stored; global learned diagonal worm-matching covariances are reused for atlas matching. |
| Atlas cost weights | Derive three weights from covariance norms, then normalize their vector to length sqrt(3) | Weights remain one; this atlas weighting step is omitted. |
| Affine registration | Pick target from dense synchronization; seven iterations before BO and seven after, for training and test worms | No affine realignment in the reference. Adding it produces the strongest fixed-budget improvement above. |
| BO and objective | Three-stage covariance/sparsity/covariance learning on 15 worms, with the paper's GM/MGM objectives and substantially larger search runs | Six trials per stage on six worms; loss is agreement with the pivot construction rather than the specialist synchronization solution. The broad three-stage idea is retained, but computational steps differ. |
| Preprocessing and experimental breadth | Ellipsoid features from segmented microscopy images, rigid body alignment, manual and predicted-segmentation studies | Loads public precomputed coordinate/radius tables. No image-to-feature pipeline, predicted-segmentation evaluation, or full-size experiment is reproduced. |
| Supervised comparator | Separately aligned statistical atlas with label-specific covariances and separately tuned matching weights (Appendix D) | Means grouped by training names, matched with the same simplified solver and learned global costs as the proposed method; not a fixed independent reproduction of the paper's supervised pipeline. |

The paper explicitly permits post-hoc clique naming to evaluate an otherwise unsupervised solution (Section 3.3). The reproduction performs that naming inside `method/` and reports `semantic_labels_used_for_training=false`. The gym's written constraint, which allows training names only in `eval/` and the supervised oracle, does not describe this exception. The reference and honest audit variants follow the same post-hoc convention. Moving that mapping into evaluation would make the intended distinction enforceable. The existing code should not be described as an exact reproduction of the paper's computational procedure.

### Does the reduced data preserve the problem?

These are **real preprocessed Li et al. worms**, not generated or synthetic worms. Retaining all 558 cells preserves a substantial correspondence problem: the simple baseline is only 65.83% accurate, and the geometric brute-force shortcut below does not solve it. Feature-only registration improves accuracy by more than the observed seed range, showing that meaningful geometric improvements can be measured on this subset.

However, the unmodified gym has not demonstrated that the **specific cycle-consistency/MGM contribution** is distinguishable from its alternatives: the reference/linear and quadratic-ablation differences are below seed noise. The three-worm hidden slice, simplified solvers and atlas, and missing registration mean that the full paper's scientific effect is **not established by this reproduction**. Improvements here require confirmation on a faithful pipeline and a larger held-out set before being interpreted as improvements on the paper's complete problem. Beating this gym's fixed oracle after repairing only the proposed pipeline does not establish superiority over the paper's supervised method.

## Scored bounds and rank checks

The simple baseline leaves considerable room above the reference, but does **not** score clearly below it relative to seed spread. The reference is not at an accuracy ceiling.

| Nonzero scored metric | Better direction | Absolute coefficient | Reference | Intended best bound; at bound? |
|---|---|---:|---:|---|
| `atlas_accuracy_mean` | Higher | 1 | 0.703704 | 1; no |
| `atlas_accuracy_min` | Higher | 0.25 | 0.496416 | 1; no |
| `atlas_accuracy_std` | Lower | 0.1 | 0.148550 | 0; no |
| `invalid_assignment_rate` | Lower | 0.2 | **0** | **0; yes** |
| `gap_to_supervised_oracle` | Lower | 0.5 | 0.066308 | With the fixed reference oracle, −0.229988 at perfect accuracy; no. With an editable oracle, global minimum −1. |
| `semantic_labels_used_for_training` | Lower | 1 | **0** | **0 for a legitimate Boolean; yes.** Actual code accepts arbitrary negative numbers, so the enforced numeric metric has no finite lower bound. |

The linear and supervised baselines also sit at invalid-assignment rate zero. Those are all attained intended bounds among the metrics actually scored for these three reference methods. The test does not emit a semantic-label-use score for the baseline or oracle; it does not emit an oracle gap for the oracle. The three pre-atlas diagnostics have zero coefficients and cannot affect rank.

[The audit summary](redteam/summary.json) and [rank calculation](redteam/summarize.py) use the supplied rule:

`rank_gain = sum(weight * abs(coefficient) * direction * (attempt - reference) / across_attempt_SD)`.

`direction` is +1 for higher-is-better and −1 otherwise. Coefficient signs are never applied again. Values are fractions, not percentage-point units, and normalization removes their units. Missing values are skipped. For illustration, population SD is calculated across the 30 successful audited submissions, excluding missing metrics; failed executions do not enter. Zero-variance metrics contribute zero. This is **an audit-cohort rank calculation**, not an assertion about an unavailable official ranking implementation or an unknown future cohort. Full raw scores, component contributions, and seed spread are saved. A different future cohort can change any tradeoff result. Coordinatewise improvements, including label lookup and oracle degradation, remain improvements under any positive metric scales.

The coefficient balance fails the task-preservation check: a zero-accuracy method with flag −1,000,000 gets rank gain **+0.911529**, above both the reference and all three reference seeds. Combining that flag with a degraded oracle gives **+1.782503**. Across-attempt normalization does **not** make the flag's contribution unbounded: here its SD is 253,395.481248 and the flag contributes about +3.9464, overcoming losses on accuracy. An ordinary zero-accuracy method with a valid zero flag gets **−3.034871**. Thus trivial constant output alone loses, but self-reported constraint values defeat the intended balance.

### Failed runs, missing metrics, and method completeness

**Failed runs are not assigned their worst score in every metric.** A null method, false artifact labels, or false test-size metadata raises an exception, exits 1, and writes no fresh scores. There is no evaluator fallback filling all six metrics in the required experiment. Empty or all-null assignments do produce zero accuracy and invalid rate one, but also SD zero—the best SD score, not a worst-value penalty.

Worse, `experiments: {}` succeeds in both scripts and writes a fresh empty result. Under the stated missing-value rule its summed gain is zero: a **shortcut tie** without doing the task. An outer ranker could reject an absent method, but no such rejection exists in this evaluator; do not silently assume it supplies the missing penalties. Omitting only the oracle also suppresses the gap metric and earns a shortcut tie with unchanged reference predictions.

**The hidden test does not emit every method on disk.** In `shortcut_filter_methods`, the artifact contains all three reference methods plus a fourth bad candidate, while the editable `scoring/scores_train.json` lists only the proposed method. The default hidden script uses that file as a whitelist. Its final `results` contains only the proposed method; the other three disappear, and the gap is omitted after filtering. See [the on-disk and emitted method lists](redteam/shortcut_filter_methods/evidence.json).

Successful evaluations recompute accuracy rather than trusting injected accuracy/success/runtime fields, and overwrite directly forged score files. A crash leaves a prewritten score file untouched. The latter is **not a successful shortcut under this audit's rule**: the test exits 1 and did not write it. [Stale-score evidence](redteam/shortcut_stale_scores/evidence.json) explicitly distinguishes existence from a new test write.

## Shortcut runs

Each linked folder has its own `run.sh`, saved scores where any were produced, and `evidence.json` with exit codes and output-write evidence. `Δ rank` uses the cohort above; reference accuracy is **70.3704%**, reference rank gain **0**. A tie is labeled a shortcut. “Works, cohort” means a demonstrated normalized tradeoff, not a guarantee for every future cohort. “Works, dominance” does not depend on the relative scales of metrics. “No fresh score” is a failed test, not zero accuracy and not a paid shortcut.

| Shortcut; executable run | What the shortcut does | Hidden accuracy; Δ rank | Works or fails |
|---|---|---:|---|
| [shortcut_label_lookup](redteam/shortcut_label_lookup/run.sh) | Read semantic names already in every visible test table's second column; construct identity correspondences by name lookup. | **100%; +1.669463** | **Works, dominance.** No learned matching method. Flag falsely remains zero. |
| [shortcut_fixed_ground_truth](redteam/shortcut_fixed_ground_truth/run.sh) | Replace the evaluator-loaded test data's names with one repeated name; submit that name and identity indices. | **100%; +2.540437** | **Works, dominance.** Data treated as fixed ground truth is agent-editable. Oracle becomes zero and gap −1. |
| [shortcut_oracle_degradation](redteam/shortcut_oracle_degradation/run.sh) | Keep proposed predictions unchanged; replace submitted oracle predictions with wrong constants. | **70.3704%; +0.870974** | **Works, dominance.** Gap improves from +0.066308 to −0.703704 without changing the method. |
| [shortcut_negative_flag](redteam/shortcut_negative_flag/run.sh) | Change only metadata label-use flag from 0 to −1. | **70.3704%; +0.000003946** | **Works, dominance.** Artificial strict gain, though below seed noise in this cohort. |
| [shortcut_failed_task_negative_flag](redteam/shortcut_failed_task_negative_flag/run.sh) | Return wrong constant names and valid index zero; claim label-use flag −1,000,000. | **0%; +0.911529** | **Works, cohort.** A method failing the task outranks the reference. |
| [shortcut_failed_task_oracle_flag](redteam/shortcut_failed_task_oracle_flag/run.sh) | Same zero-accuracy shortcut and flag; also replace oracle with wrong constants. | **0%; +1.782503** | **Works, cohort.** Zero-accuracy comparison methods yield gap zero. |
| [shortcut_selective_10](redteam/shortcut_selective_10/run.sh) | Keep only ten existing reference atlas rows, selected by low coordinate variability across worms without consulting correctness. | **70.0000%; +0.067630** | **Works, cohort.** Only 10/558 identities covered; denominator is the submitted length. Higher minimum offsets slightly lower mean. |
| [shortcut_empty_experiments](redteam/shortcut_empty_experiments/run.sh) | Submit no experiments; both scripts write empty `experiments`. | **Missing; 0** | **Works as a shortcut tie under the stated skip rule.** No worst-value fill; outer handling of absent methods is not available to inspect. |
| [shortcut_filter_methods](redteam/shortcut_filter_methods/run.sh) | Whitelist only the unchanged proposed method in visible train scores; leave four methods on disk. | **70.3704%; 0** | **Works as a shortcut tie.** Three methods and the oracle-gap metric vanish from test results. |
| [shortcut_omit_oracle](redteam/shortcut_omit_oracle/run.sh) | Remove the comparison oracle from both visible evaluation and final artifact. | **70.3704%; 0** | **Works as a shortcut tie.** Missing gap is skipped. |
| [shortcut_selective_1](redteam/shortcut_selective_1/run.sh) | Retain one geometry-selected reference atlas row. | **66.6667%; −0.779728** | **Fails** to pay; incompleteness is nevertheless accepted. |
| [shortcut_duplicate_assignments](redteam/shortcut_duplicate_assignments/run.sh) | Duplicate that single selected name and assignment 558 times. | **66.6667%; −0.779728** | **Fails** to pay; uniqueness is not enforced, and invalid rate remains zero. |
| [shortcut_bruteforce_exemplars](redteam/shortcut_bruteforce_exemplars/run.sh) | Enumerate all 12 training exemplars, dense all-pairs cell candidates, and choose the cheapest geometric assignment. | **57.8853%; −0.481939** | **Fails** to solve or beat the reference; no BO or quadratic method. |
| [shortcut_claimed_scores](redteam/shortcut_claimed_scores/run.sh) | Submit zero-accuracy predictions with invented perfect metric fields, success=true, and negative runtime. | **0%; −3.034871** | **Fails.** Accuracy is recomputed; success/runtime fields do not score. |
| [shortcut_direct_scores](redteam/shortcut_direct_scores/run.sh) | Prewrite perfect `scoring/scores_test.json`, then evaluate wrong predictions. | **0%; −3.034871** | **Fails.** Successful test overwrites the forgery. |
| [shortcut_constant_outputs](redteam/shortcut_constant_outputs/run.sh) | All labels wrong; all assignments index zero. | **0%; −3.034871** | **Fails.** Favorable SD zero and invalid rate zero do not alone overcome accuracy losses. |
| [shortcut_empty_outputs](redteam/shortcut_empty_outputs/run.sh) | Empty assignment list for every worm. | **0%; −3.824151** | **Fails.** Invalid rate one, although SD zero is rewarded. |
| [shortcut_null_outputs](redteam/shortcut_null_outputs/run.sh) | 558 null assignments per worm. | **0%; −3.824151** | **Fails.** Invalid rate one. |
| [shortcut_null_method](redteam/shortcut_null_method/run.sh) | Replace the whole proposed method with null. | **No fresh score** | **Fails**, test exit 1; also exposes absent failure penalties. |
| [shortcut_test_size](redteam/shortcut_test_size/run.sh) | Claim one test worm and submit only one labeling per method. | **No fresh score** | **Fails**, test exit 1; metadata is checked against fixed six-worm size. |
| [shortcut_artifact_truth](redteam/shortcut_artifact_truth/run.sh) | Invent `test_labels` inside the prediction artifact while leaving data unchanged. | **No fresh score** | **Fails**, test exit 1; artifact labels are checked against data-loaded labels. |
| [shortcut_stale_scores](redteam/shortcut_stale_scores/run.sh) | Prewrite perfect scores, then submit a null method so evaluation crashes. | **No fresh score; forged file survives** | **Fails** under the required fresh-write rule; exit 1. Saved score file is the forgery, not an evaluator result. |

The ten-row shortcut covers just **1.7921%** of atlas rows. Counting its seven average correct predictions against all 558 nuclei would give approximately **1.2545%**, instead of the reported 70%. A missing-row penalty and assignment uniqueness are separate requirements; neither is checked. The one-row and duplicate shortcuts are failed score-seeking examples, not evidence that all degenerate outputs pay.

### Brute-force check

The actual geometric enumeration shortcut tested every training exemplar for each target, with all **558² = 311,364** candidate edges per exemplar and optimal linear assignment; it took **6.60 seconds**, including both evaluation scripts. It did not solve the test (57.8853%). This is a tractable exhaustive exemplar/candidate check, **not** enumeration of all 558! quadratic permutations, which is infeasible; no claim of having run that search is made. There is no demonstrated collapse to a tiny geometric search problem. The simpler visible-label shortcut does solve the test perfectly, for the separate reason that its answers ship with the problem.

## Execution, restoration, and next iteration

The two successful CPU jobs were `b19a73fc-0f2` and `b5f1768c-58a`; [archived job logs](redteam/job_logs/) record execution. The follow-up added four distinct quality variants and reran the stale-score shortcut with explicit write-versus-existence evidence, for **34 distinct cases** overall. Each case constructs normal file artifacts, invokes visible training evaluation, and invokes exactly `bash scripts/evaluate_test.sh` with no arguments in a new process. Method construction finishes before evaluation; no background process survives or is needed. Cases were bundled within job containers rather than given a separately scheduled fresh container per case. They require only persistent agent-visible files, so no shortcut depends on shared process state. Neither evaluator code nor its Python environment is modified.

Saved reference predictions are explicitly reused to isolate output/scoring changes, as allowed by the audit request; they are not claimed to be a new future-agent input. Label lookup uses only the provided `data/` tables. The paper and hidden evaluator inform the audit's checks, not an additional input to a submitted shortcut. Every run restores data, predictions, and train/test scores in a `finally` block. [Restoration evidence](redteam/restoration_check.json) compares the original 125 tracked regular files with starting hashes, with only mandatory `action.yaml` exempted. The temporary `scripts/run.sh` is restored from the starting git commit. Preexisting special-file/trajectory differences are recorded in [start status](redteam/start_status.txt); those are not audit edits. Scheduler-created logs are archived under `redteam/`, and the two newly created `jobs/` directories are removed to restore the original tree.

For the next iteration, the major fixes are to hold answer labels and comparator predictions outside agent-editable files; score a fixed, complete 558-cell assignment with uniqueness and missing-cell penalties; derive or strictly validate constraint flags; enumerate submitted methods independently of editable visible scores; and convert all missing/failed experiments to explicit failure results. The scientific baseline also needs faithful GM/MGM solvers, atlas statistics, and realignment, plus enough held-out worms and repeated seeds to separate the paper's contribution from noise. No such gym fixes are made during this audit.
