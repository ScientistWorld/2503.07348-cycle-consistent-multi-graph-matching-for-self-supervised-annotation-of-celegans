#!/bin/bash
# Standard evaluation entry point for development: scores every method under
# outputs/ on the visible dev slice and writes scoring/scores.json (same content
# as scripts/evaluate_train.sh). Evaluation only reads prediction artifacts; it
# never imports method/ code.
#
# Usage (no arguments): bash scripts/evaluate.sh
set -e
cd /home/user
mkdir -p scoring
python eval/train/evaluate_slice.py --output scoring/scores.json
