#!/usr/bin/env python3
"""Compile and run the native restricted four-way replicator solver."""

import argparse
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("population", type=Path, help="JSON with population[].allocation")
    parser.add_argument("--add-action", action="append", default=[],
                        help="extra comma-separated allocation to append to the support")
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--eta", type=float, default=0.02)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    data = json.loads(args.population.read_text())
    if "population" in data:
        actions = [tuple(entry["allocation"]) for entry in data["population"]]
    else:
        actions = [tuple(action) for action in data["actions"]]
    actions.extend(tuple(int(x) for x in row.split(",")) for row in args.add_action)
    if any(len(action) != 5 or sum(action) != 100 or min(action) < 0 for action in actions):
        parser.error("all support actions must contain five nonnegative integers summing to 100")
    if len(set(actions)) != len(actions):
        parser.error("support actions must be unique")

    source = Path(__file__).with_name("restricted_replicator.cpp")
    with tempfile.TemporaryDirectory(prefix="castle-replicator-") as tmp:
        binary = Path(tmp) / "replicator"
        subprocess.run(["c++", "-O3", "-std=c++17", str(source), "-o", str(binary)], check=True)
        payload = f"{len(actions)} {args.iterations} {args.eta}\n"
        payload += "".join(" ".join(map(str, action)) + "\n" for action in actions)
        output = subprocess.run([str(binary)], input=payload, text=True,
                                capture_output=True, check=True).stdout

    dynamics = json.loads(output, parse_float=Decimal)
    result = {
        "method": "native restricted symmetric multiplicative-weights dynamics",
        "iterations": args.iterations,
        "eta": args.eta,
        "actions": [list(action) for action in actions],
        "final_probabilities": [float(x) for x in dynamics["final_probabilities"]],
        "final_probabilities_decimal": [str(x) for x in dynamics["final_probabilities"]],
        "last_half_time_average_probabilities": [
            float(x) for x in dynamics["last_half_time_average_probabilities"]
        ],
        "last_half_time_average_probabilities_decimal": [
            str(x) for x in dynamics["last_half_time_average_probabilities"]
        ],
        "warning": "Restricted support only; not a full-game equilibrium certificate.",
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
