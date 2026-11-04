#!/usr/bin/env python3
"""Build exact payoff-vector classes for responses to a small fixed support.

Two allocations outside the supplied support are equivalent iff they pay
identically against every unordered triple from that support. This is an exact
quotient for all omitted pure responses to every mixture over that support. It
is not a quotient of opponent actions; when the support changes, rebuild it.
"""
from __future__ import annotations

import itertools
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SOURCE = Path(__file__).with_name("response_equivalence_classes.cpp")
BINARY = Path(tempfile.gettempdir()) / "castle-game2-response-classes"


@dataclass(frozen=True)
class ResponseClasses:
    support: tuple[tuple[int, ...], ...]
    triples: tuple[tuple[int, int, int], ...]
    representatives: tuple[tuple[int, ...], ...]
    class_sizes: tuple[int, ...]
    payouts_quarters: np.ndarray  # class x unordered opponent triple


def build_response_classes(support) -> ResponseClasses:
    """Enumerate all omitted legal actions once and quotient their exact response rows.

    The current native implementation supports opponent supports of size at
    most nine (at most 165 unordered triples). It is especially effective for
    early support sizes: the four-million-action game can collapse to hundreds
    or a few thousand payoff vectors.
    """
    actions = tuple(tuple(map(int, a)) for a in support)
    if not 1 <= len(actions) <= 9:
        raise ValueError("response classes support sizes 1..9")
    if len(set(actions)) != len(actions):
        raise ValueError("support actions must be distinct")
    if any(len(a) != 5 or min(a) < 0 or sum(a) != 100 for a in actions):
        raise ValueError("every support allocation must be legal")
    if not BINARY.exists() or BINARY.stat().st_mtime < SOURCE.stat().st_mtime:
        subprocess.run(["c++", "-O3", "-std=c++17", str(SOURCE), "-o", str(BINARY)],
                       check=True, stdout=subprocess.DEVNULL)
    triples = tuple((i, j, k) for i in range(len(actions))
                    for j in range(i, len(actions))
                    for k in range(j, len(actions)))
    input_text = str(len(actions)) + "\n" + "".join(
        " ".join(map(str, a)) + "\n" for a in actions
    )
    result = subprocess.run([str(BINARY)], input=input_text, text=True,
                            check=True, capture_output=True)
    lines = result.stdout.splitlines()
    class_count, scenario_count = map(int, lines[0].split())
    if scenario_count != len(triples) or len(lines) != class_count + 1:
        raise RuntimeError("malformed native response-class output")
    reps, sizes, rows = [], [], []
    for line in lines[1:]:
        fields = list(map(int, line.split()))
        reps.append(tuple(fields[:5]))
        sizes.append(fields[5])
        rows.append(fields[6:])
    return ResponseClasses(actions, triples, tuple(reps), tuple(sizes),
                           np.asarray(rows, dtype=np.uint8))


def exact_top_responses(classes: ResponseClasses, frequencies, *, top_k=10):
    """Rank class representatives exactly for integer-frequency mixtures.

    Returns `(allocation, numerator, denominator, class_size)` rows. Payouts
    are in dollars with denominator `4 * total_frequency**3`; the numerators
    are Python integers, so ranking is exact.
    """
    frequencies = tuple(map(int, frequencies))
    if len(frequencies) != len(classes.support) or min(frequencies) < 0:
        raise ValueError("frequency vector must match support and be nonnegative")
    total = sum(frequencies)
    if total <= 0:
        raise ValueError("frequency total must be positive")
    scenario_weights = []
    for i, j, k in classes.triples:
        multiplicity = 1 if i == k else 3 if i == j or j == k else 6
        scenario_weights.append(multiplicity * frequencies[i] * frequencies[j] * frequencies[k])
    numerators = [sum(int(pay) * weight
                      for pay, weight in zip(row, scenario_weights))
                  for row in classes.payouts_quarters]
    order = sorted(range(len(numerators)), key=lambda i: (-numerators[i],
                                                           classes.representatives[i]))
    denominator = 4 * total**3
    return [(classes.representatives[i], numerators[i], denominator,
             classes.class_sizes[i]) for i in order[:top_k]]


def top_responses(classes: ResponseClasses, probabilities, *, top_k=10):
    """Floating-point counterpart for continuation/prediction steps."""
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if probabilities.shape != (len(classes.support),) or np.any(probabilities < 0):
        raise ValueError("probability vector must match support and be nonnegative")
    if not np.isclose(probabilities.sum(), 1.0):
        raise ValueError("probabilities must sum to one")
    weights = []
    for i, j, k in classes.triples:
        multiplicity = 1 if i == k else 3 if i == j or j == k else 6
        weights.append(multiplicity * probabilities[i] * probabilities[j] * probabilities[k])
    values = classes.payouts_quarters @ np.asarray(weights) / 4.0
    order = sorted(range(len(values)), key=lambda i: (-values[i],
                                                       classes.representatives[i]))
    return [(classes.representatives[i], float(values[i]), classes.class_sizes[i])
            for i in order[:top_k]]
