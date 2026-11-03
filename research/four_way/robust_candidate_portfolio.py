#!/usr/bin/env python3
"""Find a restricted robust portfolio against saved opponent populations.

This is a zero-sum meta-game: the row player picks one candidate allocation,
and the column player picks one saved opponent population. It is not a GTO
solver for the original four-player game.
"""

import argparse
from collections import Counter
import json
from pathlib import Path

from castle_challenges.games.four_way.best_response import expected_payout


def read_population(path: Path) -> dict[tuple[int, ...], float]:
    data = json.loads(path.read_text())
    if "population" in data:
        return {tuple(row["allocation"]): float(row["weight"])
                for row in data["population"] if float(row["weight"]) > 0}
    probabilities = data.get(
        "last_half_time_average_probabilities_decimal",
        data["last_half_time_average_probabilities"],
    )
    return {tuple(action): float(weight)
            for action, weight in zip(data["actions"], probabilities)
            if float(weight) > 0}


def solve(population_files: list[Path], iterations: int = 100_000,
          extra_actions: list[tuple[int, ...]] | None = None) -> dict:
    populations = [read_population(path) for path in population_files]
    actions = sorted({action for population in populations for action in population}
                     | set(extra_actions or []))
    # Payoff matrix: candidate own allocation by opponent-population scenario.
    matrix = [[expected_payout(action, population) for population in populations]
              for action in actions]
    n, m = len(actions), len(populations)
    row_counts = [0] * n
    col_counts = [0] * m

    for t in range(iterations):
        row_total = max(1, t)
        col_total = max(1, t)
        row_payoffs = [sum(matrix[i][j] * col_counts[j] for j in range(m)) / col_total
                       for i in range(n)]
        col_payoffs = [sum(matrix[i][j] * row_counts[i] for i in range(n)) / row_total
                       for j in range(m)]
        # Deterministic first-index tie breaking keeps runs reproducible.
        row_choice = max(range(n), key=row_payoffs.__getitem__)
        col_choice = min(range(m), key=col_payoffs.__getitem__)
        row_counts[row_choice] += 1
        col_counts[col_choice] += 1

    row_prob = [count / iterations for count in row_counts]
    col_prob = [count / iterations for count in col_counts]
    row_values = [sum(row_prob[i] * matrix[i][j] for i in range(n)) for j in range(m)]
    col_values = [sum(col_prob[j] * matrix[i][j] for j in range(m)) for i in range(n)]
    lower = min(row_values)
    upper = max(col_values)
    portfolio = [
        {"allocation": list(action), "probability": row_prob[i]}
        for i, action in enumerate(actions) if row_prob[i] > 0
    ]
    scenario_mix = [
        {"population": str(path), "probability": col_prob[j],
         "portfolio_expected_payout": row_values[j]}
        for j, path in enumerate(population_files)
    ]
    return {
        "method": "fictitious play in the finite candidate-allocation by saved-population zero-sum meta-game",
        "iterations": iterations,
        "candidate_action_count": n,
        "opponent_population_count": m,
        "row_portfolio": portfolio,
        "scenario_results": scenario_mix,
        "worst_scenario_expected_payout": lower,
        "meta_game_upper_bound": upper,
        "restricted_meta_game_gap": upper - lower,
        "scope": "Robust only against these saved opponent populations and this finite candidate action set; not an equilibrium certificate.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("populations", nargs="+", type=Path)
    parser.add_argument("--iterations", type=int, default=100_000)
    parser.add_argument("--add-action", action="append", default=[],
                        help="extra comma-separated candidate allocation")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    extra_actions = [tuple(int(x) for x in row.split(",")) for row in args.add_action]
    if any(len(action) != 5 or min(action) < 0 or sum(action) != 100
           for action in extra_actions):
        parser.error("extra actions must contain five nonnegative integers summing to 100")
    result = solve(args.populations, args.iterations, extra_actions)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
