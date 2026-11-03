"""Game 1 command-line baseline evaluator."""

import argparse
from math import comb
import random

from ...common.allocation import SOLDIERS
from .evaluation import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(prog="castle-head-to-head")
    parser.add_argument("allocation", nargs="?", help="five comma-separated integers")
    parser.add_argument("--trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--count", action="store_true", help="print number of legal allocations")
    args = parser.parse_args()
    if args.count:
        print(comb(SOLDIERS + 4, 4))
        return
    if args.allocation is None:
        parser.error("allocation is required unless --count is used")
    try:
        strategy = tuple(int(x) for x in args.allocation.split(","))
        if len(strategy) != 5 or sum(strategy) != SOLDIERS or min(strategy) < 0:
            raise ValueError
    except ValueError:
        parser.error("allocation must be five nonnegative integers summing to 100")
    rng = random.Random(args.seed)
    population = []
    for _ in range(20_000):
        bars = sorted(rng.sample(range(SOLDIERS + 4), 4))
        cuts = [-1, *bars, SOLDIERS + 4]
        population.append(tuple(cuts[i + 1] - cuts[i] - 1 for i in range(5)))
    print("Uniform-allocation diagnostic baseline (not an equilibrium)")
    print("mean castle score, standard error:", evaluate(strategy, population, args.trials, args.seed))
