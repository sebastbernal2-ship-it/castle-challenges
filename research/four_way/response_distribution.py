#!/usr/bin/env python3
"""Audit a Game 2 response over every unordered opponent triple.

Input weights are parsed as decimal strings and converted to exact Fractions.
Profile payouts are converted to exact quarter-point integers by the rules
engine. This exposes tiny losing probability mass hidden by float rounding.
"""

import argparse
from collections import defaultdict
from fractions import Fraction
import itertools
import json
from pathlib import Path

from castle_challenges.games.four_way.rules import payout


def load_population(path: Path) -> tuple[list[tuple[int, ...]], list[Fraction]]:
    data = json.loads(path.read_text(), parse_float=Fraction)
    if "population" in data:
        entries = data["population"]
        actions = [tuple(entry["allocation"]) for entry in entries]
        weights = [Fraction(entry["weight"]) for entry in entries]
    else:
        actions = [tuple(a) for a in data["actions"]]
        decimal_weights = data.get(
            "last_half_time_average_probabilities_decimal",
            data["last_half_time_average_probabilities"],
        )
        weights = [Fraction(w) for w in decimal_weights]
    total = sum(weights)
    if total <= 0:
        raise ValueError("population has no positive probability mass")
    return actions, [w / total for w in weights]


def audit(path: Path, response: tuple[int, ...]) -> dict:
    actions, probabilities = load_population(path)
    hist: dict[int, Fraction] = defaultdict(Fraction)
    profile_count = 0
    for i, j, k in itertools.combinations_with_replacement(range(len(actions)), 3):
        if i == j == k:
            multiplicity = 1
        elif i == j or j == k:
            multiplicity = 3
        else:
            multiplicity = 6
        probability = (multiplicity * probabilities[i] * probabilities[j] * probabilities[k])
        if probability == 0:
            continue
        player_payout = payout((response, actions[i], actions[j], actions[k]))[0]
        payout_quarters = round(player_payout * 4)
        hist[payout_quarters] += probability
        profile_count += 1
    expected_quarters = sum(Fraction(q) * p for q, p in hist.items())
    expected = expected_quarters / 4
    shortfall = Fraction(9) - expected
    below_nine = 1 - hist.get(36, Fraction(0))
    return {
        "population_file": str(path),
        "response": list(response),
        "support_size": len(actions),
        "positive_probability_unordered_triples": profile_count,
        "total_probability": str(sum(hist.values())),
        "payout_probability": {
            str(Fraction(q, 4)): {
                "fraction": str(probability),
                "decimal": float(probability),
            }
            for q, probability in sorted(hist.items())
        },
        "exact_expected_payout_fraction": str(expected),
        "expected_payout_decimal": float(expected),
        "expected_shortfall_from_nine_fraction": str(shortfall),
        "expected_shortfall_from_nine_decimal": float(shortfall),
        "probability_mass_below_nine": str(below_nine),
        "probability_mass_below_nine_decimal": float(below_nine),
        "guaranteed_first_against_full_support": hist.get(36, Fraction(0)) == 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("population", type=Path)
    parser.add_argument("response", help="five comma-separated soldier counts")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    response = tuple(int(x) for x in args.response.split(","))
    if len(response) != 5 or sum(response) != 100 or min(response) < 0:
        parser.error("response must be five nonnegative integers summing to 100")
    result = audit(args.population, response)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
