"""Exact dynamic-programming best response for Game 1 mixtures."""

from collections.abc import Mapping
import ctypes
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

from ...common.allocation import Allocation, SOLDIERS, VALUES, validate

_FAST_LIBRARY = None
_FAST_COUNT_LIBRARY = None
_FAST_CHECKED = False


def payoff_tables(opponent: Mapping[Allocation, float], soldiers: int = SOLDIERS
                  ) -> tuple[tuple[float, ...], ...]:
    """Return q[castle][x] expected castle score for assigning x soldiers.

    `opponent` maps legal allocations to nonnegative probability mass. Weights
    are normalized internally, so any positive finite total mass is accepted.
    """
    if not opponent:
        raise ValueError("opponent distribution must not be empty")
    total = 0.0
    marginals = [[0.0] * (soldiers + 1) for _ in VALUES]
    for allocation, weight in opponent.items():
        validate(allocation, soldiers)
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("probability weights must be finite and nonnegative")
        total += weight
        for i, soldiers_at_castle in enumerate(allocation):
            marginals[i][soldiers_at_castle] += weight
    if total <= 0:
        raise ValueError("opponent distribution must have positive total mass")

    tables = []
    for i, value in enumerate(VALUES):
        cumulative = 0.0
        row = []
        for x, mass in enumerate(marginals[i]):
            row.append(value * (cumulative + mass / 2) / total)
            cumulative += mass
        tables.append(tuple(row))
    return tuple(tables)


def best_response(opponent: Mapping[Allocation, float], soldiers: int = SOLDIERS
                 ) -> tuple[Allocation, float]:
    """Return a pure allocation maximizing expected score against a mixture.

    The dynamic program is exact up to floating-point arithmetic. The returned
    value is the expected score (whose game value is 7.5 in equilibrium).
    """
    return _solve_tables(payoff_tables(opponent, soldiers), soldiers)


def best_response_from_counts(counts: tuple[list[int], ...], soldiers: int = SOLDIERS
                              ) -> tuple[Allocation, int, int]:
    """Exact-integer best response to integer opponent marginal frequencies.

    Returns `(allocation, score_numerator, denominator)`, where score is the
    fraction numerator/denominator and denominator is twice the population size.
    Castle payoff tables and max-plus DP use integer arithmetic throughout.
    """
    if len(counts) != 5 or soldiers > 100 or soldiers < 0:
        raise ValueError("need five marginal count histograms and 0 <= soldiers <= 100")
    totals = []
    for row in counts:
        if len(row) != soldiers + 1 or any(type(x) is not int or x < 0 for x in row):
            raise ValueError("invalid integer marginal counts")
        totals.append(sum(row))
    if not totals[0] or any(total != totals[0] for total in totals):
        raise ValueError("each marginal must have the same positive total count")
    function = _compiled_count_function()
    if function is None:
        # Exact integer fallback, used only for final certificates / small tests.
        dp = [[None] * (soldiers + 1) for _ in range(6)]
        choice = [[0] * (soldiers + 1) for _ in range(6)]
        dp[0][0] = 0
        for i in range(1, 6):
            row = counts[i - 1]
            cumulative = 0
            q = []
            for mass in row:
                q.append(i * (2 * cumulative + mass))
                cumulative += mass
            for used in range(soldiers + 1):
                for x in range(used + 1):
                    previous = dp[i - 1][used - x]
                    if previous is None:
                        continue
                    candidate = previous + q[x]
                    if dp[i][used] is None or candidate > dp[i][used]:
                        dp[i][used] = candidate
                        choice[i][used] = x
        allocation = [0] * 5
        remaining = soldiers
        for i in range(5, 0, -1):
            allocation[i - 1] = choice[i][remaining]
            remaining -= allocation[i - 1]
        return tuple(allocation), dp[5][soldiers], 2 * totals[0]  # type: ignore[return-value]

    flat = []
    for row in counts:
        flat.extend(row)
        flat.extend([0] * (101 - len(row)))
    array = (ctypes.c_int64 * 505)(*flat)
    numerator = ctypes.c_int64()
    allocation = (ctypes.c_int * 5)()
    function(array, soldiers, ctypes.byref(numerator), allocation)
    return tuple(allocation), numerator.value, 2 * totals[0]  # type: ignore[return-value]


