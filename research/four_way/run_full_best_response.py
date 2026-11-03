#!/usr/bin/env python3
"""Compile/run the exact Game 2 action-space response search for a JSON mixture."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("population", type=Path)
    parser.add_argument("--compiler", default="c++")
    args = parser.parse_args()
    data = json.loads(args.population.read_text())
    if "population" in data:
        entries = data["population"]
    elif "row_portfolio" in data:
        entries = [
            {"allocation": entry["allocation"], "weight": entry["probability"]}
            for entry in data["row_portfolio"]
        ]
    else:
        probabilities = data.get(
            "last_half_time_average_probabilities_decimal",
            data["last_half_time_average_probabilities"],
        )
        if len(data["actions"]) != len(probabilities):
            raise ValueError("action and probability arrays must have the same length")
        entries = [
            {"allocation": action, "weight": weight}
            for action, weight in zip(data["actions"], probabilities)
        ]
    lines = [str(len(entries))]
    for entry in entries:
        allocation = entry["allocation"]
        if len(allocation) != 5 or sum(allocation) != 100:
            parser.error(f"invalid allocation in {args.population}: {allocation}")
        lines.append(" ".join(map(str, allocation)) + " " + str(entry["weight"]))
    source = Path(__file__).with_name("full_action_best_response.cpp")
    with tempfile.TemporaryDirectory(prefix="castle-br4-") as temp:
        binary = Path(temp) / "best_response"
        subprocess.run([args.compiler, "-O3", "-std=c++17", str(source), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], input="\n".join(lines) + "\n",
                                text=True, capture_output=True, check=True)
    allocation, value, profile_count = result.stdout.strip().split("\t")
    print(json.dumps({
        "population_file": str(args.population),
        "support_size": len(entries),
        "unordered_opponent_profiles": int(profile_count),
        "full_legal_action_count": 4_598_126,
        "best_response": [int(x) for x in allocation.split(",")],
        "expected_payout": float(value),
        "expected_payout_text": value,
        "probability_arithmetic": "long double; profile scoring and action enumeration are exact",
        "scope": "Full pure-action best response to supplied mixture only; not an equilibrium result."
    }, indent=2))


if __name__ == "__main__":
    main()
