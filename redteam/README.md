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
