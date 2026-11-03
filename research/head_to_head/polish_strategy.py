#!/usr/bin/env python3
"""Frank-Wolfe-style exploitability polishing for a saved Game 1 mixture.

Each proposal follows the exact subgradient induced by the current worst
opponent response. A grid line search is followed by integer-frequency
quantization and an exact integer-DP certificate. This is an experiment, not a
convergence guarantee for the non-smooth objective.
"""

import argparse
import json
from pathlib import Path

from castle_challenges.games.head_to_head.best_response import (
    best_response_from_counts,
)


ALPHAS = (tuple(10.0 ** (power / 4) / 1_000_000
                for power in range(0, 17))
          + (0.0001, 0.0002, 0.0005, 0.001, 0.002))


def _histogram(weights: dict[tuple[int, ...], int]) -> list[list[int]]:
    hist = [[0] * 101 for _ in range(5)]
    for action, mass in weights.items():
        for i, soldiers in enumerate(action):
            hist[i][soldiers] += mass
    return hist


def _quantize(weights: dict[tuple[int, ...], float], total: int) -> dict[tuple[int, ...], int]:
    scale = total / sum(weights.values())
    weights = {action: value * scale for action, value in weights.items()}
    floors = {a: int(value) for a, value in weights.items() if value > 0}
    residual = total - sum(floors.values())
    order = sorted(weights, key=lambda a: weights[a] - int(weights[a]), reverse=True)
    for action in order[:residual]:
        floors[action] = floors.get(action, 0) + 1
    return {a: n for a, n in floors.items() if n > 0}


def polish(source: Path, steps: int = 20) -> dict:
    data = json.loads(source.read_text())
    if "row_strategy" in data:
        total = data["rounds"] + data["initial_actions_per_side"]
        entries = data["row_strategy"]
    else:
        total = data["frequency_total"]
        entries = data["strategy"]
    strategy = {tuple(action): round(probability * total) for action, probability in entries}
    current_hist = _histogram(strategy)
    initial_br, initial_num, initial_den = best_response_from_counts(
        tuple(current_hist))
    trace = [{"step": 0, "gap": initial_num / initial_den - 7.5,
              "best_response": list(initial_br)}]

    for step in range(1, steps + 1):
        br, _, _ = best_response_from_counts(tuple(current_hist))
        pure_hist = [[0] * 101 for _ in range(5)]
        for i, soldiers in enumerate(br):
            pure_hist[i][soldiers] = 1
        descent, _, _ = best_response_from_counts(tuple(pure_hist))

        best_gap = trace[-1]["gap"]
        best_strategy = None
        best_hist = None
        for alpha in ALPHAS:
            candidate_weights = {
                action: (1 - alpha) * mass for action, mass in strategy.items()
            }
            candidate_weights[descent] = candidate_weights.get(descent, 0.0) + alpha * total
            quantized = _quantize(candidate_weights, total)
            hist = _histogram(quantized)
            response, numerator, denominator = best_response_from_counts(tuple(hist))
            gap = numerator / denominator - 7.5
            if gap < best_gap - 1e-14:
                best_gap = gap
                best_strategy = quantized
                best_hist = hist
                best_response_action = response
        if best_strategy is None:
            break
        strategy, current_hist = best_strategy, best_hist
        trace.append({"step": step, "gap": best_gap,
                      "best_response": list(best_response_action),
                      "descent_action": list(descent)})

    _, numerator, denominator = best_response_from_counts(tuple(current_hist))
    payload = {
        "source": str(source),
        "method": "best-response subgradient direction + grid line search",
        "frequency_total": total,
        "trace": trace,
        "final_gap_fraction": [numerator - 15 * denominator // 2, denominator],
        "final_best_response_score_fraction": [numerator, denominator],
        "strategy": [[list(a), n / total] for a, n in sorted(strategy.items())],
        "warning": "Heuristic polishing; only final exact integer-DP gap is certified.",
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", type=Path)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = polish(args.strategy, args.steps)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "strategy"}, indent=2))


if __name__ == "__main__":
    main()
