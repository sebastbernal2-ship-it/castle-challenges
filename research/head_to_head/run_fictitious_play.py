#!/usr/bin/env python3
"""Run full-action Game 1 fictitious play and save a reproducible JSON result."""

import argparse
import json
from pathlib import Path

from castle_challenges.games.head_to_head.fictitious_play import solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("research/head_to_head/results"))
    args = parser.parse_args()
    result = solve(args.rounds, args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    payload = {
        "game": "head_to_head",
        "method": "two-sided full-action fictitious play",
        "rounds": result.rounds,
        "seed": args.seed,
        "initial_actions_per_side": 26,
        "row_support": len(result.row_strategy),
        "column_support": len(result.column_strategy),
        "row_best_deviation_score_against_column_mix": result.row_deviation_score,
        "column_best_deviation_score_against_row_mix": result.column_deviation_score,
        "row_exploitability_above_7_5": result.row_deviation_score - 7.5,
        "column_exploitability_above_7_5": result.column_deviation_score - 7.5,
        "row_best_response": result.row_response,
        "column_best_response": result.column_response,
        "row_strategy": [[a, p] for a, p in sorted(result.row_strategy.items())],
        "column_strategy": [[a, p] for a, p in sorted(result.column_strategy.items())],
        "note": "Approximate finite-iteration result, not an equilibrium certificate.",
    }
    path = args.output / f"fictitious-play-seed-{args.seed}-rounds-{args.rounds}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: v for k, v in payload.items() if "strategy" not in k}, indent=2))
    print(f"Full mixed strategies written to {path}")


if __name__ == "__main__":
    main()
