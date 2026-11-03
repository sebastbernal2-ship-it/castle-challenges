"""Entropic/logit equilibrium iteration using Game 1's castle separability."""

from dataclasses import dataclass
from math import comb, exp, log

from ...common.allocation import SOLDIERS, VALUES
from .best_response import best_response_from_marginals


@dataclass(frozen=True)
class LogitResult:
    temperature: float
    iterations: int
    residual: float
    marginals: tuple[tuple[float, ...], ...]
    best_response: tuple[int, int, int, int, int]
    best_response_score: float
    exploitability: float


def logit_response_marginals(marginals: tuple[list[float], ...], temperature: float,
                             soldiers: int = SOLDIERS) -> tuple[list[float], ...]:
    """Exact marginals of the entropy-regularized best response distribution.

    The distribution over allocations is proportional to exp(expected_score/tau).
    Since Game 1's score is additive across castles, its partition function and
    all five marginals are computed by log-space coefficient DP.
    """
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    if len(marginals) != 5 or any(len(row) != soldiers + 1 for row in marginals):
        raise ValueError("marginals have the wrong shape")
    q = []
    log_weights = []
    for i, value in enumerate(VALUES):
        total = sum(marginals[i])
        if total <= 0:
            raise ValueError("each marginal must have positive mass")
        cumulative = 0.0
        row = []
        for mass in marginals[i]:
            row.append(value * (cumulative + mass / 2) / total)
            cumulative += mass
        q.append(row)
        high = max(row)
        log_weights.append([(score - high) / temperature for score in row])

    # Forward and backward log partition functions by total soldier count.
    prefix = [[float("-inf")] * (soldiers + 1) for _ in range(6)]
    prefix[0][0] = 0.0
    for i in range(5):
        for total in range(soldiers + 1):
            prefix[i + 1][total] = _logsumexp(
                log_weights[i][x] + prefix[i][total - x] for x in range(total + 1))
    suffix = [[float("-inf")] * (soldiers + 1) for _ in range(6)]
    suffix[5][0] = 0.0
    for i in range(4, -1, -1):
        for total in range(soldiers + 1):
            suffix[i][total] = _logsumexp(
                log_weights[i][x] + suffix[i + 1][total - x]
                for x in range(total + 1))

    response = []
    for i in range(5):
        log_masses = []
        for x in range(soldiers + 1):
            remainder = soldiers - x
            rest = _logsumexp(prefix[i][before] + suffix[i + 1][remainder - before]
                              for before in range(remainder + 1))
            log_masses.append(log_weights[i][x] + rest)
        normalizer = _logsumexp(log_masses)
        response.append([exp(value - normalizer) for value in log_masses])
    return tuple(response)


def solve_averaged(temperature: float, iterations: int = 10_000,
                  soldiers: int = SOLDIERS) -> LogitResult:
    """Average logit best responses, rather than seeking a fixed point.

    This is regularized fictitious play. The output is checked with the exact
    unregularized DP oracle, since regularized convergence alone is not a proof.
    """
    if temperature <= 0 or iterations < 1:
        raise ValueError("temperature and iterations must be positive")
    count = comb(soldiers + 4, 4)
    current = [[comb(soldiers - x + 3, 3) / count for x in range(soldiers + 1)]
               for _ in VALUES]
    for t in range(1, iterations + 1):
        response = logit_response_marginals(tuple(current), temperature, soldiers)
        current = [[((t - 1) * current[i][x] + response[i][x]) / t
                    for x in range(soldiers + 1)] for i in range(5)]
    action, score = best_response_from_marginals(tuple(current), 1.0, soldiers)
    return LogitResult(temperature, iterations, float("nan"),
                       tuple(tuple(row) for row in current), action, score, score - 7.5)


def solve(temperatures: tuple[float, ...] = (0.2, 0.1, 0.05, 0.02, 0.01),
          soldiers: int = SOLDIERS, damping: float = 0.2,
          max_iterations: int = 20_000, tolerance: float = 1e-10) -> tuple[LogitResult, ...]:
    """Continuation solve for symmetric logit QREs, then exact deviation check.

    Returned strategies are mixtures represented by their castle marginals;
    this suffices because all Game 1 payoffs depend only on those marginals.
    The final exploitability is the exact pure best response to that mixture.
    """
    if not 0 < damping <= 1:
        raise ValueError("damping must be in (0, 1]")
    # Marginals under the uniform distribution over weak compositions.
    count = comb(soldiers + 4, 4)
    current = [[comb(soldiers - x + 3, 3) / count for x in range(soldiers + 1)]
               for _ in VALUES]
    results = []
    for tau in temperatures:
        if tau <= 0:
            raise ValueError("all temperatures must be positive")
        residual = float("inf")
        iteration = 0
        for iteration in range(1, max_iterations + 1):
            response = logit_response_marginals(tuple(current), tau, soldiers)
            residual = max(abs(response[i][x] - current[i][x])
                           for i in range(5) for x in range(soldiers + 1))
            current = [[(1 - damping) * current[i][x] + damping * response[i][x]
                        for x in range(soldiers + 1)] for i in range(5)]
            if residual <= tolerance:
                break
        action, score = best_response_from_marginals(
            tuple(current), total_mass=1.0, soldiers=soldiers)
        results.append(LogitResult(tau, iteration, residual,
                                   tuple(tuple(row) for row in current), action,
                                   score, score - 7.5))
    return tuple(results)


def _logsumexp(values) -> float:
    values = list(values)
    high = max(values)
    if high == float("-inf"):
        return high
    return high + log(sum(exp(value - high) for value in values))
