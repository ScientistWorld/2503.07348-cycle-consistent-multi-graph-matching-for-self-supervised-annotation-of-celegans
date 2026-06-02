# Experiment Overview

## scaled_manual_segmentation
This experiment tests the central identity-assignment task on a tracked public sample of preprocessed C. elegans worms. It measures whether a reference built from training worms can assign correct biological identities to cells in held-out worms, and whether a label-free result remains close to a supervised oracle under the same data and evaluation rules.

The current default benchmark uses 12 training worms, 6 held-out worms, and all 558 cells in each worm. Smaller diagnostic scripts are retained for future agents that need fast smoke checks before running the default setting; those positive `--cells` settings are label-free input-order subsets and should not be reported as the formal default benchmark.

An expanded probe is available through `scripts/expanded_core.sh` with 16 training worms, 6 held-out worms, and 220 cells. It writes to `outputs/expanded/` rather than `scoring/scores.json`, because the formal default benchmark remains the comparable `scripts/reproduce.sh` setting.
