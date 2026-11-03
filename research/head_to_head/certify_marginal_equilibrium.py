#!/usr/bin/env python3
"""Rationalize and exactly certify a marginal-polytope LP equilibrium candidate.

The floating LP is only a discovery step. This script reconstructs small exact
marginal fractions, finds an integer path-flow coupling with a MILP, and writes
an explicit finite strategy. The final claim is accepted only if the existing
integer-DP verifier returns zero exploitability over every legal action.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from castle_challenges.common.allocation import VALUES
from castle_challenges.games.head_to_head.best_response import best_response_from_counts
from marginal_polytope_lp import make_network


def rationalize_marginals(candidate: Path, max_denominator: int):
    data = json.loads(candidate.read_text())
    strategy = data.get("continuous_strategy")
    if not strategy:
        raise ValueError("candidate must contain continuous_strategy from marginal_polytope_lp.py")
    marginals = [[0.0] * 101 for _ in VALUES]
    for raw_action, probability in strategy:
        action = tuple(map(int, raw_action))
        if len(action) != 5 or sum(action) != 100 or min(action) < 0:
            raise ValueError(f"invalid allocation in continuous candidate: {action}")
        for castle, soldiers in enumerate(action):
            marginals[castle][soldiers] += float(probability)
    exact = [[Fraction(value).limit_denominator(max_denominator) for value in row]
             for row in marginals]
    if any(sum(row) != 1 for row in exact):
        raise ValueError("small-denominator reconstruction did not normalize each marginal exactly")
    denominator = math.lcm(*(value.denominator for row in exact for value in row))
    counts = [[int(value * denominator) for value in row] for row in exact]
    if any(sum(row) != denominator for row in counts):
        raise AssertionError("exact marginal counts do not sum to common denominator")
    return exact, denominator, counts


def find_integer_flow(denominator: int, marginal_counts: list[list[int]], time_limit: float):
    edges, _, nflow, nvar, slack, a_eq, b_eq = make_network()
    b_eq = b_eq.copy()
    b_eq[0] = denominator
    b_eq[5 * 101 + 100] = -denominator
    fixed_marginals = [value for row in marginal_counts for value in row]
    bounds = Bounds(
        np.zeros(nvar),
        np.asarray([denominator] * nflow + fixed_marginals + [0], dtype=float),
    )
    integrality = np.asarray([1] * nflow + [0] * (nvar - nflow), dtype=np.uint8)
    result = milp(
        np.zeros(nvar), integrality=integrality, bounds=bounds,
        constraints=LinearConstraint(a_eq, b_eq, b_eq),
        options={"time_limit": time_limit, "mip_rel_gap": 0.0, "presolve": True},
    )
    if result.x is None:
        raise RuntimeError(f"integer path-flow coupling not found: {result.message}")
    raw_flow = result.x[:nflow]
    if np.max(np.abs(raw_flow - np.rint(raw_flow))) > 1e-7:
        raise RuntimeError("MILP did not return an integral path flow")
    flow = [int(value) for value in np.rint(raw_flow)]
    # Independently check the integer network balances and all marginal totals.
    node_balance = [0] * 606
    observed = [[0] * 101 for _ in VALUES]
    for mass, (castle, start, count) in zip(flow, edges):
        node_balance[castle * 101 + start] += mass
        node_balance[(castle + 1) * 101 + start + count] -= mass
        observed[castle][count] += mass
    expected = [0] * 606
    expected[0] = denominator
    expected[5 * 101 + 100] = -denominator
    if node_balance != expected:
        raise RuntimeError("rounded integer flow fails exact node conservation")
    if observed != marginal_counts:
        raise RuntimeError("integer flow does not match the rational marginals")
    return edges, flow, result.message


def decompose_integer_flow(edges, flow, denominator: int):
    adjacency = [[[] for _ in range(101)] for _ in VALUES]
    for mass, (castle, start, count) in zip(flow, edges):
        if mass:
            adjacency[castle][start].append([count, mass])
    paths: dict[tuple[int, ...], int] = {}
    while True:
        path: list[int] = []

        def visit(castle: int, state: int) -> bool:
            if castle == len(VALUES):
                return state == 100
            for count, mass in sorted(adjacency[castle][state], key=lambda edge: -edge[1]):
                if mass <= 0 or state + count > 100:
                    continue
                path.append(count)
                if visit(castle + 1, state + count):
                    return True
                path.pop()
            return False

        if not visit(0, 0):
            break
        action = tuple(path)
        states = [0]
        for count in action:
            states.append(states[-1] + count)
        mass = min(next(value for count, value in adjacency[castle][states[castle]]
                        if count == action[castle]) for castle in range(5))
        if mass <= 0:
            raise AssertionError("path search returned a zero-mass path")
        paths[action] = paths.get(action, 0) + mass
        for castle in range(5):
            state = states[castle]
            for edge in adjacency[castle][state]:
                if edge[0] == action[castle]:
                    edge[1] -= mass
                    break
    if sum(paths.values()) != denominator:
        raise RuntimeError(f"path decomposition has mass {sum(paths.values())}, expected {denominator}")
    return paths


def certify(candidate: Path, output: Path, max_denominator: int, time_limit: float):
    _, denominator, marginal_counts = rationalize_marginals(candidate, max_denominator)
    edges, flow, solver_status = find_integer_flow(denominator, marginal_counts, time_limit)
    paths = decompose_integer_flow(edges, flow, denominator)
    # Verify path decomposition independently reproduces every marginal.
    reconstructed = [[0] * 101 for _ in VALUES]
    for action, count in paths.items():
        if len(action) != 5 or sum(action) != 100 or min(action) < 0:
            raise AssertionError(f"illegal decomposed allocation: {action}")
        for castle, soldiers in enumerate(action):
            reconstructed[castle][soldiers] += count
    if reconstructed != marginal_counts:
        raise AssertionError("decomposed strategy does not reproduce rational marginals")
    counts = tuple(tuple(row) for row in reconstructed)
    response, numerator, response_denominator = best_response_from_counts(counts)
    gap_numerator = numerator - 15 * denominator
    result = {
        "source_candidate": str(candidate),
        "method": "rational marginals plus integral layered path-flow coupling",
        "frequency_total": denominator,
        "flow_milp_status": solver_status,
        "marginal_denominator": denominator,
        "marginal_counts": marginal_counts,
        "path_flow_support_size": len(paths),
        "best_response": list(response),
        "best_response_score_fraction": [numerator, response_denominator],
        "exploitability_fraction": [gap_numerator, response_denominator],
        "exploitability": gap_numerator / response_denominator,
        "verified_full_action_space": True,
        "strategy": [[list(action), mass / denominator]
                     for action, mass in sorted(paths.items())],
        "interpretation": "A zero exact gap is a full-game equilibrium certificate under the encoded rules.",
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    verifier = Path(__file__).with_name("verify_strategy.py")
    verified = json.loads(subprocess.run(
        [sys.executable, str(verifier), str(output)], text=True,
        capture_output=True, check=True).stdout)
    if verified["exploitability_fraction"][0] != gap_numerator:
        raise RuntimeError("independent strategy verifier disagrees with marginal DP")
    if gap_numerator != 0:
        raise RuntimeError(f"candidate has positive exact gap: {verified['exploitability_fraction']}")
    result["independent_full_action_verification"] = verified
    output.write_text(json.dumps(result, indent=2) + "\n")
    output.with_suffix(".verify.json").write_text(json.dumps(verified, indent=2) + "\n")
    return verified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True,
                        help="LP output JSON containing a continuous_strategy field")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-denominator", type=int, default=1000)
    parser.add_argument("--milp-time-limit", type=float, default=300.0)
    args = parser.parse_args()
    print(json.dumps(certify(args.candidate, args.output, args.max_denominator,
                             args.milp_time_limit), indent=2))


if __name__ == "__main__":
    main()
