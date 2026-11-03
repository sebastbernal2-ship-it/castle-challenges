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
- No runtime dependencies for the game models and verifiers
- Optional `research` dependencies (`numpy`, `scipy`) for the marginal-polytope LP and rational-flow certificate generator

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

The evaluator reports performance against a sampled uniform-composition baseline. That baseline is diagnostic only, not a model of applicants or an equilibrium. Game 1 now has an exact symmetric Nash-equilibrium certificate under the encoded rules: `research/head_to_head/results/exact-equilibrium-flow-lp.json` is a legal 194-allocation mixture (frequency total 410) whose exact best-response score is `6150/820 = 7.5` and whose full-action exploitability is exactly zero. Verify it with `PYTHONPATH=src python3 research/head_to_head/verify_strategy.py research/head_to_head/results/exact-equilibrium-flow-lp.json`. The proof covers all 4,598,126 legal allocations; confirm challenge tie and sampling semantics before treating it as the definitive challenge answer. Derivation and reproducibility are in `research/head_to_head/computation.md`.

**Solved under the encoded model:** a symmetric Nash equilibrium in this finite two-player constant-sum game is saved and exactly certified. There are `C(104,4) = 4,598,126` legal pure strategies; the exact dynamic-programming verifier covers them all.

## Game 2 — Four-Way Battle

Four players allocate 100 soldiers each. Each castle's points are awarded to its high bidder(s), split equally in case of a tie. Players are ranked by castle points; players tied in rank split the payouts for the rank slots they occupy, using `(9, 4, 2, 0)`.

Game-specific code: `src/castle_challenges/games/four_way/`. Its analysis and computation log are in `research/four_way/`. `run_exact_full_best_response.py` evaluates responses over all 4,598,126 legal allocations with exact integer arithmetic and can return the top K; optional support truncation gives a rigorous bound for discarded mass. A restricted symmetric-minimax response-expansion search has reached a best exact-audited deviation gap of about `1.2674`, still far above zero. Game 2 remains unsolved; HPG job `49377453` is continuing the search. See `research/four_way/analysis.md` and `computation.md` for limitations and current status.

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
