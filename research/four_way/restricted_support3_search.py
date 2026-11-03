#!/usr/bin/env python3
"""Numerical symmetric-equilibrium search for supports of size at most three.

It solves the two cubic indifference equations on each 3-action support by
multi-start Newton, checks all omitted actions in the restricted pool, and
exactly audits any surviving rationalized candidate against the entire game.
Roots are numerical; this is candidate generation, not a proof-complete solver.
"""

from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from castle_challenges.games.four_way.rules import payout

FREQUENCY_TOTAL = 1_000_002


def load_pool(path: Path) -> list[tuple[int, ...]]:
    data = json.loads(path.read_text())
    entries = data.get("population", data.get("strategy"))
    if entries is None:
        raise ValueError("input needs a population or strategy")
    actions = []
    for entry in entries:
        raw = entry["allocation"] if isinstance(entry, dict) else entry[0]
        action = tuple(map(int, raw))
        if len(action) != 5 or sum(action) != 100 or min(action) < 0:
            raise ValueError(f"invalid allocation: {action}")
        if action not in actions:
            actions.append(action)
    return actions


def payoff_tensor(actions: list[tuple[int, ...]]):
    n = len(actions)
    return [[[[round(4 * payout((actions[i], actions[j], actions[k], actions[l]))[0])
               for l in range(n)] for k in range(n)] for j in range(n)]
            for i in range(n)]


def payoff(tensor, action: int, support: tuple[int, int, int], p) -> float:
    total = 0.0
    for j in range(3):
        for k in range(3):
            for l in range(3):
                total += (tensor[action][support[j]][support[k]][support[l]]
                          * p[j] * p[k] * p[l])
    return total / 4.0


def payoff_derivative(tensor, action: int, support: tuple[int, int, int],
                      p, direction) -> float:
    total = 0.0
    for changed in range(3):
        for j in range(3):
            for k in range(3):
                total += (3 * tensor[action][support[changed]][support[j]][support[k]]
                          * direction[changed] * p[j] * p[k])
    return total / 4.0


def _system(tensor, support, x, y):
    p = (x, y, 1.0 - x - y)
    f = (payoff(tensor, support[0], support, p)
         - payoff(tensor, support[1], support, p),
         payoff(tensor, support[0], support, p)
         - payoff(tensor, support[2], support, p))
    directions = ((1.0, 0.0, -1.0), (0.0, 1.0, -1.0))
    jacobian = []
    for left, right in ((support[0], support[1]), (support[0], support[2])):
        jacobian.append([
            payoff_derivative(tensor, left, support, p, direction)
            - payoff_derivative(tensor, right, support, p, direction)
            for direction in directions
        ])
    return f, jacobian, p


def newton_root(tensor, support, x, y, tolerance=1e-9):
    for _ in range(80):
        f, j, p = _system(tensor, support, x, y)
        norm = max(abs(f[0]), abs(f[1]))
        if norm < tolerance:
            return (x, y, p[2]) if min(p) > 1e-7 else None
        det = j[0][0] * j[1][1] - j[0][1] * j[1][0]
        if abs(det) < 1e-13:
            return None
        dx = (f[0] * j[1][1] - f[1] * j[0][1]) / det
        dy = (j[0][0] * f[1] - j[1][0] * f[0]) / det
        step = 1.0
        accepted = False
        while step > 1e-5:
            nx, ny = x - step * dx, y - step * dy
            np = (nx, ny, 1 - nx - ny)
            if min(np) < -0.25 or max(np) > 1.25:
                step *= 0.5
                continue
            nf, _, _ = _system(tensor, support, nx, ny)
            if max(abs(nf[0]), abs(nf[1])) < norm:
                x, y = nx, ny
                accepted = True
                break
            step *= 0.5
        if not accepted:
            return None
    f, _, p = _system(tensor, support, x, y)
    if max(abs(f[0]), abs(f[1])) < tolerance and min(p) > 1e-7:
        return p
    return None


