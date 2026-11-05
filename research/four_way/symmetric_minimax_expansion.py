#!/usr/bin/env python3
"""Restricted symmetric minimax search with exact full-action response expansion.

For any population p, the mean of pure-action payoffs weighted by p is exactly
15/4, so max_a g_a(p) >= 15/4. On a finite pool P, minimizing max_{a in P}
g_a(p) to 15/4 is equivalent to finding a symmetric Nash equilibrium of that
restricted game. The objective is a nonconvex cubic max; multistart SLSQP only
generates candidates. We exact-audit several distinct restricted equilibria
against all legal actions and add their profitable responses to the pool.
"""

from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix

VALUE = 15.0 / 4.0
_PAYOFF_FUNCTION = None


def _payoff_function():
    global _PAYOFF_FUNCTION
    if _PAYOFF_FUNCTION is not None:
        return _PAYOFF_FUNCTION
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("a C++17 compiler is required for restricted payoff tensors")
    source = Path(__file__).with_name("restricted_payoff_tensor.cpp")
    library = Path(tempfile.gettempdir()) / "castle-fourway-payoff-tensor.so"
    if not library.exists() or library.stat().st_mtime < source.stat().st_mtime:
        subprocess.run([compiler, "-O3", "-std=c++17", "-shared", "-fPIC",
                        str(source), "-o", str(library)], check=True,
                       stdout=subprocess.DEVNULL)
    loaded = ctypes.CDLL(str(library))
    function = loaded.four_way_payoff_tensor
    function.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                         ctypes.POINTER(ctypes.c_uint8)]
    function.restype = None
    _PAYOFF_FUNCTION = (loaded, function)
    return _PAYOFF_FUNCTION


def load_actions(path: Path) -> list[tuple[int, ...]]:
    data = json.loads(path.read_text())
    if "actions" in data:
        raw = data["actions"]
    elif "population" in data:
        raw = [entry["allocation"] for entry in data["population"]]
    elif "strategy" in data:
        raw = [entry[0] for entry in data["strategy"]]
    else:
        raise ValueError("pool must contain actions, population, or strategy")
    actions = []
    for row in raw:
        action = tuple(map(int, row))
        if len(action) != 5 or sum(action) != 100 or min(action) < 0:
            raise ValueError(f"invalid allocation {action}")
        if action not in actions:
            actions.append(action)
    return actions


def payoff_tensor(actions: list[tuple[int, ...]]):
    """Quarter-unit payoffs against unordered opponent triples with multiplicity."""
    n = len(actions)
    triples, multiplicities = [], []
    for j in range(n):
        for k in range(j, n):
            for ell in range(k, n):
                triples.append((j, k, ell))
                multiplicities.append(1 if j == ell else 3 if j == k or k == ell else 6)
    triple_array = np.asarray(triples, dtype=np.int32)
    multiplicity_array = np.asarray(multiplicities, dtype=np.float64)
    output = (ctypes.c_uint8 * (n * len(triples)))()
    flat_actions = (ctypes.c_int * (5 * n))(*(x for action in actions for x in action))
    _library, function = _payoff_function()
    function(flat_actions, n, output)
    # Keep quarter-unit payouts compact; matrix products promote against the
    # float64 probability weights, while preserving uint8 cuts tensor memory 8x.
    tensor = np.ctypeslib.as_array(output).reshape(n, len(triples))
    return triple_array, multiplicity_array, tensor


def prune_pool_support(actions, probabilities, threshold):
    """Drop inactive restricted actions; the full-game oracle still audits globally."""
    probabilities = np.asarray(probabilities, dtype=np.float64)
    keep = probabilities > threshold
    if not np.any(keep):
        raise ValueError("support pruning removed every action")
    reduced = probabilities[keep]
    reduced /= reduced.sum()
    return [action for action, active in zip(actions, keep) if active], reduced


