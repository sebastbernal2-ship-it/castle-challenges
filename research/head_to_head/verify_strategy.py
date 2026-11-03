#!/usr/bin/env python3
"""Recompute a saved Game 1 strategy's full-action exact deviation certificate."""

import argparse
import json
from pathlib import Path

from castle_challenges.games.head_to_head.best_response import best_response_from_counts


def verify(path: Path) -> dict:
    data = json.loads(path.read_text())
    if "row_strategy" in data:
        total = data["rounds"] + data["initial_actions_per_side"]
        entries = data["row_strategy"]
    else:
        total = data["frequency_total"]
        entries = data["strategy"]
    counts = [[0] * 101 for _ in range(5)]
    for allocation, probability in entries:
        mass = round(probability * total)
        for castle, soldiers in enumerate(allocation):
            counts[castle][soldiers] += mass
    totals = [sum(row) for row in counts]
    if any(value != total for value in totals):
        raise ValueError(f"reconstructed marginal masses {totals} != {total}")
    action, numerator, denominator = best_response_from_counts(tuple(counts))
    gap_num = numerator - 15 * denominator // 2
    saved = data.get("final_gap_fraction")
    if saved is None:
        saved = data.get("row_exploitability_fraction")
    if saved is not None and [gap_num, denominator] != saved:
        raise ValueError(f"stored certificate {saved} does not match recomputed {[gap_num, denominator]}")
    return {
        "strategy_file": str(path),
        "frequency_total": total,
        "support_size": len(entries),
        "best_response": list(action),
        "best_response_score_fraction": [numerator, denominator],
        "exploitability_fraction": [gap_num, denominator],
        "exploitability": gap_num / denominator,
        "verified_full_action_space": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.strategy), indent=2))


if __name__ == "__main__":
    main()
