#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit weaker_radii_only
