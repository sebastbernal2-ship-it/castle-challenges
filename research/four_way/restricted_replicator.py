#!/usr/bin/env python3
"""Explore a restricted symmetric Game 2 support with multiplicative weights.

This is an exploratory restricted-game method. It does not certify equilibrium
outside the supplied strategy pool and multiplayer replicator dynamics can cycle.
"""

import argparse
import json
import math
from pathlib import Path

from castle_challenges.games.four_way.rules import payout


def solve(actions: list[tuple[int, ...]], iterations: int = 20_000,
          eta: float = 0.1) -> tuple[list[float], list[float]]:
    n = len(actions)
    if not n or iterations < 1 or eta <= 0:
        raise ValueError("need actions, positive iterations, and positive eta")
    # Tensor[i][j][k][l] is payoff to i against ordered opponents j,k,l.
    tensor = [[[[0.0] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                for ell in range(n):
                    tensor[i][j][k][ell] = payout(
                        (actions[i], actions[j], actions[k], actions[ell]))[0]
    probabilities = [1 / n] * n
    average = [0.0] * n
    kept = 0
    for t in range(iterations):
        payoffs = [0.0] * n
        for i in range(n):
            total = 0.0
            for j in range(n):
                pj = probabilities[j]
                if not pj:
                    continue
                for k in range(n):
                    pjk = pj * probabilities[k]
                    if not pjk:
                        continue
                    for ell in range(n):
                        total += pjk * probabilities[ell] * tensor[i][j][k][ell]
            payoffs[i] = total
        # Symmetry and constant-sum imply the population's mean payoff is 3.75.
        logits = [math.log(max(p, 1e-300)) + eta * (u - 3.75)
                  for p, u in zip(probabilities, payoffs)]
        top = max(logits)
        weights = [math.exp(x - top) for x in logits]
        norm = sum(weights)
        probabilities = [x / norm for x in weights]
        if t >= iterations // 2:
            for i, p in enumerate(probabilities):
                average[i] += p
            kept += 1
    return probabilities, [x / kept for x in average]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("population", type=Path, help="JSON with population[].allocation")
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--eta", type=float, default=0.1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.population.read_text())
    actions = [tuple(x["allocation"]) for x in data["population"]]
    final, average = solve(actions, args.iterations, args.eta)
    payload = {
        "method": "restricted symmetric multiplicative-weights dynamics",
        "iterations": args.iterations,
        "eta": args.eta,
        "actions": [list(a) for a in actions],
        "final_probabilities": final,
        "last_half_time_average_probabilities": average,
        "warning": "Restricted support only; not a full-game equilibrium certificate.",
    }
    text = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
