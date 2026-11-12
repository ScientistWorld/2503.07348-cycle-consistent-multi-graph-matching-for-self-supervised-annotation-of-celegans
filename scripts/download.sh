#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: 0 GB. Estimated disk usage: <5 MB.
#
# The benchmark's inputs are agent-derived, anonymized nucleus tables that are
# small enough for git and tracked directly:
#   data/worms/pool/*.txt, data/worms/dev/*.txt  (visible)
#   eval/test/worms/*.txt                        (hidden side)
# They were derived (rows shuffled, names removed) from the public preprocessed
# Li et al. (2024) worms of the authors' code release
# (https://github.com/vislearn/cellmatch, commit 91cef19, testdata/), which
# themselves come from https://zenodo.org/records/7628038. That source carries
# every nucleus' name, so this script deliberately does NOT fetch it into the
# workspace: the benchmark is label-free. Solver packages (pylibmgm, optuna,
# numpy, scipy) are installed by environment/setup.sh.
#
# Idempotent: only creates the (empty) downloads directory.
set -e
cd /home/user
mkdir -p data/downloads
for f in data/worms/pool/p00.txt data/worms/dev/d00.txt; do
  [ -f "$f" ] || { echo "missing tracked benchmark file $f (check out the repository)"; exit 1; }
done
echo "benchmark data is tracked in git; nothing to download"