def _quantize(probabilities, total):
    scaled = [max(0.0, p) * total / sum(probabilities) for p in probabilities]
    counts = [int(p) for p in scaled]
    for i in sorted(range(len(counts)), key=lambda j: scaled[j] - counts[j],
                    reverse=True)[:total - sum(counts)]:
        counts[i] += 1
    return counts


def exact_audit(actions, weights, binary):
    payload = [str(len(actions))]
    payload.extend("{} {}".format(" ".join(map(str, action)), weight)
                   for action, weight in zip(actions, weights) if weight)
    output = subprocess.run([str(binary), "1"], input="\n".join(payload) + "\n",
                            text=True, capture_output=True, check=True).stdout.strip()
    response, numerator, denominator, _ = output.split("\t")
    from fractions import Fraction
    gap = Fraction(int(numerator), int(denominator)) - Fraction(15, 4)
    return tuple(map(int, response.split(","))), gap


def search(path: Path, *, max_actions: int = 12, grid_denominator: int = 8) -> dict:
    pool = load_pool(path)
    if len(pool) > max_actions:
        raise ValueError(f"pool size {len(pool)} exceeds limit {max_actions}")
    tensor = payoff_tensor(pool)
    roots = []
    restricted_equilibria = []
    for support in combinations(range(len(pool)), 3):
        seen = []
        for i in range(1, grid_denominator):
            x = i / grid_denominator
            for j in range(1, grid_denominator - i):
                y = j / grid_denominator
                p = newton_root(tensor, support, x, y)
                if p is None or any(max(abs(p[z] - q[z]) for z in range(3)) < 1e-6
                                    for q in seen):
                    continue
                seen.append(p)
                roots.append((support, p))
                values = [payoff(tensor, action, support, p)
                          for action in range(len(pool))]
                if max(values) <= 15 / 4 + 2e-6:
                    restricted_equilibria.append((support, p, max(values)))

    if not restricted_equilibria:
        return {
            "method": "support-three multi-start Newton with restricted-pool checks",
            "pool_file": str(path), "pool_size": len(pool),
            "roots_found": len(roots), "restricted_equilibria_found": 0,
            "grid_denominator": grid_denominator,
            "warning": "Numerical multi-start search; no support-three restricted equilibrium was found. Supports larger than three are not searched.",
        }

    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("a C++17 compiler is required for exact full-action audits")
    source = Path(__file__).with_name("exact_full_action_best_response.cpp")
    audits = []
    with tempfile.TemporaryDirectory(prefix="four-way-support3-") as temp:
        binary = Path(temp) / "oracle"
        subprocess.run([compiler, "-O3", "-std=c++17", "-pthread", str(source), "-o", str(binary)],
                       check=True, stdout=subprocess.DEVNULL)
        for support, p, restricted_value in restricted_equilibria:
            actions = tuple(pool[i] for i in support)
            weights = _quantize(p, FREQUENCY_TOTAL)
            response, gap = exact_audit(actions, weights, binary)
            audits.append({
                "support": [[list(action), weight]
                            for action, weight in zip(actions, weights) if weight],
                "restricted_max_payoff": restricted_value,
                "best_response": list(response),
                "exploitability_fraction": [gap.numerator, gap.denominator],
                "exploitability": float(gap),
            })
    audits.sort(key=lambda item: item["exploitability"])
    return {
        "method": "support-three numerical Newton roots + exact full-action audit",
        "pool_file": str(path), "pool_size": len(pool),
        "roots_found": len(roots),
        "restricted_equilibria_found": len(restricted_equilibria),
        "grid_denominator": grid_denominator,
        "frequency_total": FREQUENCY_TOTAL,
        "best_candidate": audits[0],
        "candidates": audits,
        "warning": "Roots and restricted inequalities use floating point; the exact exploitability applies only to each rationalized mixture. Supports larger than three are not searched.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--grid-denominator", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = search(args.pool, max_actions=args.max_actions,
                    grid_denominator=args.grid_denominator)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result.get("best_candidate", result), indent=2))


if __name__ == "__main__":
    main()
