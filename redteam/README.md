This is a benchmark scoring audit. `bash redteam/run_all.sh` runs the entire
bundle inside the existing gym container. Every individual case has its own
`run.sh`, which constructs a submission, invokes the visible evaluation,
invokes `bash scripts/evaluate_test.sh` with no arguments, saves scores and
exit evidence, and restores predictions, scores, and data in a `finally` block.
No evaluator or Python environment changes are used. Each evaluator invocation
starts a new interpreter; no running method process is needed at test time.

`reference/predictions.json` is the already-trained reproduction output reused
with the audit's explicit permission. It is not an assumed future-agent input;
quality reruns reconstruct it, and answer-lookup shortcuts use visible `data/`.
The other shortcuts reuse it to isolate scoring changes and save computation.

All shared shortcut implementations are in `shortcuts.py`; all genuine
variants are in `quality_methods.py`. Case names select an implementation, not
a score. Generated case predictions and logs are ignored; scores and run
evidence are retained. `summary.json` uses the metric directions and absolute
coefficients in `scoring/reference.json` and normalizes over the successful
audit cohort. Future attempts change that normalization; coordinatewise
dominance findings do not depend on it.

The completed audit used two CPU jobs, `b19a73fc-0f2` and `b5f1768c-58a`.
`run_all.sh` now includes all 34 distinct cases; `run_followup.sh` is the
five-case second-job bundle. The second job repeats the stale-score shortcut
to distinguish a surviving file from a score actually written by the test.
Full conclusions, seed spread, and the shortcut table are in `../REDTEAM.md`.
The job logs are archived under `job_logs/`.

Run these scripts as compute jobs in the gym container, not on a login node.
Cases share that container but construct artifacts before starting the
unchanged test script in its own process. There is no background process,
import patch, or evaluator state required to reproduce a shortcut.
