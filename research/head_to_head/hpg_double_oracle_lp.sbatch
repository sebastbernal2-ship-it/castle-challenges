#!/bin/bash
#SBATCH --job-name=h2h-lp-oracle
#SBATCH --partition=hpg-default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16gb
#SBATCH --time=24:00:00
#SBATCH --output=logs/lp-oracle-%j.out
#SBATCH --error=logs/lp-oracle-%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PYTHONPATH="$HOME/mathopt:$HOME/lib/python3.12/site-packages:src${PYTHONPATH:+:${PYTHONPATH}}"

base="${BASE_STRATEGY:-research/head_to_head/results/lp-baseline.json}"
out="research/head_to_head/results/double-oracle-lp.json"
seed_size="${LP_SEED_SIZE:-256}"
response_batch="${LP_RESPONSE_BATCH:-200}"
iterations="${LP_MAX_ITERATIONS:-20}"
resume_state="${LP_RESUME_STATE:-}"
resume_args=()
if [[ -n "$resume_state" ]]; then
  resume_args=(--resume-state "$resume_state")
fi

python3 research/head_to_head/double_oracle_lp.py "$base" \
  --seed-size "$seed_size" --response-batch "$response_batch" \
  --max-iterations "$iterations" --tolerance 1e-7 \
  "${resume_args[@]}" --output "$out"
python3 research/head_to_head/verify_strategy.py "$out" \
  > "${out%.json}.verify.json"
echo "CERTIFICATE ${out%.json}.verify.json"
