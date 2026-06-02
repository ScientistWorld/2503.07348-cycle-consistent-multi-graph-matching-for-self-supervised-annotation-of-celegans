# Experiment Overview

## scaled_manual_segmentation
This experiment tests the central atlas-annotation task on a tracked public sample of preprocessed C. elegans worms. It measures whether an atlas built from training worms can assign correct biological identities to cells in held-out worms, and whether the unsupervised result remains close to a supervised oracle under the same data and evaluation rules.

The current default reproduction uses `scripts/reproduce.sh` with 12 training worms, 6 held-out worms, 160 cells, and 6 parameter-search trials per learning stage. Smaller diagnostic scripts are retained for future agents that need fast smoke checks before running the default setting.

An expanded probe is available through `scripts/expanded_core.sh` with 16 training worms, 6 held-out worms, and 220 cells. It writes to `outputs/expanded/` rather than `scoring/scores.json`, because the formal default benchmark remains the comparable `scripts/reproduce.sh` setting.
