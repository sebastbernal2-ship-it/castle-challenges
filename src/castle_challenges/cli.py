"""Command line helpers."""

import argparse
from math import comb
import random

from .game import SOLDIERS
from .simulation import evaluate_four_way, evaluate_head_to_head


def parse_allocation(text: str) -> tuple[int, int, int, int, int]:
    try:
        result = tuple(int(part.strip()) for part in text.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use five comma-separated integers") from exc
    if len(result) != 5 or any(x < 0 for x in result) or sum(result) != 100:
        raise argparse.ArgumentTypeError("allocation must be five nonnegative integers summing to 100")
    return result  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(prog="castle-challenges")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("count", help="count legal pure allocations")
    evaluate = sub.add_parser("evaluate", help="evaluate versus a baseline population")
    evaluate.add_argument("allocation", type=parse_allocation)
    evaluate.add_argument("--opponents", type=int, default=10_000)
    evaluate.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.command == "count":
        print(comb(104, 4))
        return
    # Uniform sampling over all pure allocations is a neutral diagnostic baseline,
    # not an equilibrium or a claim about the applicant population.
    rng = random.Random(args.seed)
    population = []
    # Uniform stars-and-bars sample; this is a sampled baseline population.
    for _ in range(20_000):
        bars = sorted(rng.sample(range(SOLDIERS + 4), 4))
        cuts = [-1, *bars, SOLDIERS + 4]
        population.append(tuple(cuts[i + 1] - cuts[i] - 1 for i in range(5)))
    print("Uniform-allocation baseline")
    print("Game 1 (mean score, SE):", evaluate_head_to_head(args.allocation, population, args.opponents, args.seed))
    print("Game 2 (mean payout, SE):", evaluate_four_way(args.allocation, population, args.opponents, args.seed))


if __name__ == "__main__":
    main()
