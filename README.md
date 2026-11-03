# Castle Challenges Research

This repository studies two related allocation challenges as **separate games**. They share the legal allocation format, but have different scoring rules, objectives, analyses, and (eventually) solvers.

## Repository structure

```text
src/castle_challenges/
├── common/                 # Allocation representation and validation only
└── games/
    ├── head_to_head/       # Game 1 rules, evaluation, CLI, solver work
    └── four_way/           # Game 2 rules, evaluation, CLI, solver work
research/
├── head_to_head/           # Game 1 notebooks, experiments, findings
└── four_way/               # Game 2 notebooks, experiments, findings
tests/
├── head_to_head/           # Game 1 tests
└── four_way/               # Game 2 tests
```

## Shared setup

- Python 3.10+
- No runtime dependencies

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Game 1 — Head to Head

Each player allocates 100 whole soldiers across castles worth `(1, 2, 3, 4, 5)`. For each castle, the larger allocation wins its points and a tie splits the points. The challenge objective is average castle score over opponents.

Game-specific code: `src/castle_challenges/games/head_to_head/`. The `best_response` module contains an exact dynamic-programming oracle against any finite mixed strategy; see `research/head_to_head/analysis.md` for the derivation and double-oracle plan.

```sh
castle-head-to-head --count
castle-head-to-head 20,20,20,20,20 --trials 10000 --seed 7
```

The evaluator reports performance against a sampled uniform-composition baseline. That baseline is diagnostic only, not a model of applicants or an equilibrium.

**Research target:** symmetric Nash equilibrium in this finite two-player constant-sum game. There are `C(104,4) = 4,598,126` legal pure strategies, so restricted-game solving and best-response expansion are natural starting points.

## Game 2 — Four-Way Battle

Four players allocate 100 soldiers each. Each castle's points are awarded to its high bidder(s), split equally in case of a tie. Players are ranked by castle points; players tied in rank split the payouts for the rank slots they occupy, using `(9, 4, 2, 0)`.

Game-specific code: `src/castle_challenges/games/four_way/`. Its analysis and a solver plan are in `research/four_way/analysis.md`.

```sh
castle-four-way 20,20,20,20,20 --trials 10000 --seed 7
```

Opponents are sampled independently with replacement from the sampled uniform-composition baseline.

**Research target:** explicitly state the solution concept. This is a multiplayer general-sum game; symmetric Nash equilibrium, evolutionary stability, and best performance against a particular applicant field are different goals and may yield different strategies.

## Modelling assumptions to verify

The challenge description does not fully specify group sampling or tie resolution details. Current conventions are documented in each rules module: tied castle leaders split castle points, and rank ties average payouts across occupied places. Four-way simulation samples opponents independently with replacement. Verify these against the actual implementation before claiming a definitive solution.

## Research standards

- Keep each game's assumptions, experiments, solver code, and results in its own directory.
- Record parameters, source revision, random seed, and uncertainty for stochastic results.
- Separate exact calculations from Monte Carlo estimates.
- Do not label a population-specific benchmark or approximate solver output “GTO” without a defined equilibrium concept and exploitability validation.
