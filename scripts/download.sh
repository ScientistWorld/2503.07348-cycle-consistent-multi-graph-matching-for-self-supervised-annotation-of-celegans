#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: 0 GB for the default benchmark data.
# Estimated disk usage after extraction: 2 MB.
#
# The default benchmark data is tracked in git, so this script only creates
# the downloads directory and records the full raw-data source for users who
# want to extend the benchmark beyond the default sample.

set -e

cd /home/user

mkdir -p data/downloads
cat > data/downloads/README.txt <<'EOF'
The default scaled benchmark uses the small preprocessed Li et al. worm sample
tracked in data/cellmatch_sample, copied from the public cellmatch code release.
No external download is required for the default reproduction.

The full public raw image dataset is available from Zenodo:
https://zenodo.org/records/7628038
EOF
