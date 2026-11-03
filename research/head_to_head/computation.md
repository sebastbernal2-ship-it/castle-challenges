# Game 1 computation log

## Full-action fictitious play, exact best responses

Ran two-sided fictitious play on the entire 4,598,126-action strategy space. At each round, each side's action is a pure best response to the opponent's empirical mixture. The response is computed by the exact marginal-payoff dynamic program, not by sampling allocations. Each side starts with the same 26-action pseudocount set: equal allocation, five corner allocations, and 20 seeded uniform-composition draws. Deterministic tie-breaking and symmetric initialization make the two empirical strategies identical in these runs.

For each final mixture, a fresh exact DP computes the best pure deviation against the other mixture. Since the symmetric constant-sum game's value is 7.5, `best-response score - 7.5` is the exact exploitability of that mixture against the full action space, up to floating-point arithmetic. This is a valid deviation check for these returned strategies; it is not a proof that fictitious play has converged.

| Seed | Best-response rounds | Distinct support | Exact best-response score | Gap above 7.5 |
|---:|---:|---:|---:|---:|
| 1 | 100 | 95 | 9.015873 | 1.515873 |
| 1 | 1,000 | 329 | 7.990741 | 0.490741 |
| 1 | 10,000 | 1,003 | 7.635049 | 0.135049 |
| 1 | 20,000 | 1,401 | 7.595101 | 0.095101 |
| 2 | 10,000 | 955 | 7.633702 | 0.133702 |
| 3 | 10,000 | 992 | 7.640884 | 0.140884 |

The three independent 10,000-round runs have similar exploitability (about 0.134–0.141 castle points), providing evidence of numerical stability at this scale, not an equilibrium certificate. The 20,000-round run improves the gap for seed 1. The strategy mean soldier counts vary slightly by seed; for the 20,000-round seed-1 mixture they are approximately `(6.36, 13.09, 19.91, 26.68, 33.95)`. This mean is descriptive, not a recommendation for a pure allocation: the mixed strategy's support and allocation correlations matter.

Full mixed distributions, initialization seeds, exact deviations, and machine-readable metadata are saved as JSON beside this report. Reproduce from the repository root:

```sh
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 20000 --seed 1
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 10000 --seed 2
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 10000 --seed 3
```

## Interpretation and next computation

This is substantially stronger than random-composition Monte Carlo: it searches the full legal action space for deviations at every step and for final verification. Yet a 0.095-point profitable deviation remains after 20,000 rounds, so the current mixture is not a GTO solution at useful precision. Fictitious play convergence can be slow. Next steps are acceleration (restricted matrix equilibrium / sequence methods), longer runs and more seeds, convergence traces, and independent oracle/property tests. Report current strategies as approximate low-exploitability candidates only.
