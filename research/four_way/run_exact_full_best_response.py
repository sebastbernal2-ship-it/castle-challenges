#!/usr/bin/env python3
"""Run the exact-integer full-action Game 2 response oracle.

Input mixtures are converted to an explicit integer-frequency distribution;
for that rational distribution the C++ oracle compares every legal action with
128-bit integer numerators and emits an exact payout fraction.
"""

import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import tempfile


def _load_entries(data: dict):
    if "population" in data:
        return [tuple(item["allocation"]) for item in data["population"]], [
            Fraction(item.get("weight", item.get("probability")))
            for item in data["population"]
        ]
    if "row_portfolio" in data:
        return [tuple(item["allocation"]) for item in data["row_portfolio"]], [
            Fraction(item["probability"]) for item in data["row_portfolio"]
        ]
    if "strategy" in data and "frequency_total" in data:
        total = int(data["frequency_total"])
        actions = [tuple(item[0]) for item in data["strategy"]]
        counts = [round(Fraction(item[1]) * total) for item in data["strategy"]]
        return actions, [Fraction(count, total) for count in counts]
    if "actions" in data:
        actions = [tuple(a) for a in data["actions"]]
        raw = data.get("last_half_time_average_probabilities_decimal")
        if raw is None:
            raw = data["last_half_time_average_probabilities"]
        return actions, [Fraction(value) for value in raw]
    raise ValueError("unrecognized Game 2 mixture JSON format")


def _integer_frequencies(actions: list[tuple[int, ...]], weights: list[Fraction],
                         total: int) -> dict[tuple[int, ...], int]:
    mass = sum(weights)
    if mass <= 0:
        raise ValueError("mixture must have positive total weight")
    probabilities = [weight / mass for weight in weights]
    raw = [probability * total for probability in probabilities]
    floors = [value.numerator // value.denominator for value in raw]
    residual = total - sum(floors)
    order = sorted(range(len(actions)),
                   key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:residual]:
        floors[i] += 1
    counts: dict[tuple[int, ...], int] = {}
    for action, count in zip(actions, floors):
        if count:
            if len(action) != 5 or sum(action) != 100 or min(action) < 0:
                raise ValueError(f"invalid allocation {action}")
            counts[action] = counts.get(action, 0) + count
    if sum(counts.values()) != total:
        raise AssertionError("integer-frequency quantization lost probability mass")
    return counts


def _retain_top_support(counts: dict[tuple[int, ...], int], max_support: int | None
                        ) -> tuple[dict[tuple[int, ...], int], int]:
    if max_support is None or len(counts) <= max_support:
        return counts, 0
    if max_support < 1:
        raise ValueError("max_support must be positive")
    actions = sorted(counts, key=counts.get, reverse=True)[:max_support]
    retained = {action: counts[action] for action in actions}
    return retained, sum(counts.values()) - sum(retained.values())


def _certified_payout_upper_bound(retained_payout: Fraction, tail: Fraction) -> Fraction:
    """If tail mass is delta, BR <= (1-delta)BR(retained)+9delta."""
    return min(Fraction(9), (1 - tail) * retained_payout + 9 * tail)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("population", type=Path)
    parser.add_argument("--frequency-total", type=int, default=1_000_000_000,
                        help="integer denominator for the audited rational mixture")
    parser.add_argument("--max-support", type=int,
                        help="keep the largest integer frequencies; add a rigorous 9*tail-mass BR bound")
    parser.add_argument("--compiler", default="c++")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.frequency_total <= 1_000_000_000_000:
        parser.error("frequency total must be in 1..1e12")

    data = json.loads(args.population.read_text(), parse_float=Fraction)
    actions, weights = _load_entries(data)
    counts = _integer_frequencies(actions, weights, args.frequency_total)
    try:
        retained, tail_mass = _retain_top_support(counts, args.max_support)
    except ValueError as error:
        parser.error(str(error))
    lines = [str(len(retained))]
    for action, count in sorted(retained.items()):
        lines.append(" ".join(map(str, action)) + " " + str(count))
    source = Path(__file__).with_name("exact_full_action_best_response.cpp")
    with tempfile.TemporaryDirectory(prefix="castle-fourway-exact-br-") as temp:
        binary = Path(temp) / "exact_best_response"
        subprocess.run([args.compiler, "-O3", "-std=c++17", str(source), "-o", str(binary)],
                       check=True, stdout=subprocess.DEVNULL)
        result = subprocess.run([str(binary)], input="\n".join(lines) + "\n",
                                text=True, capture_output=True, check=True).stdout.strip()
    allocation, numerator, denominator, profile_count = result.split("\t")
    exact_retained_payout = Fraction(int(numerator), int(denominator))
    tail_fraction = Fraction(tail_mass, args.frequency_total)
    payout_upper_bound = _certified_payout_upper_bound(exact_retained_payout,
                                                        tail_fraction)
    exploitability_upper_bound = payout_upper_bound - Fraction(15, 4)
    report = {
        "population_file": str(args.population),
        "original_support_size": len(actions),
        "quantized_support_size": len(counts),
        "oracle_support_size": len(retained),
        "frequency_total": args.frequency_total,
        "oracle_frequency_total": sum(retained.values()),
        "discarded_frequency_fraction": [tail_fraction.numerator, tail_fraction.denominator],
        "certified_global_best_response_upper_bound_fraction": [payout_upper_bound.numerator, payout_upper_bound.denominator],
        "certified_exploitability_upper_bound_fraction": [exploitability_upper_bound.numerator, exploitability_upper_bound.denominator],
        "certified_exploitability_upper_bound": float(exploitability_upper_bound),
        "distribution_quantization": "largest-remainder integer frequencies; all response arithmetic is exact for this rationalized mixture",
        "best_response": [int(x) for x in allocation.split(",")],
        "exact_expected_payout_fraction_on_oracle_mixture": f"{numerator}/{denominator}",
        "expected_payout_decimal_on_oracle_mixture": float(exact_retained_payout),
        "discard_bound": "A discarded mass delta changes any action's expected payout by at most 9*delta; retained probabilities are renormalized and globally best-responded exactly.",
        "unordered_opponent_triples": int(profile_count),
        "full_legal_action_count": 4_598_126,
        "scope": (
            "Exact full-action best response to the stated integer-frequency mixture; not an equilibrium claim."
            if tail_mass == 0 else
            "Exact best response to the retained mixture plus a rigorous global upper bound for the discarded mass; not an equilibrium claim."
        ),
    }
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
