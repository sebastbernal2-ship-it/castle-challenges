#!/usr/bin/env python3
"""Measure whether listed high-payout replies rely on tiny support tails."""

from fractions import Fraction
import json
from pathlib import Path

from response_distribution import audit

ROOT = Path(__file__).parent
CASES = [
    ("pool18", "results/replicator_runs/diverse-pool18.json", (21, 24, 28, 25, 2)),
    ("pool19", "results/replicator_runs/diverse-pool19-response1.json", (21, 25, 29, 0, 25)),
    ("pool20", "results/replicator_runs/diverse-pool20-response2.json", (6, 26, 30, 32, 6)),
    ("pool21", "results/replicator_runs/diverse-pool21-response3-100k.json", (22, 27, 31, 0, 20)),
    ("pool22", "results/replicator_runs/diverse-pool22-response4-100k.json", (0, 0, 32, 33, 35)),
    ("robust_portfolio", "results/robust_candidate_portfolio.json", (0, 0, 32, 26, 42)),
]
CUTOFFS = [Fraction(0), Fraction(1, 10**8), Fraction(1, 10**12),
           Fraction(1, 10**16), Fraction(1, 10**100)]


def main() -> None:
    rows = []
    for name, relative_path, response in CASES:
        path = ROOT / relative_path
        for cutoff in CUTOFFS:
            result = audit(path, response, cutoff)
            rows.append({
                "case": name,
                "population_file": relative_path,
                "response": list(response),
                "minimum_action_probability": str(cutoff),
                "retained_support_size": result["support_size"],
                "retained_original_probability_mass": float(
                    Fraction(result["retained_original_probability_mass"])),
                "expected_payout": result["expected_payout_decimal"],
                "expected_shortfall_from_9": result["expected_shortfall_from_nine_decimal"],
                "probability_of_payout_below_9": result["probability_mass_below_nine_decimal"],
                "guaranteed_9_against_retained_support": result[
                    "guaranteed_first_against_full_support"],
            })
    out = {
        "method": "exact-rational response payout audit after discarding actions below each probability cutoff and renormalizing",
        "cutoffs_are_on_each_action_probability_before_renormalization": True,
        "results": rows,
        "interpretation": "Truncation diagnostics only: discarded probability mass is reported, and no claim is made about profiles involving omitted actions.",
    }
    path = ROOT / "results" / "support_threshold_audit.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