def payoff_and_jacobian(p, triples, multiplicities, tensor):
    j, k, ell = triples.T
    weighted = multiplicities * p[j] * p[k] * p[ell]
    payoff_values = (tensor @ weighted) / 4.0

    # Each unordered triple's derivative touches at most three coordinates.
    # Keep this matrix sparse: a dense n-by-triple tensor would make the
    # Jacobian product O(n^2 * number_of_triples) instead of O(n * triples).
    triple_count = len(triples)
    rows = np.repeat(np.arange(triple_count, dtype=np.int32), 3)
    cols = np.column_stack((j, k, ell)).ravel()
    data = np.column_stack((
        multiplicities * p[k] * p[ell],
        multiplicities * p[j] * p[ell],
        multiplicities * p[j] * p[k],
    )).ravel()
    derivative_weights = csr_matrix((data, (rows, cols)),
                                    shape=(triple_count, len(p)))
    jacobian = np.asarray(derivative_weights.T @ tensor.T).T / 4.0
    return payoff_values, jacobian


def optimize_restricted(actions, warm_start, *, restarts=4, seed=1, max_iterations=600):
    triples, multiplicities, tensor = payoff_tensor(actions)
    n = len(actions)
    rng = np.random.default_rng(seed)
    starts = []
    if warm_start is not None and len(warm_start) == n:
        candidate = np.maximum(warm_start, 0)
        starts.append(candidate / max(float(candidate.sum()), 1e-300))
    starts.append(np.full(n, 1.0 / n))
    while len(starts) < restarts:
        starts.append(rng.dirichlet(np.ones(n)))

    def utilities(z):
        return payoff_and_jacobian(z[:n], triples, multiplicities, tensor)

    def objective(z):
        return z[-1]

    def objective_jac(z):
        grad = np.zeros(n + 1)
        grad[-1] = 1.0
        return grad

    def normalization(z):
        return float(np.sum(z[:n]) - 1.0)

    def normalization_jac(_z):
        return np.r_[np.ones(n), 0.0]

    def security_constraints(z):
        return z[-1] - utilities(z)[0]

    def security_jac(z):
        return np.column_stack((-utilities(z)[1], np.ones(n)))

    solutions = []
    for start in starts:
        result = minimize(
            objective, np.r_[start, 9.0], jac=objective_jac, method="SLSQP",
            bounds=[(0.0, 1.0)] * n + [(0.0, 9.0)],
            constraints=[
                {"type": "eq", "fun": normalization, "jac": normalization_jac},
                {"type": "ineq", "fun": security_constraints, "jac": security_jac},
            ],
            options={"maxiter": max_iterations, "ftol": 1e-11, "disp": False},
        )
        p = np.maximum(result.x[:n], 0.0)
        if p.sum() <= 0:
            continue
        p /= p.sum()
        values, _ = payoff_and_jacobian(p, triples, multiplicities, tensor)
        score = float(np.max(values))
        if any(np.max(np.abs(p - old["probabilities"])) < 1e-5 for old in solutions):
            continue
        solutions.append({
            "probabilities": p,
            "restricted_best_payoff": score,
            "optimizer_success": bool(result.success),
            "optimizer_message": str(result.message),
            "optimizer_iterations": int(result.nit),
        })
    if not solutions:
        raise RuntimeError("all restricted nonlinear optimization starts failed")
    equilibria = [s for s in solutions if s["restricted_best_payoff"] <= VALUE + 1e-5]
    return equilibria or sorted(solutions, key=lambda s: s["restricted_best_payoff"])


def audit_full_action(actions, probabilities, *, frequency_total, threads, top_k):
    entries = {"actions": [list(a) for a in actions],
               "last_half_time_average_probabilities_decimal": [repr(float(p))
                                                                  for p in probabilities]}
    with tempfile.TemporaryDirectory(prefix="game2-minimax-audit-") as temp:
        population = Path(temp) / "mixture.json"
        report = Path(temp) / "audit.json"
        population.write_text(json.dumps(entries))
        runner = Path(__file__).with_name("run_exact_full_best_response.py")
        subprocess.run([
            sys.executable, str(runner), str(population),
            "--frequency-total", str(frequency_total), "--threads", str(threads),
            "--top-k", str(top_k), "--output", str(report),
        ], check=True, stdout=subprocess.DEVNULL)
        return json.loads(report.read_text())


