#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

mkdir -p outputs/method
python -m method.cycle_mgm "$@"
bash scripts/evaluate.sh outputs/method/predictions.json
