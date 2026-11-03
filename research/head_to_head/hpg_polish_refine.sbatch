#!/bin/bash
#SBATCH --job-name=h2h-refine
#SBATCH --partition=hpg-default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4gb
#SBATCH --time=24:00:00
#SBATCH --output=logs/h2h-refine-%j.out
#SBATCH --error=logs/h2h-refine-%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
base="${BASE_STRATEGY:-research/head_to_head/results/polished-full-action-defense-oracle.json}"
out="${OUTPUT_PATH:-research/head_to_head/results/polished-hpg-refinement.json}"

python3 research/head_to_head/polish_strategy.py "$base" \
  --steps 3 --top-k 50000 --oracle-iterations 1000000 \
  --pure-directions 128 --output "$out"
python3 research/head_to_head/verify_strategy.py "$out" \
  > "${out%.json}.verify.json"
echo "CERTIFICATE ${out%.json}.verify.json"
