#!/usr/bin/env python3
"""Exact full-action response oracle for the Game 2 equilibrium homotopy."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))
from run_exact_full_best_response import _integer_frequencies, _load_entries

A0 = (20, 20, 20, 20, 20)
A1 = (19, 20, 20, 20, 21)


def action_cost(action: tuple[int, ...]) -> Fraction:
    if action == A0:
        return Fraction(0)
    if action == A1:
        return Fraction(1)
    weighted = sum((i + 1) * count for i, count in enumerate(action))
    return Fraction(10_000 + weighted, 5_000)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mixture", type=Path)
    parser.add_argument("--t-num", type=int, required=True)
    parser.add_argument("--t-den", type=int, required=True)
    parser.add_argument("--frequency-total", type=int, default=1_000_000)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.t_num <= args.t_den <= 1_000_000:
        parser.error("require 0 <= t-num <= t-den <= 1,000,000")
    if not 1 <= args.frequency_total <= 1_000_000:
        parser.error("frequency-total must be in 1..1,000,000")
    data = json.loads(args.mixture.read_text())
    actions, weights = _load_entries(data)
    counts = _integer_frequencies(actions, weights, args.frequency_total)
    source = Path(__file__).with_name("exact_auxiliary_best_response.cpp")
    binary = Path(tempfile.gettempdir()) / "castle-game2-auxiliary-response"
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(["c++", "-O3", "-std=c++17", "-pthread", str(source), "-o", str(binary)], check=True)
    input_text = str(len(counts)) + "\n" + "".join(
        " ".join(map(str, action)) + " " + str(count) + "\n"
        for action, count in counts.items()
    )
    raw = subprocess.run(
        [str(binary), str(args.threads), str(args.top_k), str(args.t_num), str(args.t_den)],
        input=input_text, text=True, capture_output=True, check=True,
    ).stdout
    total = args.frequency_total
    expected_cost = sum(Fraction(count, total) * action_cost(action)
                        for action, count in counts.items())
    t = Fraction(args.t_num, args.t_den)
    responses = []
    for line in raw.splitlines():
        allocation, numerator, denominator, adjusted, triples = line.split("\t")
        action = tuple(map(int, allocation.split(",")))
        payout = Fraction(int(numerator), int(denominator))
        utility = (1 - t) * (Fraction(15, 4) - action_cost(action) + expected_cost) + t * payout
        responses.append({
            "allocation": list(action),
            "target_payout_fraction": [payout.numerator, payout.denominator],
            "target_payout": float(payout),
            "auxiliary_payout_fraction": [utility.numerator, utility.denominator],
            "auxiliary_payout": float(utility),
            "adjusted_component_numerator": adjusted,
            "class_cost_fraction": [action_cost(action).numerator, action_cost(action).denominator],
            "opponent_triples": int(triples),
        })
    result = {
        "t_fraction": [args.t_num, args.t_den],
        "frequency_total": total,
        "support_size": len(counts),
        "expected_cost_fraction": [expected_cost.numerator, expected_cost.denominator],
        "top_responses": responses,
        "scope": "exact ranking over all 4,598,126 legal actions for this quantized mixture and auxiliary cost",
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
