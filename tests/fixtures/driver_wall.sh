#!/bin/bash
# driver with a perl-alarm outer wall and an --inner-seconds bound.
set -uo pipefail
for N in $(seq 1 12); do
  echo "========== CYCLE $N  $(date -u +%H:%M:%SZ) =========="
  perl -e 'alarm shift; exec @ARGV' 10800 python3 run-v2.py \
    --goal "cycle $N" --inner "python3 spoke.py --cycle $N" --inner-seconds 3000 \
    --log cycle.md --trajectories ai/trajectories --project-dir proj --outer-steps 60
  echo "========== CYCLE $N done =========="
done
