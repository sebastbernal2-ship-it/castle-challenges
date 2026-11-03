#!/usr/bin/env python3
"""Cutting-plane LP for a Game 1 symmetric minimax strategy.

A mixed allocation strategy is represented as a unit flow on the 5-layer
allocation DAG. 505 castle soldier-count marginals are linked to that flow.
For each pure opponent allocation b, the constraint that b's expected score
against the candidate be <= 7.5 is linear in those marginals. A full-action
DP best response separates omitted constraints. This is a scalable candidate
generator; floating-point LP output is never called an exact equilibrium until
the resulting finite mixture passes the integer full-action verifier.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, vstack

from castle_challenges.common.allocation import VALUES
from castle_challenges.games.head_to_head.best_response import best_response_from_marginals

SOLDIERS = 100
CASTLES = 5
MARGINALS = CASTLES * (SOLDIERS + 1)


def make_network():
    """Build edge list, sparse flow/link equalities, and marginal edge lookup."""
    edges = []
    by_castle_count = [[[] for _ in range(SOLDIERS + 1)] for _ in range(CASTLES)]
    for castle in range(CASTLES):
        for start in range(SOLDIERS + 1):
            for count in range(SOLDIERS - start + 1):
                index = len(edges)
                edges.append((castle, start, count))
                by_castle_count[castle][count].append(index)

    nflow = len(edges)
    nvar = nflow + MARGINALS + 1  # final variable is common slack in doubled points
    slack = nvar - 1
    node_rows, node_cols, node_data = [], [], []
    for edge_index, (castle, start, count) in enumerate(edges):
        source = castle * 101 + start
        target = (castle + 1) * 101 + start + count
        node_rows.extend((source, target))
        node_cols.extend((edge_index, edge_index))
        node_data.extend((1.0, -1.0))
    network = coo_matrix((node_data, (node_rows, node_cols)), shape=(606, nvar)).tocsr()
    rhs_network = np.zeros(606)
    rhs_network[0] = 1.0
    rhs_network[5 * 101 + SOLDIERS] = -1.0

    link_rows, link_cols, link_data = [], [], []
    for castle in range(CASTLES):
        for count in range(SOLDIERS + 1):
            row = castle * 101 + count
            marginal_col = nflow + row
            link_rows.append(row)
            link_cols.append(marginal_col)
            link_data.append(1.0)
            for edge_index in by_castle_count[castle][count]:
                link_rows.append(row)
                link_cols.append(edge_index)
                link_data.append(-1.0)
    links = coo_matrix((link_data, (link_rows, link_cols)),
                       shape=(MARGINALS, nvar)).tocsr()
    a_eq = vstack((network, links), format="csr")
    b_eq = np.concatenate((rhs_network, np.zeros(MARGINALS)))
    return edges, by_castle_count, nflow, nvar, slack, a_eq, b_eq


def cut_row(action, nflow, nvar):
    """Linear coefficients for doubled payoff of pure action vs candidate."""
    cols, values = [], []
    for castle, opponent_count in enumerate(action):
        value = VALUES[castle]
        base = nflow + castle * 101
        for own_count in range(opponent_count):
            cols.append(base + own_count)
            values.append(2.0 * value)
        cols.append(base + opponent_count)
        values.append(float(value))
    cols.append(nvar - 1)
    values.append(1.0)
    return cols, values


def make_cut_matrix(actions, nflow, nvar):
    rows, cols, data = [], [], []
    for row, action in enumerate(actions):
        action_cols, values = cut_row(action, nflow, nvar)
        rows.extend([row] * len(action_cols))
        cols.extend(action_cols)
        data.extend(values)
    return coo_matrix((data, (rows, cols)), shape=(len(actions), nvar)).tocsr()


def strategy_marginals(strategy_path):
    data = json.loads(Path(strategy_path).read_text())
    frequency = int(data.get("frequency_total", 0))
    hist = [[0] * 101 for _ in range(CASTLES)]
    allocations = []
    for entry in data["strategy"]:
        action = tuple(map(int, entry[0]))
        count = int(round(float(entry[1]) * frequency))
        if count <= 0:
            continue
        allocations.append((action, count))
        for castle, soldiers in enumerate(action):
            hist[castle][soldiers] += count
    return allocations, hist, frequency


def initial_cuts(strategy_path, include_support=500):
    allocations, _, _ = strategy_marginals(strategy_path)
    data = json.loads(Path(strategy_path).read_text())
    cuts = {tuple(map(int, a)) for a in data.get("trace", [])
            if isinstance(a, list) and len(a) == CASTLES}
    for record in data.get("trace", []):
        if isinstance(record, dict) and "best_response" in record:
            cuts.add(tuple(map(int, record["best_response"])))
    allocations.sort(key=lambda pair: -pair[1])
    cuts.update(action for action, _ in allocations[:include_support])
    return sorted(cuts)


def decompose_flow(flow, edges, *, tolerance=1e-12):
    adjacency = [[[] for _ in range(101)] for _ in range(CASTLES)]
    for value, (castle, start, count) in zip(flow, edges):
        if value > tolerance:
            adjacency[castle][start].append((count, float(value)))
    paths = {}
    for _ in range(100_000):
        chosen = []
        states = [0]
        for castle in range(CASTLES):
            options = sorted(adjacency[castle][states[-1]], key=lambda x: -x[1])
            if not options:
                break
            count, _ = options[0]
            chosen.append(count)
            states.append(states[-1] + count)
        if len(chosen) != CASTLES or states[-1] != SOLDIERS:
            # Search a path with DFS rather than choosing locally largest arcs.
            path = []
            def visit(castle, state):
                if castle == CASTLES:
                    return state == SOLDIERS
                for count, mass in sorted(adjacency[castle][state], key=lambda x: -x[1]):
                    if mass <= tolerance or state + count > SOLDIERS:
                        continue
                    path.append(count)
                    if visit(castle + 1, state + count):
                        return True
                    path.pop()
                return False
            if not visit(0, 0):
                break
            chosen = list(path)
            states = [0]
            for count in chosen:
                states.append(states[-1] + count)
        bottleneck = min(next(mass for count, mass in adjacency[c][states[c]]
                              if count == chosen[c]) for c in range(CASTLES))
        if bottleneck <= tolerance:
            break
        action = tuple(chosen)
        paths[action] = paths.get(action, 0.0) + bottleneck
        for castle in range(CASTLES):
            state = states[castle]
            for index, (count, mass) in enumerate(adjacency[castle][state]):
                if count == chosen[castle]:
                    adjacency[castle][state][index] = (count, max(0.0, mass - bottleneck))
                    break
    total = sum(paths.values())
    if total <= 0 or abs(total - 1.0) > 2e-7:
        raise RuntimeError(f"flow decomposition mass is {total}, expected 1")
    return {action: mass / total for action, mass in paths.items()}


def quantize(distribution, total):
    scaled = {a: p * total for a, p in distribution.items()}
    counts = {a: math.floor(v) for a, v in scaled.items()}
    residual = total - sum(counts.values())
    for action in sorted(scaled, key=lambda a: scaled[a] - counts[a], reverse=True)[:residual]:
        counts[action] += 1
    return {a: n for a, n in counts.items() if n > 0}


def quantize_marginals(marginals, total=2**30):
    output = []
    for row in marginals:
        row = np.maximum(0.0, np.asarray(row, dtype=float))
        row /= row.sum()
        scaled = row * total
        counts = np.floor(scaled).astype(np.int64)
        residual = total - int(counts.sum())
        order = np.argsort(-(scaled - counts))
        counts[order[:residual]] += 1
        output.append(counts.tolist())
    return tuple(output)


def audit_strategy(strategy, frequency, verify_script):
    path = Path(strategy)
    result = subprocess.run([sys.executable, str(verify_script), str(path)],
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def run(args):
    edges, by_count, nflow, nvar, slack, a_eq, b_eq = make_network()
    if args.resume and args.state.exists():
        state = json.loads(args.state.read_text())
        cuts = {tuple(a) for a in state["cuts"]}
        history = state.get("history", [])
    else:
        cuts = set(initial_cuts(args.seed_strategy, args.seed_support))
        history = []
    c = np.zeros(nvar)
    c[slack] = -1.0
    bounds = [(0.0, None)] * (nvar - 1) + [(None, None)]
    best_gap = math.inf
    best_certificate = None
    verify_script = Path(__file__).with_name("verify_strategy.py")

    for iteration in range(args.max_iterations):
        ordered_cuts = sorted(cuts)
        a_ub = make_cut_matrix(ordered_cuts, nflow, nvar)
        b_ub = np.full(len(ordered_cuts), 15.0)
        result = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq,
                         bounds=bounds, method="highs",
                         options={"primal_feasibility_tolerance": 1e-9,
                                  "dual_feasibility_tolerance": 1e-9,
                                  "ipm_optimality_tolerance": 1e-10})
        if not result.success:
            raise RuntimeError(f"LP iteration {iteration}: {result.message}")
        x = result.x
        marginals = tuple(x[nflow + i * 101:nflow + (i + 1) * 101].tolist()
                          for i in range(CASTLES))
        response, response_score = best_response_from_marginals(marginals, 1.0)
        max_score2 = 2.0 * response_score
        slack_value = float(x[slack])
        record = {"iteration": iteration, "cuts": len(cuts),
                  "lp_slack_doubled_points": slack_value,
                  "full_action_best_response": list(response),
                  "full_action_best_response_score": response_score,
                  "full_action_gap": response_score - 7.5,
                  "lp_status": result.message}
        history.append(record)
        print(json.dumps(record), flush=True)

        flow = np.maximum(0.0, x[:nflow])
        distribution = decompose_flow(flow, edges)
        counts = quantize(distribution, args.frequency_total)
        candidate = {
            "source": str(args.seed_strategy),
            "method": "marginal-polytope cutting-plane LP with full-action DP separation",
            "frequency_total": args.frequency_total,
            "iteration": iteration,
            "lp_slack_doubled_points": slack_value,
            "continuous_best_response": list(response),
            "continuous_best_response_score": response_score,
            "flow_decomposition_support": len(distribution),
            "continuous_strategy": [[list(a), probability]
                                    for a, probability in sorted(distribution.items())],
            "restricted_cut_actions": [list(a) for a in ordered_cuts],
            "strategy": [[list(a), count / args.frequency_total]
                         for a, count in sorted(counts.items())],
            "warning": "Floating-point LP candidate; exact verifier output is the only certificate.",
        }
        candidate_path = args.output.with_name(args.output.stem + ".candidate.json")
        candidate_path.write_text(json.dumps(candidate, indent=2) + "\n")
        certificate = audit_strategy(candidate_path, args.frequency_total, verify_script)
        gap = float(certificate["exploitability"])
        record["quantized_exact_gap"] = gap
        record["quantized_exact_best_response"] = certificate["best_response"]
        print(json.dumps({"audit_iteration": iteration, **certificate}), flush=True)
        if gap < best_gap:
            best_gap = gap
            best_certificate = certificate
            candidate["exact_verification"] = certificate
            args.output.write_text(json.dumps(candidate, indent=2) + "\n")
            state = {"cuts": [list(a) for a in sorted(cuts)], "history": history,
                     "best_gap": best_gap}
            args.state.write_text(json.dumps(state, indent=2) + "\n")

        if response_score <= 7.5 + args.continuous_tolerance:
            break
        if response in cuts:
            raise RuntimeError("separation returned an already constrained action; solver tolerance or coefficient mismatch")
        cuts.add(response)
        # Save cuts even when the quantized strategy did not improve.
        args.state.write_text(json.dumps({"cuts": [list(a) for a in sorted(cuts)],
                                         "history": history,
                                         "best_gap": best_gap}, indent=2) + "\n")

    return {"best_gap": best_gap, "best_certificate": best_certificate,
            "iterations": len(history), "cuts": len(cuts),
            "output": str(args.output), "state": str(args.state)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-strategy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed-support", type=int, default=500)
    parser.add_argument("--frequency-total", type=int, default=20_000_260)
    parser.add_argument("--max-iterations", type=int, default=200)
    parser.add_argument("--continuous-tolerance", type=float, default=1e-8)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
