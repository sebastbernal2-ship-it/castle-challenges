#!/usr/bin/env python3
"""Restricted-game LP double oracle for two-player constant-sum Game 1.

Each restricted row/column action is allowed to be a mixed strategy. The
baseline strategy is included as a meta-action, preserving its incumbent
certificate while exact DP separation adds pure best responses. The final
symmetric average is independently auditable with verify_strategy.py.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path
from typing import Any

from castle_challenges.common.allocation import Allocation, VALUES
from castle_challenges.games.head_to_head.best_response import (
    best_response_from_counts,
    top_responses_from_counts,
)

FREQUENCY_TOTAL = 1_000_000_000


def _quantize(actions: list[Allocation], probabilities: list[float], total: int
              ) -> dict[Allocation, int]:
    mass = sum(probabilities)
    if mass <= 0:
        raise ValueError("strategy has no positive probability")
    scaled = [max(0.0, p) * total / mass for p in probabilities]
    floors = [int(x) for x in scaled]
    residual = total - sum(floors)
    order = sorted(range(len(actions)), key=lambda i: scaled[i] - floors[i], reverse=True)
    for i in order[:residual]:
        floors[i] += 1
    return {a: n for a, n in zip(actions, floors) if n}


def _histogram(strategy: dict[Allocation, int]) -> tuple[list[int], ...]:
    hist = [[0] * 101 for _ in range(5)]
    for action, count in strategy.items():
        for castle, soldiers in enumerate(action):
            hist[castle][soldiers] += count
    return tuple(hist)


def _strategy_marginals(strategy: dict[Allocation, int]):
    import numpy as np

    total = sum(strategy.values())
    marginal = np.zeros((5, 101), dtype=np.float64)
    for action, count in strategy.items():
        for castle, soldiers in enumerate(action):
            marginal[castle, soldiers] += count / total
    return marginal


def _payoff_matrix(rows: list[dict[Allocation, int]],
                   cols: list[dict[Allocation, int]]):
    """Pairwise score matrix for mixed-strategy meta-actions, in half-points."""
    import numpy as np

    row_marginals = [_strategy_marginals(s) for s in rows]
    col_marginals = [_strategy_marginals(s) for s in cols]
    row_array = np.stack(row_marginals)
    col_array = np.stack(col_marginals)
    matrix = np.zeros((len(rows), len(cols)), dtype=np.float64)
    for castle, value in enumerate(VALUES):
        col_below = np.cumsum(col_array[:, castle, :], axis=1) - col_array[:, castle, :]
        wins = row_array[:, castle, :] @ col_below.T
        ties = row_array[:, castle, :] @ col_array[:, castle, :].T
        matrix += value * (2 * wins + ties)
    return matrix


def _restricted_equilibrium(matrix):
    """Solve both primal and dual restricted matrix-game LPs using HiGHS."""
    import numpy as np
    from scipy.optimize import linprog

    row_count, col_count = matrix.shape
    row_lp = linprog(
        np.r_[np.zeros(row_count), -1.0],
        A_ub=np.column_stack((-matrix.T, np.ones(col_count))),
        b_ub=np.zeros(col_count),
        A_eq=np.r_[np.ones(row_count), 0.0][None, :],
        b_eq=[1.0],
        bounds=[(0.0, None)] * row_count + [(None, None)],
        method="highs",
        options={"dual_feasibility_tolerance": 1e-9,
                 "primal_feasibility_tolerance": 1e-9},
    )
    col_lp = linprog(
        np.r_[np.zeros(col_count), 1.0],
        A_ub=np.column_stack((matrix, -np.ones(row_count))),
        b_ub=np.zeros(row_count),
        A_eq=np.r_[np.ones(col_count), 0.0][None, :],
        b_eq=[1.0],
        bounds=[(0.0, None)] * col_count + [(None, None)],
        method="highs",
        options={"dual_feasibility_tolerance": 1e-9,
                 "primal_feasibility_tolerance": 1e-9},
    )
    if not row_lp.success or not col_lp.success:
        raise RuntimeError(f"restricted LP failed: row={row_lp.message}; col={col_lp.message}")
    return row_lp.x[:-1], col_lp.x[:-1], float(row_lp.x[-1]), float(col_lp.x[-1])


def _mix_pool(pool: list[dict[Allocation, int]], probabilities: list[float]
              ) -> dict[Allocation, int]:
    mass: dict[Allocation, float] = defaultdict(float)
    for strategy, probability in zip(pool, probabilities):
        if probability <= 0:
            continue
        total = sum(strategy.values())
        for action, count in strategy.items():
            mass[action] += probability * count / total
    return _quantize(list(mass), list(mass.values()), FREQUENCY_TOTAL)


def _pure_strategy(action: Allocation) -> dict[Allocation, int]:
    return {action: FREQUENCY_TOTAL}


def _strategy_entries(counts: dict[Allocation, int], total: int
                       ) -> list[list[Any]]:
    return [[list(action), count / total] for action, count in sorted(counts.items())]


def _average_counts(row: dict[Allocation, int], col: dict[Allocation, int]
                    ) -> dict[Allocation, int]:
    average = dict(row)
    for action, count in col.items():
        average[action] = average.get(action, 0) + count
    return average


def _candidate_payload(source: Path, row: dict[Allocation, int],
                       col: dict[Allocation, int], history: list[dict[str, Any]
                       ]) -> tuple[Fraction, dict[str, Any]]:
    average = _average_counts(row, col)
    total = 2 * FREQUENCY_TOTAL
    action, score_num, denominator = best_response_from_counts(_histogram(average))
    gap_num = score_num - 15 * denominator // 2
    gap = Fraction(gap_num, denominator)
    payload = {
        "source": str(source),
        "method": "restricted zero-sum LP double oracle with exact full-action DP separation",
        "frequency_total": total,
        "lp_frequency_total_per_side": FREQUENCY_TOTAL,
        "lp_row_strategy": _strategy_entries(row, FREQUENCY_TOTAL),
        "lp_column_strategy": _strategy_entries(col, FREQUENCY_TOTAL),
        "final_best_response_score_fraction": [score_num, denominator],
        "final_gap_fraction": [gap_num, denominator],
        "best_response": list(action),
        "strategy": _strategy_entries(average, total),
        "iterations": history.copy(),
        "warning": "Restricted LPs generate candidates; only the saved symmetric mixture's exact DP gap is a full-action certificate.",
    }
    return gap, payload


def _incumbent_payload(source: Path, data: dict[str, Any]
                       ) -> tuple[Fraction, dict[str, Any]]:
    total = data["frequency_total"]
    counts: dict[Allocation, int] = {
        tuple(action): round(probability * total)
        for action, probability in data["strategy"]
    }
    hist = _histogram(counts)
    action, score_num, denominator = best_response_from_counts(hist)
    gap_num = score_num - 15 * denominator // 2
    gap = Fraction(gap_num, denominator)
    payload = {
        "source": str(source),
        "method": "unchanged incumbent preserved by LP double-oracle search",
        "frequency_total": total,
        "final_best_response_score_fraction": [score_num, denominator],
        "final_gap_fraction": [gap_num, denominator],
        "best_response": list(action),
        "strategy": _strategy_entries(counts, total),
        "iterations": [],
    }
    return gap, payload


def solve(source: Path, *, seed_size: int = 256, response_batch: int = 20,
          max_iterations: int = 50, tolerance: float = 1e-7,
          checkpoint: Path | None = None, resume_state: Path | None = None
          ) -> dict[str, Any]:
    if seed_size < 1 or response_batch < 1 or max_iterations < 1:
        raise ValueError("seed size, response batch, and iteration count must be positive")
    data = json.loads(source.read_text())
    initial = _quantize(
        [tuple(action) for action, _ in data["strategy"]],
        [float(probability) for _, probability in data["strategy"]],
        FREQUENCY_TOTAL,
    )
    initial_hist = _histogram(initial)

    # Keep the incumbent mixture in both restricted strategy pools. Pool
    # members may be mixed strategies; their convex combinations remain valid.
    rows = [initial]
    cols = [initial]
    row_actions = [a for a, _ in top_responses_from_counts(initial_hist, seed_size)]
    col_actions = sorted(initial, key=initial.get, reverse=True)[:seed_size]
    for row in row_actions:
        pure_hist = [[0] * 101 for _ in range(5)]
        for i, soldiers in enumerate(row):
            pure_hist[i][soldiers] = 1
        defense, _, _ = best_response_from_counts(tuple(pure_hist))
        col_actions.append(defense)
    row_actions = list(dict.fromkeys(row_actions))
    col_actions = list(dict.fromkeys(col_actions))
    if resume_state is not None:
        state = json.loads(resume_state.read_text())["double_oracle_state"]
        row_actions = [tuple(a) for a in state["row_pure_actions"]]
        col_actions = [tuple(a) for a in state["column_pure_actions"]]
    rows.extend(_pure_strategy(a) for a in row_actions
                if not (len(initial) == 1 and a in initial))
    cols.extend(_pure_strategy(a) for a in col_actions
                if not (len(initial) == 1 and a in initial))
    row_pure_set, col_pure_set = set(row_actions), set(col_actions)

    # The incumbent itself is always retained as a candidate, even if the
    # restricted LP's current equilibrium is worse against omitted actions.
    history: list[dict[str, Any]] = []
    best = _incumbent_payload(source, data)

    for iteration in range(max_iterations):
        matrix = _payoff_matrix(rows, cols)
        row_probs, col_probs, restricted_lower, restricted_upper = _restricted_equilibrium(matrix)
        row_counts = _mix_pool(rows, row_probs.tolist())
        col_counts = _mix_pool(cols, col_probs.tolist())

        row_hist = _histogram(row_counts)
        col_hist = _histogram(col_counts)
        row_br, row_num, denominator = best_response_from_counts(col_hist)
        col_br, col_num, _ = best_response_from_counts(row_hist)
        pair_gap_num = row_num + col_num - 15 * denominator
        pair_gap = Fraction(pair_gap_num, denominator)

        candidate_gap, candidate = _candidate_payload(source, row_counts, col_counts, history)
        if candidate_gap < best[0]:
            best = candidate_gap, candidate

        entry = {
            "iteration": iteration,
            "row_pool_size": len(rows),
            "column_pool_size": len(cols),
            "restricted_value_half_points": restricted_lower,
            "restricted_primal_dual_gap_half_points": restricted_upper - restricted_lower,
            "full_pair_gap_fraction": [pair_gap.numerator, pair_gap.denominator],
            "full_pair_gap": float(pair_gap),
            "average_full_action_gap_fraction": [candidate["final_gap_fraction"][0],
                                                 candidate["final_gap_fraction"][1]],
            "average_full_action_gap": float(candidate_gap),
            "row_best_response": list(row_br),
            "column_best_response": list(col_br),
            "average_best_response": candidate["best_response"],
        }
        should_stop = candidate_gap <= tolerance or pair_gap <= tolerance
        if not should_stop:
            row_set, col_set = row_pure_set, col_pure_set
            new_rows = [a for a, _ in top_responses_from_counts(col_hist, response_batch)
                        if a not in row_set]
            new_cols = [a for a, _ in top_responses_from_counts(row_hist, response_batch)
                        if a not in col_set]
            entry["new_rows"] = len(new_rows)
            entry["new_columns"] = len(new_cols)
            should_stop = not new_rows and not new_cols
            rows.extend(_pure_strategy(a) for a in new_rows)
            cols.extend(_pure_strategy(a) for a in new_cols)
            row_pure_set.update(new_rows)
            col_pure_set.update(new_cols)
        history.append(entry)
        print(json.dumps(entry), flush=True)

        best[1]["iterations"] = history.copy()
        best[1]["iterations_completed"] = len(history)
        best[1]["double_oracle_state"] = {
            "row_pure_actions": [list(a) for a in sorted(row_pure_set)],
            "column_pure_actions": [list(a) for a in sorted(col_pure_set)],
        }
        if checkpoint is not None:
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            temporary = checkpoint.with_suffix(checkpoint.suffix + ".tmp")
            temporary.write_text(json.dumps(best[1]))
            temporary.replace(checkpoint)
        if should_stop:
            break

    best[1]["iterations"] = history
    best[1]["iterations_completed"] = len(history)
    best[1]["termination_tolerance"] = tolerance
    return best[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", type=Path)
    parser.add_argument("--seed-size", type=int, default=256)
    parser.add_argument("--response-batch", type=int, default=20)
    parser.add_argument("--max-iterations", type=int, default=50)
    parser.add_argument("--tolerance", type=float, default=1e-7)
    parser.add_argument("--resume-state", type=Path,
                        help="previous output containing a double_oracle_state")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = solve(args.strategy, seed_size=args.seed_size,
                   response_batch=args.response_batch,
                   max_iterations=args.max_iterations, tolerance=args.tolerance,
                   checkpoint=args.output, resume_state=args.resume_state)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in {"strategy", "lp_row_strategy", "lp_column_strategy"}},
                     indent=2))


if __name__ == "__main__":
    main()
