#!/usr/bin/env python3
"""Numerically search symmetric restricted equilibria on four-action supports.

For each four-action support, solve three cubic indifference equations with
multi-start Newton, check all pool deviations, then exact-audit survivors in
the full action space. This remains a candidate search, not a complete solver.
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


def payoff_tensor(actions):
    n = len(actions)
    return [[[[round(4 * payout((actions[i], actions[j], actions[k], actions[l]))[0])
               for l in range(n)] for k in range(n)] for j in range(n)]
            for i in range(n)]


def expected_payoff(tensor, action, support, p):
    k = len(support)
    total = 0.0
    for j in range(k):
        for l in range(k):
            for m in range(k):
                total += (tensor[action][support[j]][support[l]][support[m]]
                          * p[j] * p[l] * p[m])
    return total / 4


def derivative(tensor, action, support, p, direction):
    k = len(support)
    total = 0.0
    for changed in range(k):
        for j in range(k):
            for l in range(k):
                total += (3 * tensor[action][support[changed]][support[j]][support[l]]
                          * direction[changed] * p[j] * p[l])
    return total / 4


def _system(tensor, support, x):
    k = len(support)
    p = tuple(x) + (1.0 - sum(x),)
    f = [expected_payoff(tensor, support[0], support, p)
         - expected_payoff(tensor, support[i], support, p)
         for i in range(1, k)]
    directions = []
    for d in range(k - 1):
        direction = [0.0] * k
        direction[d] = 1.0
        direction[-1] = -1.0
        directions.append(tuple(direction))
    jacobian = []
    for i in range(1, k):
        jacobian.append([
            derivative(tensor, support[0], support, p, direction)
            - derivative(tensor, support[i], support, p, direction)
            for direction in directions
        ])
    return f, jacobian, p


def _solve_linear(matrix, vector):
    n = len(vector)
    a = [list(matrix[i]) + [vector[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= scale
        for row in range(n):
            if row == col:
                continue
            scale = a[row][col]
            for j in range(col, n + 1):
                a[row][j] -= scale * a[col][j]
    return [a[i][n] for i in range(n)]


def newton_root(tensor, support, start, tolerance=1e-9):
    x = list(start)
    k = len(support)
    for _ in range(80):
        f, jacobian, p = _system(tensor, support, x)
        norm = max(map(abs, f))
        if norm < tolerance:
            return p if min(p) > 1e-7 else None
        step_vector = _solve_linear(jacobian, f)
        if step_vector is None:
            return None
        scale = 1.0
        accepted = False
        while scale > 1e-5:
            candidate = [x[d] - scale * step_vector[d] for d in range(k - 1)]
            cp = candidate + [1 - sum(candidate)]
            if min(cp) < -0.25 or max(cp) > 1.25:
                scale *= 0.5
                continue
            candidate_f, _, _ = _system(tensor, support, candidate)
            if max(map(abs, candidate_f)) < norm:
                x = candidate
                accepted = True
                break
            scale *= 0.5
        if not accepted:
            return None
    f, _, p = _system(tensor, support, x)
    return p if max(map(abs, f)) < tolerance and min(p) > 1e-7 else None


def _grid_points(k, denominator):
    def visit(prefix, remaining, slots):
        if slots == 1:
            if remaining >= 1:
                yield tuple(prefix + [remaining])
            return
        for value in range(1, remaining - slots + 2):
            yield from visit(prefix + [value], remaining - value, slots - 1)

    for total in range(k, denominator):
        for integer_parts in visit([], total, k):
            yield tuple(part / denominator for part in integer_parts[:-1])


def _quantize(p, total):
    scaled = [max(0.0, x) * total / sum(p) for x in p]
    counts = [int(x) for x in scaled]
    order = sorted(range(len(p)), key=lambda i: scaled[i] - counts[i], reverse=True)
    for i in order[:total - sum(counts)]:
        counts[i] += 1
    return counts


def _exact_audit(actions, weights, binary):
    payload = [str(len(actions))]
    payload.extend("{} {}".format(" ".join(map(str, action)), weight)
                   for action, weight in zip(actions, weights) if weight)
    output = subprocess.run([str(binary), "1"], input="\n".join(payload) + "\n",
                            text=True, capture_output=True, check=True).stdout.strip()
    response, numerator, denominator, _ = output.split("\t")
    from fractions import Fraction
    gap = Fraction(int(numerator), int(denominator)) - Fraction(15, 4)
    return tuple(map(int, response.split(","))), gap


def search(path: Path, *, max_actions=10, grid_denominator=8):
    pool = load_pool(path)
    if len(pool) > max_actions:
        raise ValueError(f"pool size {len(pool)} exceeds limit {max_actions}")
    tensor = payoff_tensor(pool)
    roots_found = 0
    equilibria = []
    for support in combinations(range(len(pool)), 4):
        seen = []
        for start in _grid_points(4, grid_denominator):
            p = newton_root(tensor, support, start)
            if p is None or any(max(abs(p[i] - q[i]) for i in range(4)) < 1e-6
                                for q in seen):
                continue
            seen.append(p)
            roots_found += 1
            values = [expected_payoff(tensor, a, support, p)
                      for a in range(len(pool))]
            if max(values) <= 15 / 4 + 2e-6:
                equilibria.append((support, p, max(values)))

    result = {
        "method": "support-four multistart Newton, restricted-pool check, exact full-action audit",
        "pool_file": str(path), "pool_size": len(pool),
        "roots_found": roots_found,
        "restricted_equilibria_found": len(equilibria),
        "grid_denominator": grid_denominator,
    }
    if not equilibria:
        result["warning"] = "Numerical multistart search; no support-four restricted equilibrium found. This is not a proof of nonexistence."
        return result

    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("a C++17 compiler is required")
    source = Path(__file__).with_name("exact_full_action_best_response.cpp")
    audits = []
    with tempfile.TemporaryDirectory(prefix="four-way-support4-") as temp:
        binary = Path(temp) / "oracle"
        subprocess.run([compiler, "-O3", "-std=c++17", "-pthread", str(source), "-o", str(binary)],
                       check=True, stdout=subprocess.DEVNULL)
        for support, p, restricted_value in equilibria:
            actions = tuple(pool[i] for i in support)
            weights = _quantize(p, FREQUENCY_TOTAL)
            response, gap = _exact_audit(actions, weights, binary)
            audits.append({
                "support": [[list(a), w] for a, w in zip(actions, weights) if w],
                "restricted_max_payoff": restricted_value,
                "best_response": list(response),
                "exploitability_fraction": [gap.numerator, gap.denominator],
                "exploitability": float(gap),
            })
    audits.sort(key=lambda item: item["exploitability"])
    result.update({"frequency_total": FREQUENCY_TOTAL,
                   "best_candidate": audits[0], "candidates": audits,
                   "warning": "Roots are numerical and only the rationalized mixture's deviation gap is exact."})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--max-actions", type=int, default=10)
    parser.add_argument("--grid-denominator", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = search(args.pool, max_actions=args.max_actions,
                    grid_denominator=args.grid_denominator)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result.get("best_candidate", result), indent=2))


if __name__ == "__main__":
    main()