def run(args):
    if args.resume and args.state.exists():
        state = json.loads(args.state.read_text())
        actions = [tuple(a) for a in state["actions"]]
        warm = np.asarray(state["probabilities"], dtype=float)
        history = state.get("history", [])
        best_gap = float(state.get("best_gap", 9.0))
        if args.prune_zero_support and len(warm) == len(actions):
            actions, warm = prune_pool_support(actions, warm, args.support_threshold)
        elif len(warm) == 0:
            warm = None
        previous_best = args.output_dir / "best.json"
        if previous_best.exists():
            previous_audit = json.loads(previous_best.read_text())["exact_oracle_audit"]
            best_gap = min(best_gap, previous_audit["certified_exploitability_upper_bound"])
    else:
        actions = load_actions(args.pool)
        warm = None
        if args.initial_mixture:
            data = json.loads(args.initial_mixture.read_text())
            initial_actions = data.get("actions", [])
            probabilities = data.get("last_half_time_average_probabilities_decimal",
                                    data.get("last_half_time_average_probabilities", []))
            warm_map = {tuple(a): float(p) for a, p in zip(initial_actions, probabilities)}
            warm = np.asarray([warm_map.get(a, 0.0) for a in actions])
        history = []
        best_gap = 9.0
    for raw in args.add_action:
        action = tuple(map(int, raw.split(",")))
        if len(action) != 5 or sum(action) != 100 or min(action) < 0:
            raise ValueError(f"invalid added action: {raw}")
        if action not in actions:
            actions.append(action)
            warm = np.r_[warm, 0.0] if warm is not None else None

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for iteration in range(args.max_rounds):
        solutions = optimize_restricted(actions, warm, restarts=args.restarts,
                                        seed=args.seed + iteration,
                                        max_iterations=args.optimizer_iterations)
        audited = []
        for solution in solutions[:args.audit_candidates]:
            audit = audit_full_action(actions, solution["probabilities"],
                                      frequency_total=args.frequency_total,
                                      threads=args.threads, top_k=args.oracle_top_k)
            audited.append((solution, audit))
        solution, audit = min(
            audited,
            key=lambda pair: pair[1]["certified_exploitability_upper_bound"],
        )
        round_best_gap = audit["certified_exploitability_upper_bound"]
        input_gap_upper = audit["input_mixture_certified_exploitability_upper_bound"]
        response = tuple(audit["best_response"])
        if args.prune_zero_support:
            next_actions, next_probabilities = prune_pool_support(
                actions, solution["probabilities"], args.support_threshold
            )
        else:
            next_actions = list(actions)
            next_probabilities = solution["probabilities"].copy()
        novel_responses = []
        # Add responses from several distinct restricted equilibria so the pool
        # is not steered by a single local basin. This is a search heuristic.
        for other_solution, other_audit in sorted(
                audited, key=lambda pair: pair[1]["certified_exploitability_upper_bound"]):
            for response_record in other_audit["top_responses"]:
                action = tuple(response_record["allocation"])
                if action not in next_actions and action not in novel_responses:
                    novel_responses.append(action)
                if len(novel_responses) >= args.add_responses_per_round:
                    break
            if len(novel_responses) >= args.add_responses_per_round:
                break
        candidate_summaries = []
        for other_solution, other_audit in audited:
            candidate_summaries.append({
                "restricted_best_payoff": other_solution["restricted_best_payoff"],
                "optimizer_success": other_solution["optimizer_success"],
                "quantized_support_size": other_audit["oracle_support_size"],
                "best_response": other_audit["best_response"],
                "full_action_payout": other_audit["expected_payout_decimal_on_oracle_mixture"],
                "certified_gap_lower": other_audit["input_mixture_certified_exploitability_lower_bound"],
                "certified_gap_upper": other_audit["input_mixture_certified_exploitability_upper_bound"],
                "rationalized_strategy_exact_gap": other_audit["certified_exploitability_upper_bound"],
            })
        record = {
            "iteration": iteration, "pool_size": len(actions),
            "distinct_restricted_equilibria_audited": len(audited),
            "restricted_best_payoff": solution["restricted_best_payoff"],
            "optimizer_success": solution["optimizer_success"],
            "restricted_support_size": int(np.count_nonzero(solution["probabilities"] > 1e-8)),
            "quantized_support_size": audit["oracle_support_size"],
            "full_action_best_response": list(response),
            "full_action_payout": audit["expected_payout_decimal_on_oracle_mixture"],
            "certified_gap_lower": audit["input_mixture_certified_exploitability_lower_bound"],
            "certified_gap_upper": input_gap_upper,
            "rationalized_strategy_exact_gap": round_best_gap,
            "rationalized_strategy_exact_gap_fraction": audit["certified_exploitability_upper_bound_fraction"],
            "added_response_actions": [list(a) for a in novel_responses],
            "candidate_equilibria": candidate_summaries,
        }
        if round_best_gap < best_gap:
            best_gap = round_best_gap
            args.output_dir.joinpath("best.json").write_text(json.dumps({
                "pool_actions": [list(a) for a in actions],
                "pool_probabilities": [float(p) for p in solution["probabilities"]],
                "exact_oracle_audit": audit,
                "rationalized_strategy_exact_gap": best_gap,
                "optimizer_input_gap_upper": input_gap_upper,
            }, indent=2) + "\n")
        record["best_gap_so_far"] = best_gap
        history.append(record)
        print(json.dumps(record), flush=True)
        mixture = {
            "method": "multistart restricted symmetric minimax plus exact full-action response expansion",
            "pool_actions": [list(a) for a in actions],
            "pool_probabilities": [float(p) for p in solution["probabilities"]],
            "exact_oracle_audit": audit,
            "candidate_equilibria_audited": candidate_summaries,
            "warning": "The restricted nonlinear optimizer is local. Only exact full-action response bounds certify a candidate; positive gaps are not equilibria.",
        }
        (args.output_dir / f"round-{iteration:03d}.json").write_text(
            json.dumps(mixture, indent=2) + "\n")
        warm = next_probabilities
        exact_candidate = round_best_gap <= args.exact_tolerance
        if not exact_candidate and novel_responses:
            next_actions.extend(novel_responses)
            warm = np.r_[warm, np.zeros(len(novel_responses))]
        elif not exact_candidate:
            warm = None
            record["all_responses_already_in_pool"] = True
        actions = next_actions
        args.state.write_text(json.dumps({"actions": [list(a) for a in actions],
                                          "probabilities": warm.tolist() if warm is not None else [],
                                          "history": history, "best_gap": best_gap}, indent=2) + "\n")
        if exact_candidate:
            record["exact_equilibrium_candidate"] = True
            break
    return {"rounds": len(history), "pool_size": len(actions),
            "best_gap": best_gap, "history": history, "state": str(args.state)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--initial-mixture", type=Path)
    parser.add_argument("--add-action", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--audit-candidates", type=int, default=4)
    parser.add_argument("--add-responses-per-round", type=int, default=4)
    parser.add_argument("--oracle-top-k", type=int, default=10)
    parser.add_argument("--optimizer-iterations", type=int, default=600)
    parser.add_argument("--frequency-total", type=int, default=1_000_000_000)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--exact-tolerance", type=float, default=0.0)
    parser.add_argument("--prune-zero-support", action="store_true",
                        help="keep only positive-mass restricted actions between rounds")
    parser.add_argument("--support-threshold", type=float, default=1e-8)
    args = parser.parse_args()
    if args.support_threshold < 0 or args.support_threshold >= 1:
        parser.error("support threshold must be in [0, 1)")
    print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
