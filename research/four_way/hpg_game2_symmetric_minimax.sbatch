#!/bin/bash
#SBATCH --job-name=game2-minimax-do
#SBATCH --output=logs/game2-minimax-%j.out
#SBATCH --error=logs/game2-minimax-%j.err
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --mail-type=END,FAIL

set -euo pipefail
cd "$HOME/castle-challenges-hpg"
export PYTHONPATH=src
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

python3 research/four_way/symmetric_minimax_expansion.py \
  research/four_way/results/replicator_runs/diverse-pool25-response7-500k.json \
  --output-dir research/four_way/results/hpg_symmetric_minimax_multistart \
  --state research/four_way/results/hpg_symmetric_minimax_multistart/state.json \
  --resume \
  --max-rounds 30 \
  --restarts 6 \
  --audit-candidates 3 \
  --add-responses-per-round 4 \
  --oracle-top-k 10 \
  --optimizer-iterations 400 \
  --frequency-total 1000000000 \
  --threads 8 \
  --seed 19001
