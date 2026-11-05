#!/usr/bin/env python3
"""Continuation/column-generation experiment for Game 2's auxiliary game.

At a fixed homotopy parameter t, solve the restricted symmetric minimax game,
then use an exact full-action auxiliary best-response oracle to add entering
allocations. This is an equilibrium-path experiment, not a global certificate
for the target game; a t=1 endpoint still requires the ordinary exact audit.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from run_exact_auxiliary_best_response import action_cost
from symmetric_minimax_expansion import payoff_and_jacobian, payoff_tensor

A0 = (20, 20, 20, 20, 20)
A1 = (19, 20, 20, 20, 21)
VALUE = 15.0 / 4.0


def optimize_auxiliary(actions, costs, t: float, warm, iterations: int):
    triples, multiplicities, tensor = payoff_tensor(actions)
    n = len(actions)

    def utility(p):
        target, jacobian = payoff_and_jacobian(p, triples, multiplicities, tensor)
        expected_cost = float(costs @ p)
        values = (1.0 - t) * (VALUE - costs + expected_cost) + t * target
        jac = t * jacobian + (1.0 - t) * np.broadcast_to(costs, (n, n))
        return values, jac

    def constraint(z):
        return z[-1] - utility(z[:n])[0]

    def constraint_jac(z):
        return np.column_stack((-utility(z[:n])[1], np.ones(n)))

    start = np.maximum(np.asarray(warm, dtype=float), 0.0)
    start /= start.sum()
    result = minimize(
        lambda z: z[-1], np.r_[start, 9.0],
        jac=lambda _z: np.r_[np.zeros(n), 1.0], method="SLSQP",
        bounds=[(0.0, 1.0)] * n + [(0.0, 9.0)],
        constraints=[
            {"type": "eq", "fun": lambda z: float(z[:n].sum() - 1.0),
             "jac": lambda _z: np.r_[np.ones(n), 0.0]},
            {"type": "ineq", "fun": constraint, "jac": constraint_jac},
        ],
        options={"maxiter": iterations, "ftol": 1e-11, "disp": False},
    )
    p = np.maximum(result.x[:n], 0.0)
    p /= p.sum()
    values, _ = utility(p)
    return p, float(np.max(values)), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t-num", type=int, required=True)
    parser.add_argument("--t-den", type=int, default=1000)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--add-per-round", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--frequency-total", type=int, default=1_000_000)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pool", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=800)
    args = parser.parse_args()
    if not 0 <= args.t_num <= args.t_den <= 1_000_000:
        parser.error("require 0 <= t-num <= t-den <= 1,000,000")
    t_fraction = Fraction(args.t_num, args.t_den)
    t = float(t_fraction)
    if args.pool:
        raw = json.loads(args.pool.read_text())
        actions = [tuple(map(int, a)) for a in raw["actions"]]
    else:
        actions = [A0, A1]
    actions = list(dict.fromkeys(actions))
    warm = np.full(len(actions), 1.0 / len(actions))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for round_id in range(args.rounds):
        costs = np.asarray([float(action_cost(a)) for a in actions])
        p, restricted_max, result = optimize_auxiliary(
            actions, costs, t, warm, args.iterations
        )
        keep = p > 1e-9
        support = [a for a, active in zip(actions, keep) if active]
        probabilities = p[keep]
        probabilities /= probabilities.sum()
        mix = {
            "actions": [list(a) for a in support],
            "last_half_time_average_probabilities_decimal": [repr(float(q)) for q in probabilities],
        }
        temp = args.output_dir / f"mixture-{round_id:03d}.json"
        temp.write_text(json.dumps(mix, indent=2) + "\n")
        import subprocess, sys
        audit_path = args.output_dir / f"auxiliary-audit-{round_id:03d}.json"
        subprocess.run([
            sys.executable, str(Path(__file__).with_name("run_exact_auxiliary_best_response.py")),
            str(temp), "--t-num", str(args.t_num), "--t-den", str(args.t_den),
            "--frequency-total", str(args.frequency_total), "--threads", str(args.threads),
            "--top-k", str(args.top_k), "--output", str(audit_path),
        ], check=True, stdout=subprocess.DEVNULL)
        audit = json.loads(audit_path.read_text())
        top = audit["top_responses"]
        best = top[0]
        gap = best["auxiliary_payout"] - VALUE
        record = {
            "t_fraction": [args.t_num, args.t_den],
            "pool_actions": [list(a) for a in actions],
            "active_actions": [list(a) for a in support],
            "probabilities": probabilities.tolist(),
            "restricted_auxiliary_max": restricted_max,
            "optimizer_success": bool(result.success),
            "optimizer_message": str(result.message),
            "exact_auxiliary_audit": audit,
            "best_response_auxiliary_gap": gap,
            "method": "restricted auxiliary minimax with exact full-action separation",
            "warning": "not a target-game equilibrium certificate unless t=1 and gap is zero",
        }
        (args.output_dir / f"round-{round_id:03d}.json").write_text(
            json.dumps(record, indent=2) + "\n"
        )
        print(
            f"round={round_id} pool={len(actions)} support={len(support)} "
            f"restricted={restricted_max:.10f} exact_aux_gap={gap:.10f} "
            f"response={best['allocation']}", flush=True
        )
        if gap <= 1e-7:
            print("auxiliary full-game separation closed at this t")
            break
        additions = []
        for response in top:
            action = tuple(response["allocation"])
            if action not in actions and action not in additions:
                additions.append(action)
            if len(additions) >= args.add_per_round:
                break
        if not additions:
            print("no new actions in exact top-response list; stopping")
            break
        # Retain the current equilibrium support and add the highest auxiliary
        # responses. Inactive historical columns are safely rechecked by oracle.
        actions = list(dict.fromkeys(support + additions))
        warm = np.r_[probabilities, np.zeros(len(actions) - len(support))]


if __name__ == "__main__":
    main()