def best_response_from_marginals(marginals: tuple[list[float], ...], total_mass: float,
                                 soldiers: int = SOLDIERS) -> tuple[Allocation, float]:
    """Exact best response from per-castle opponent soldier-count histograms.

    Each marginal histogram must have the same total `total_mass`. This avoids
    rescanning a large empirical strategy support when only a few counts change.
    """
    if len(marginals) != 5 or total_mass <= 0 or not math.isfinite(total_mass):
        raise ValueError("need five marginal histograms and positive finite total mass")
    tables = []
    for i, value in enumerate(VALUES):
        if len(marginals[i]) != soldiers + 1 or any(
                not math.isfinite(x) or x < 0 for x in marginals[i]):
            raise ValueError("invalid marginal histogram")
        if not math.isclose(sum(marginals[i]), total_mass, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError("marginal histogram masses must equal total_mass")
        cumulative = 0.0
        row = []
        for mass in marginals[i]:
            row.append(value * (cumulative + mass / 2) / total_mass)
            cumulative += mass
        tables.append(tuple(row))
    return _solve_tables(tuple(tables), soldiers)


def _solve_tables(tables: tuple[tuple[float, ...], ...], soldiers: int
                  ) -> tuple[Allocation, float]:
    fast = _compiled_response(tables, soldiers)
    if fast is not None:
        return fast
    # Pure-Python fallback: dp[i][t] is the best contribution from castles [0, i).
    dp = [[-math.inf] * (soldiers + 1) for _ in range(len(VALUES) + 1)]
    choice = [[0] * (soldiers + 1) for _ in range(len(VALUES) + 1)]
    dp[0][0] = 0.0
    for i in range(1, len(VALUES) + 1):
        row = tables[i - 1]
        for used in range(soldiers + 1):
            for x in range(used + 1):
                candidate = dp[i - 1][used - x] + row[x]
                if candidate > dp[i][used]:
                    dp[i][used] = candidate
                    choice[i][used] = x
    allocation = [0] * len(VALUES)
    remaining = soldiers
    for i in range(len(VALUES), 0, -1):
        allocation[i - 1] = choice[i][remaining]
        remaining -= allocation[i - 1]
    return tuple(allocation), dp[len(VALUES)][soldiers]  # type: ignore[return-value]


def _compiled_count_function():
    if not _FAST_CHECKED:
        _compiled_response(tuple((0.0,) * 101 for _ in range(5)), 100)
    return _FAST_COUNT_LIBRARY


def _compiled_response(tables: tuple[tuple[float, ...], ...], soldiers: int
                      ) -> tuple[Allocation, float] | None:
    """Use optional C++ DP kernel when a compiler is available; otherwise fallback."""
    global _FAST_LIBRARY, _FAST_COUNT_LIBRARY, _FAST_CHECKED
    if not _FAST_CHECKED:
        _FAST_CHECKED = True
        compiler = shutil.which("c++")
        if compiler:
            source = Path(__file__).with_name("fast_dp.cpp")
            library_path = Path(tempfile.gettempdir()) / "castle-challenges-fast-dp.so"
            try:
                subprocess.run([compiler, "-O3", "-shared", "-fPIC", str(source),
                                "-o", str(library_path)], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                library = ctypes.CDLL(str(library_path))
                function = library.castle_h2h_dp
                function.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int,
                                     ctypes.POINTER(ctypes.c_double),
                                     ctypes.POINTER(ctypes.c_int)]
                function.restype = None
                _FAST_LIBRARY = function
                count_function = library.castle_h2h_dp_counts
                count_function.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.c_int,
                                           ctypes.POINTER(ctypes.c_int64),
                                           ctypes.POINTER(ctypes.c_int)]
                count_function.restype = None
                _FAST_COUNT_LIBRARY = count_function
            except (OSError, subprocess.SubprocessError):
                _FAST_LIBRARY = None
    if _FAST_LIBRARY is None or soldiers > 100:
        return None
    flat_tables = []
    for row in tables:
        flat_tables.extend(row)
        flat_tables.extend([0.0] * (101 - len(row)))
    flattened = (ctypes.c_double * (5 * 101))(*flat_tables)
    output_value = ctypes.c_double()
    output_allocation = (ctypes.c_int * 5)()
    _FAST_LIBRARY(flattened, soldiers, ctypes.byref(output_value), output_allocation)
    return tuple(output_allocation), output_value.value  # type: ignore[return-value]
