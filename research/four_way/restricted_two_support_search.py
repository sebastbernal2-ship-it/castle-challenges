#!/usr/bin/env python3
"""Enumerate symmetric equilibria with support at most two in a finite pool.

For a two-action support, the indifference equation is cubic in x, the
probability of action 0. Roots are isolated numerically, rationalized to an
integer-frequency mixture, then audited by the exact full-action oracle.
This is candidate search, not an algebraic certificate: the exact oracle
certifies the rationalized mixture's global deviation gap.
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
_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []
BERNSTEIN_TO_POWER = (
    (1, -3, 3, -1),
    (0, 3, -6, 3),
    (0, 0, 3, -3),
    (0, 0, 0, 1),
)


def _load_pool(path: Path) -> list[tuple[int, ...]]:
    data = json.loads(path.read_text())
    entries = data.get("strategy", data.get("population"))
    if entries is None:
        raise ValueError("input needs a strategy or population list")
    actions = []
    for entry in entries:
        action = entry[0] if isinstance(entry, list) else entry["allocation"]
        action = tuple(map(int, action))
        if len(action) != 5 or sum(action) != 100 or min(action) < 0:
            raise ValueError(f"invalid allocation: {action}")
        actions.append(action)
    return list(dict.fromkeys(actions))


def _indifference_polynomial(a: tuple[int, ...], b: tuple[int, ...]
                             ) -> tuple[int, int, int, int]:
    """Power-basis coefficients of E[U(a,opp,opp,opp)]-E[U(b,...)] in 4x units."""
    bernstein = []
    for zeros in range(4):
        opponents = (a,) * zeros + (b,) * (3 - zeros)
        ua = round(4 * payout((a, *opponents))[0])
        ub = round(4 * payout((b, *opponents))[0])
        bernstein.append(ua - ub)
    coeff = [0, 0, 0, 0]
    for m, value in enumerate(bernstein):
        for degree, basis_coeff in enumerate(BERNSTEIN_TO_POWER[m]):
            coeff[degree] += value * basis_coeff
    return tuple(coeff)


def _poly_value(coeff: tuple[int, ...], x: float) -> float:
    return ((coeff[3] * x + coeff[2]) * x + coeff[1]) * x + coeff[0]


def _roots_unit_interval(coeff: tuple[int, int, int, int]) -> list[float]:
    """Isolate every real cubic root in [0,1] by derivative partitioning."""
    import math

    scale = max(1, *(abs(c) for c in coeff))
    tol = 1e-12 * scale
    if not any(coeff):
        return [1 / 3, 0.5, 2 / 3]
    _, c1, c2, c3 = coeff
    critical = []
    if c3:
        disc = (2 * c2) ** 2 - 12 * c3 * c1
        if disc >= 0:
            root = math.sqrt(disc)
            critical = [(-2 * c2 - root) / (6 * c3),
                        (-2 * c2 + root) / (6 * c3)]
    elif c2:
        critical = [-c1 / (2 * c2)]
    points = [0.0] + sorted(x for x in critical if 0 < x < 1) + [1.0]
    roots = []
    for point in points:
        if abs(_poly_value(coeff, point)) <= tol:
            roots.append(point)
    for left, right in zip(points, points[1:]):
        fl, fr = _poly_value(coeff, left), _poly_value(coeff, right)
        if fl * fr >= 0:
            continue
        lo, hi = left, right
        for _ in range(80):
            mid = (lo + hi) / 2
            fm = _poly_value(coeff, mid)
            if fm == 0:
                lo = hi = mid
                break
            if fl * fm < 0:
                hi, fr = mid, fm
            else:
                lo, fl = mid, fm
        roots.append((lo + hi) / 2)
    unique = []
    for root in sorted(roots):
        if not unique or abs(root - unique[-1]) > 1e-8:
            unique.append(root)
    return unique


def _compile_oracle() -> Path:
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("a C++17 compiler is required")
    source = Path(__file__).with_name("exact_full_action_best_response.cpp")
    temp = tempfile.TemporaryDirectory(prefix="four-way-support-search-")
    _TEMP_DIRS.append(temp)
    binary = Path(temp.name) / "oracle"
    subprocess.run([compiler, "-O3", "-std=c++17", "-pthread", str(source), "-o", str(binary)],
                   check=True, stdout=subprocess.DEVNULL)
    return binary


def _audit(binary: Path, actions: tuple[tuple[int, ...], ...],
           weights: tuple[int, ...]) -> tuple[tuple[int, ...], int, int]:
    lines = [str(len(actions))]
    lines.extend("{} {}".format(" ".join(map(str, action)), weight)
                 for action, weight in zip(actions, weights) if weight)
    output = subprocess.run([str(binary), "1"], input="\n".join(lines) + "\n",
                            text=True, capture_output=True, check=True).stdout.strip()
    response, numerator, denominator, _ = output.split("\t")
    return tuple(map(int, response.split(","))), int(numerator), int(denominator)


def search(pool_file: Path, *, max_actions: int = 40,
           output_file: Path | None = None) -> dict:
    from fractions import Fraction

    pool = _load_pool(pool_file)
    if len(pool) > max_actions:
        raise ValueError(f"pool has {len(pool)} actions; limit is {max_actions}")
    binary = _compile_oracle()
    candidates = []
    support_specs: list[tuple[tuple[int, ...], tuple[int, ...], float]] = []
    for action in pool:
        support_specs.append(((action,), (FREQUENCY_TOTAL,), 1.0))
    for a, b in combinations(pool, 2):
        for x in _roots_unit_interval(_indifference_polynomial(a, b)):
            if 1e-9 < x < 1 - 1e-9:
                count_a = round(x * FREQUENCY_TOTAL)
                if 0 < count_a < FREQUENCY_TOTAL:
                    support_specs.append(((a, b),
                                         (count_a, FREQUENCY_TOTAL - count_a), x))
    seen = set()
    best = None
    for actions, weights, root in support_specs:
        key = (actions, weights)
        if key in seen:
            continue
        seen.add(key)
        response, numerator, denominator = _audit(binary, actions, weights)
        gap = Fraction(numerator, denominator) - Fraction(15, 4)
        candidate = {
            "support": [[list(a), w] for a, w in zip(actions, weights) if w],
            "indifference_root_probability_action_0": root,
            "best_response": list(response),
            "best_response_payout_fraction": [numerator, denominator],
            "exploitability_fraction": [gap.numerator, gap.denominator],
            "exploitability": float(gap),
        }
        candidates.append(candidate)
        if best is None or gap < best[0]:
            best = (gap, candidate, actions, weights)
    candidates.sort(key=lambda item: (item["exploitability"], item["support"]))
    assert best is not None
    result = {
        "method": "support-at-most-two numerical indifference roots + exact full-action audit",
        "pool_file": str(pool_file),
        "pool_size": len(pool),
        "frequency_total": FREQUENCY_TOTAL,
        "candidate_count": len(candidates),
        "best_candidate": best[1],
        "top_candidates": candidates[:20],
        "warning": "Root isolation is floating-point; exploitability is exact for each rationalized mixture, not an equilibrium proof.",
    }
    if output_file:
        output_file.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("--max-actions", type=int, default=40)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = search(args.pool, max_actions=args.max_actions, output_file=args.output)
    print(json.dumps(result["best_candidate"], indent=2))


if __name__ == "__main__":
    main()
