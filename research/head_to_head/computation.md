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
| 1 | 30,000 | 1,695 | 7.575851 | 0.075851 |
| 1 | 80,000 | 2,776 | 7.545217 | 0.045217 |
| 1 | 500,000 | 7,100 | 7.518204 | 0.018204 |
| 1 | 700,000 | 8,407 | 7.515319 | 0.015319 |
| 1 | 1,000,000 | 10,102 | 7.512992 | 0.012992 |
| 1 | 2,000,000 | 14,544 | 7.5095126263 | 0.0095126263 |
| 2 | 10,000 | 955 | 7.633702 | 0.133702 |
| 2 | 500,000 | 7,112 | 7.518088 | 0.018088 |
| 3 | 10,000 | 992 | 7.640884 | 0.140884 |

At 500,000 rounds, two independent seeds give closely matching exploitability gaps (0.018204 and 0.018088), suggesting the trend is not a seed artifact. For the 2,000,000-round seed-1 strategy, I reconstructed the empirical integer frequencies and reran the final best-response DP using integer arithmetic. It returned score `30,038,441 / 4,000,052`; subtracting the game value `15/2` gives the exact exploitability `38,051 / 4,000,052 = 0.00951262633585781` points. This is an exact certificate for the saved finite mixture under the encoded rules (not a certificate that the mixture is an exact Nash equilibrium). Earlier rows use floating-point DP. The residual is small but strictly positive. For the 20,000-round seed-1 mixture, mean soldier counts are approximately `(6.36, 13.09, 19.91, 26.68, 33.95)`. This is descriptive, not a pure recommendation: support and allocation correlations matter.

Full mixed distributions, initialization seeds, exact deviations, and machine-readable metadata are saved as JSON beside this report. A compiled C++ DP kernel and incremental marginal histograms make longer runs practical; the solver falls back to Python if no compiler is available. Reproduce from the repository root:

```sh
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 20000 --seed 1
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 10000 --seed 2
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 10000 --seed 3
PYTHONPATH=src python3 research/head_to_head/run_fictitious_play.py --rounds 2000000 --seed 1
```

## Best-response subgradient polishing

The 2-million-round mixture was further polished by minimizing its convex exploitability objective `f(p)=max_b E[u(b,a)]-7.5`. At each step, the exact DP finds a worst deviation `b`; a second exact DP finds a pure action minimizing `u(b,·)` (equivalently, a best response to pure `b` under the constant-sum identity). We grid-search the mixture step size, quantize back to the fixed integer-frequency denominator, and recertify using integer DP. This is a heuristic Frank–Wolfe/subgradient procedure; it has no guarantee for the nonsmooth objective and stopped when no tested step improved the gap.

The first polishing passes improved the certificate from `38,051 / 4,000,052 = 0.0095126263` through `22,754 / 4,000,052 = 0.0056884261`. A further search accelerated the restricted defense-matrix fictitious play in `restricted_matrix_fictitious_play.cpp` and widened the line-search grid. It used the top 3,000 exact deviations and 100,000 restricted matrix rounds. At frequency denominator 2,000,026 it reduced the exact integer-DP gap to `20,694 / 4,000,052 = 0.0051734327`, about 9% below the earlier 0.0056884 candidate. Scaling that mixture's frequencies 10x and adding finer line-search steps produced a further, smaller improvement: `206,792 / 40,000,520 = 0.0051697328` points, with best response `(4,5,3,50,38)`. This is about a 0.07% reduction from the preceding candidate, not a new equilibrium result. The 15,342-action strategy and exact certificate are in `results/polished-frequency10x-seed1.json`; compact checkpoints record the deterministic polishing chain.

Reproduce the frequency-scaled polishing chain with:

```sh
PYTHONPATH=src python3 research/head_to_head/polish_strategy.py \\
  research/head_to_head/results/polished-frequency10x-checkpoint.json \\
  --steps 1 --top-k 3000 --matrix-rounds 100000 --pure-directions 512 \\
  --output /tmp/polish-a.json
PYTHONPATH=src python3 research/head_to_head/polish_strategy.py /tmp/polish-a.json \\
  --steps 5 --top-k 3000 --matrix-rounds 100000 --pure-directions 512 \\
  --output /tmp/polish-b.json
PYTHONPATH=src python3 research/head_to_head/polish_strategy.py /tmp/polish-b.json \\
  --steps 1 --top-k 3000 --matrix-rounds 100000 --pure-directions 128 \\
  --output /tmp/polish-c.json
PYTHONPATH=src python3 research/head_to_head/polish_strategy.py /tmp/polish-c.json \\
  --steps 5 --top-k 3000 --matrix-rounds 100000 --pure-directions 128 \\
  --output /tmp/polish-final.json
PYTHONPATH=src python3 research/head_to_head/verify_strategy.py /tmp/polish-final.json
```

The saved checkpoints `polished-frequency10x-stage1.json` through `stage3.json` correspond to the successive outputs. Further top-5,000 and 512-direction searches at the unscaled denominator found no improvement; frequency scaling enabled a few single-count gains. These remain heuristic convex-objective searches, not a global optimality proof. The gap is positive, so Game 1 is still not exactly solved or GTO.

## Regularized-response experiment

We also implemented exact logit-response marginals by a log-space coefficient DP, exploiting separability. A fixed-point continuation was unstable at lower temperatures; at temperature 0.1 it converged to a mixture with exact full-action gap about 0.1034. Averaging logit responses for 10,000 iterations at temperature 0.1 gave gap 0.1023. This did not improve on long fictitious play. Lower temperatures performed worse in short runs. The method and caveats are in `src/castle_challenges/games/head_to_head/logit_equilibrium.py`; no logit result is presented as an equilibrium.

## Interpretation and next computation

The latest polished candidate is a rigorously evaluated `0.0051697328`-epsilon strategy under the encoded rules; its exact rational full-action deviation certificate is independently checked by `verify_strategy.py`. The gap remains positive, so this is not exact GTO. Standard fictitious-play convergence is asymptotic; the finite-run and local-polishing results do not identify the exact equilibrium or prove global optimality of the exploitability minimum. Further reductions require stronger optimization (for example, a convergent double-oracle/LP method with exact separation), not just labeling the current candidate equilibrium.
