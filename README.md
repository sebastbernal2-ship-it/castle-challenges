# Castle Challenges

A reproducible research workspace for finding strong strategies—and, where possible, Nash/GTO solutions—for the two 100-soldier castle games.

## Rules encoded

An allocation is a five-tuple of nonnegative integers summing to 100. Castles have values `(1, 2, 3, 4, 5)`.

### Game 1: head-to-head
For each castle, the player with more soldiers receives its value; equal allocations split the value. Utility is the sum over castles. Against a population distribution, a strategy's payoff is its expected score against a random opponent. The symmetric zero-sum payoff is equivalently the difference in scores (the score sum is always 15).

### Game 2: four-way battle
Each castle's value is split equally among all players tied for the largest allocation there. A player's rank is determined by their total castle points. Players tied in rank split the payouts for the rank positions they occupy: e.g. a two-way tie for first/second receives `(9+4)/2 = 6.5` each. Payouts are `(9, 4, 2, 0)`.

## Important modelling caveat

“GTO” depends on the opponent model and on whether players may use mixed strategies. This project treats each game as a symmetric, finite, simultaneous game with private independent randomization. Game 1 has a constant-sum payoff, so symmetric Nash equilibrium strategies are well-defined. Game 2 is a general-sum multiplayer game; a symmetric Nash equilibrium is not generally a unique strategy and need not maximize tournament score against a particular applicant population. We should report the equilibrium concept and assumptions alongside every result.

The browser description leaves some details open (for example, how random groups are sampled and how payout ties are handled). The rules above make explicit conventions; confirm them against the actual challenge implementation before treating results as definitive.

## Getting started

Requires Python 3.10+; no runtime dependencies.

```sh
python -m unittest discover -s tests -v
python -m castle_challenges.cli count
python -m castle_challenges.cli evaluate 20,20,20,20,20 --opponents 10000 --seed 7
```

The allocation space is large: `C(104,4) = 4,598,126` pure strategies. Exact full-game matrix methods are therefore not the first step. The package provides exact per-profile scoring and seeded Monte Carlo evaluation, which form a trustworthy foundation for restricted-game solvers, best-response oracles, and population searches.

## Research plan

1. Validate semantics and build unit tests against hand-calculated examples.
2. Characterize the pure-strategy landscape, dominance, and useful allocation families.
3. For Game 1, solve restricted zero-sum games and expand the support with best responses; bound/validate exploitability with independent searches.
4. For Game 2, estimate expected rank payout under candidate populations, then use sampled best responses / evolutionary or regret-based methods. Distinguish symmetric equilibrium from performance against a specified field.
5. Use independent seeds, confidence intervals, and saved experiment parameters. Never present Monte Carlo point estimates as exact GTO results.

## Layout

- `src/castle_challenges/game.py`: rules and pure allocation enumeration.
- `src/castle_challenges/simulation.py`: population Monte Carlo evaluators.
- `src/castle_challenges/cli.py`: small command-line entry point.
- `tests/`: rules and deterministic sanity checks.
- `research/`: experiment notes and results (add scripts and provenance here).
