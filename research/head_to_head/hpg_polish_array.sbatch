#!/bin/bash
#SBATCH --job-name=h2h-polish
#SBATCH --partition=hpg-default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4gb
#SBATCH --time=24:00:00
#SBATCH --array=0-7%8
#SBATCH --output=logs/h2h-%A_%a.out
#SBATCH --error=logs/h2h-%A_%a.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"

case "${SLURM_ARRAY_TASK_ID}" in
  0) top_k=50000;  rounds=1000000;  pure=128; steps=3 ;;
  1) top_k=50000;  rounds=3000000;  pure=128; steps=1 ;;
  2) top_k=100000; rounds=1000000;  pure=128; steps=1 ;;
  3) top_k=100000; rounds=2000000;  pure=128; steps=1 ;;
  4) top_k=20000;  rounds=3000000;  pure=512; steps=1 ;;
  5) top_k=50000;  rounds=1000000;  pure=512; steps=1 ;;
  6) top_k=50000;  rounds=2000000;  pure=512; steps=1 ;;
  7) top_k=10000;  rounds=5000000;  pure=512; steps=1 ;;
  *) echo "Invalid array index: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

base="${BASE_STRATEGY:-research/head_to_head/results/polished-full-action-defense-oracle.json}"
out="research/head_to_head/results/hpg_sweep/candidate-${SLURM_ARRAY_TASK_ID}.json"

export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
python3 research/head_to_head/polish_strategy.py "$base" \
  --steps "$steps" --top-k "$top_k" --oracle-iterations "$rounds" \
  --pure-directions "$pure" --output "$out"
python3 research/head_to_head/verify_strategy.py "$out" > "${out%.json}.verify.json"
echo "CERTIFICATE ${out%.json}.verify.json"
