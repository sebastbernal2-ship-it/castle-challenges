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
import shutil
import subprocess
import tempfile

from castle_challenges.games.head_to_head.best_response import (
    best_response_from_counts, top_responses_from_counts,
)
from castle_challenges.games.head_to_head.rules import score


ALPHAS = (tuple(10.0 ** (power / 4) / 100_000_000
                for power in range(0, 33))
          + (2.5e-7, 5e-7, 7.5e-7, 0.0001, 0.0002, 0.0005, 0.001,
             0.002, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0))


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


def _restricted_defense_mix(deviations: list[tuple[int, ...]], defenses: list[tuple[int, ...]],
                            rounds: int = 5_000) -> list[float]:
    """Approximate minimax defense over a small response/deviation matrix."""
    compiler = shutil.which("c++")
    if compiler:
        source = Path(__file__).with_name("restricted_matrix_fictitious_play.cpp")
        with tempfile.TemporaryDirectory(prefix="castle-h2h-matrix-") as tmp:
            binary = Path(tmp) / "matrix_fp"
            subprocess.run([compiler, "-O3", "-std=c++17", str(source), "-o", str(binary)],
                           check=True, stdout=subprocess.DEVNULL)
            payload = f"{len(deviations)} {len(defenses)} {rounds}\n"
            payload += "".join(" ".join(map(str, a)) + "\n" for a in deviations)
            payload += "".join(" ".join(map(str, a)) + "\n" for a in defenses)
            output = subprocess.run([str(binary)], input=payload, text=True,
                                    capture_output=True, check=True).stdout.split()
        return [float(x) for x in output[1:]]

    matrix = [[score(b, c) for c in defenses] for b in deviations]
    row_counts = [0] * len(deviations)
    col_counts = [0] * len(defenses)
    for _ in range(rounds):
        row = max(range(len(deviations)),
                  key=lambda i: sum(col_counts[j] * matrix[i][j]
                                   for j in range(len(defenses)))
                  )
        col = min(range(len(defenses)),
                  key=lambda j: sum(row_counts[i] * matrix[i][j]
                                   for i in range(len(deviations)))
                  )
        row_counts[row] += 1
        col_counts[col] += 1
    return [count / rounds for count in col_counts]


def _defense_oracle_mix(deviations: list[tuple[int, ...]], rounds: int
                        ) -> tuple[list[tuple[int, ...]], list[float], float | None]:
    """Solve the restricted attacker/full-action defender game by fictitious play."""
    compiler = shutil.which("c++")
    if compiler:
        source = Path(__file__).with_name("restricted_defense_oracle_fictitious_play.cpp")
        with tempfile.TemporaryDirectory(prefix="castle-h2h-defense-oracle-") as tmp:
            binary = Path(tmp) / "defense_oracle"
            subprocess.run([compiler, "-O3", "-std=c++17", str(source), "-o", str(binary)],
                           check=True, stdout=subprocess.DEVNULL)
            payload = f"{len(deviations)} {rounds}\n"
            payload += "".join(" ".join(map(str, a)) + "\n" for a in deviations)
            lines = subprocess.run([str(binary)], input=payload, text=True,
                                   capture_output=True, check=True).stdout.splitlines()
        upper, lower, _ = map(float, lines[0].split())
        defenses = []
        counts = []
        for line in lines[1:]:
            fields = list(map(int, line.split()))
            defenses.append(tuple(fields[:5]))
            counts.append(fields[5])
        total = sum(counts)
        return defenses, [count / total for count in counts], upper - lower

    directions = []
    for deviation in deviations:
        pure_hist = [[0] * 101 for _ in range(5)]
        for i, soldiers in enumerate(deviation):
            pure_hist[i][soldiers] = 1
        defense, _, _ = best_response_from_counts(tuple(pure_hist))
        if defense not in directions:
            directions.append(defense)
    probabilities = _restricted_defense_mix(deviations, directions, rounds)
    return directions, probabilities, None


def polish(source: Path, steps: int = 20, top_k: int = 10,
           matrix_rounds: int = 5_000, pure_directions: int = 64) -> dict:
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
        deviations = top_responses_from_counts(tuple(current_hist), k=top_k)
        directions, defense_probabilities, defense_game_gap = _defense_oracle_mix(
            [a for a, _ in deviations], matrix_rounds)
        ranked_directions = sorted(zip(directions, defense_probabilities),
                                   key=lambda item: item[1], reverse=True)
        direction_mixtures = [({a: 1.0}, [a]) for a, p in
                              ranked_directions[:pure_directions] if p > 0]
        direction_mixtures.append((dict(zip(directions, defense_probabilities)), directions))

        best_gap = trace[-1]["gap"]
        best_strategy = None
        best_hist = None
        best_alpha = None
        for direction_weights, direction_actions in direction_mixtures:
            for alpha in ALPHAS:
                candidate_weights = {
                    action: (1 - alpha) * mass for action, mass in strategy.items()
                }
                for action, probability in direction_weights.items():
                    candidate_weights[action] = candidate_weights.get(action, 0.0) + alpha * total * probability
                quantized = _quantize(candidate_weights, total)
                hist = _histogram(quantized)
                response, numerator, denominator = best_response_from_counts(tuple(hist))
                gap = numerator / denominator - 7.5
                if gap < best_gap - 1e-14:
                    best_gap = gap
                    best_strategy = quantized
                    best_hist = hist
                    best_response_action = response
                    best_direction_weights = direction_weights
                    best_alpha = alpha
        if best_strategy is None:
            break
        strategy, current_hist = best_strategy, best_hist
        mixture_support = [(action, probability)
                           for action, probability in best_direction_weights.items()
                           if probability > 0]
        mixture_top = sorted(mixture_support, key=lambda item: item[1], reverse=True)[:10]
        trace.append({"step": step, "gap": best_gap, "step_size": best_alpha,
                      "restricted_defense_game_gap": defense_game_gap,
                      "best_response": list(best_response_action),
                      "descent_mixture_support": len(mixture_support),
                      "descent_mixture_top": [[list(action), probability]
                                               for action, probability in mixture_top]})

    _, numerator, denominator = best_response_from_counts(tuple(current_hist))
    payload = {
        "source": str(source),
        "method": "restricted-attacker/full-action-defender fictitious play + exact full-action line search",
        "frequency_total": total,
        "top_deviations_considered": top_k,
        "restricted_defense_oracle_iterations": matrix_rounds,
        "pure_direction_candidates": pure_directions,
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
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--matrix-rounds", "--oracle-iterations", dest="matrix_rounds",
                        type=int, default=5_000)
    parser.add_argument("--pure-directions", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = polish(args.strategy, args.steps, args.top_k, args.matrix_rounds,
                    args.pure_directions)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "strategy"}, indent=2))


if __name__ == "__main__":
    main()
