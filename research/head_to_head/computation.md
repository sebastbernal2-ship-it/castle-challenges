# Game 1 computation log

## Exact equilibrium found

`results/exact-equilibrium-flow-lp.json` is an exact equilibrium certificate under the encoded rules: 194 legal allocations with integer frequency total 410, exact full-action best-response score `6150/820 = 7.5`, and exploitability `0/820`. `verify_strategy.py` checks every legal allocation using exact integer DP. The certificate was found by solving a sparse marginal-polytope cutting-plane LP, reconstructing its simple rational marginals (common denominator 410), then finding an integer path-flow coupling. The float LP was only a discovery tool; the rational flow and exhaustive exact response audit establish the result.

Reproduce the exact rational-flow extraction from the saved LP discovery candidate (requires the `research` optional dependencies):

```sh
python -m pip install -e '.[research]'
PYTHONPATH=src python3 research/head_to_head/certify_marginal_equilibrium.py \\
  --candidate research/head_to_head/results/marginal-polytope-lp-candidate.json \\
  --output /tmp/exact-equilibrium.json
PYTHONPATH=src python3 research/head_to_head/verify_strategy.py /tmp/exact-equilibrium.json
```

The floating-point discovery candidate can be regenerated with `marginal_polytope_lp.py`; the committed exact strategy and verifier output do not depend on rerunning that LP.

The proof is the saved exact strategy and zero-gap full-action audit, not the numerical LP status. Confirm tie and sampling semantics against the challenge implementation before claiming this is the definitive challenge answer.

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

The first polishing passes reduced the certificate from `38,051 / 4,000,052 = 0.0095126263` through `20,694 / 4,000,052 = 0.0051734327`. Scaling frequencies 10x and using a finer step grid reached `206,792 / 40,000,520 = 0.0051697328`; see `results/polished-frequency10x-seed1.json` for the exact audit.

A stronger direction oracle then produced a substantial further gain. For the top `K` exact attacker deviations, `restricted_defense_oracle_fictitious_play.cpp` runs fictitious play against the **full 4,598,126-action defense space**: each defender response to the current attacker mixture is found by exact integer DP, while the attacker best response is selected among the `K` supplied rows. This generates a defense mixture that can include actions that are not best responses to any single deviation. We line-search from the current strategy toward this mixture and accept a step only when the exact full-action DP gap decreases. The restricted-game fictitious-play gap is diagnostic only; only the separate full-action strategy certificate is global.

| Attacker rows K | Defender-oracle iterations | Certified full-action gap |
|---:|---:|---:|
| 1,000 | 100,000 | 0.0045127913 |
| 1,000 | 500,000 | 0.0032128582 |
| 2,000 | 1,000,000 | 0.0030916348 |
| 2,000 | 3,000,000 | 0.0028925124 |
| 3,000 | 10,000,000 | 0.0028530629 |
| 5,000 | 3,000,000 | 0.0027720390 |
| 10,000 | 3,000,000 | 0.0027061648 |
| 20,000 | 3,000,000 | 0.0024977925 |
| 50,000 | 1,000,000 | 0.0023385446 |
| 50,000 | 2,000,000 | 0.0018797756 |
| 50,000 | 1,000,000 | 0.0016154790 |
| 50,000 | 1,000,000 | 0.0013657572 |
| 50,000 | 1,000,000 | 0.0010884109 |
| 50,000 | 1,000,000 | 0.0009493127 |
| 50,000 | 1,000,000 | 0.0009021633 |
| 10,000 | 3,000,000 | 0.0007770149 |
| 10,000 | 3,000,000 | 0.0007742399 |
| 50,000 | 1,000,000 | 0.0007730400 |
| 50,000 | 1,000,000 | 0.0007702150 |
| 50,000 | 1,000,000 | 0.0007690650 |

Historical incumbent before the exact LP result: the 68,862-action mixture in `results/polished-full-action-defense-oracle.json` had exact exploitability `30,514 / 40,000,520 ≈ 0.00076284008` and best response `(12,4,5,12,67)`. HPG job `49349592` improved the prior candidate through three polishing steps; that heuristic artifact is retained for research history but superseded by the exact equilibrium above.

Reproduce the final accepted step (the oracle run takes about 11 minutes on the recorded machine):

```sh
PYTHONPATH=src python3 research/head_to_head/polish_strategy.py \\
  research/head_to_head/results/full-column-recent-checkpoint.json \\
  --steps 1 --top-k 50000 --oracle-iterations 1000000 \\
  --pure-directions 128 --output /tmp/latest.json
PYTHONPATH=src python3 research/head_to_head/verify_strategy.py /tmp/latest.json
```

The previous sweep incumbent (`step3.json`, gap `0.00076464006`) is reproducible from its preserved starting mixture with three polishing steps:

```sh
PYTHONPATH=src python3 research/head_to_head/polish_strategy.py \\
  research/head_to_head/results/polished-full-action-defense-oracle-baseline.json \\
  --steps 3 --top-k 50000 --oracle-iterations 1000000 \\
  --pure-directions 128 --output /tmp/hpg-candidate-0.json
PYTHONPATH=src python3 research/head_to_head/verify_strategy.py /tmp/hpg-candidate-0.json
```

The eight-configuration sweep (`49312405`) and its refinement (`49349592`) are historical; they generated the positive-gap heuristic incumbent described above. A further refinement (`49363145`) had been submitted before the exact LP certificate superseded it. HPG SSH access is currently unavailable, so its present status and cancellation could not be confirmed. These heuristic jobs are not needed for the exact Game 1 result.

Those historical line-search strategies had positive gaps and were not equilibria. The exact flow-LP certificate above supersedes them for Game 1 under the encoded rules.

## Compact path-flow / mirror-prox experiment

The legal allocation polytope can be represented as unit flows on a five-layer DAG of cumulative soldier totals: arc `(castle i, total s, count x)` advances from `s` to `s+x`. It has 25,755 arcs, and path decomposition gives a legal allocation mixture. Since Game 1 payoff depends only on castle marginals, the saddle objective is bilinear in the marginals projected from two such flows. `mirror_prox_flow.cpp` uses Gibbs path distributions and forward/backward DP to update them without enumerating actions; the Python runner decomposes its averaged flows into legal allocations and then invokes the exact verifier.

This is a useful compact formulation but the current numerical solver did not improve the incumbent. Exact verification gave gaps `0.17618056` after 1,000 iterations at step `0.03`, `4.41000924` after 100,000 at `0.03`, and `1.00263072` after 200,000 at `0.0002`. The implementation clips very small per-castle Gibbs weights for numerical stability, so it is not yet a certified implementation of unmodified mirror-prox. Run a small reproduction with:

```sh
PYTHONPATH=src python3 research/head_to_head/run_mirror_prox_flow.py \\
  --iterations 1000 --eta 0.03 --output /tmp/mirror-prox.json
PYTHONPATH=src python3 research/head_to_head/verify_strategy.py /tmp/mirror-prox.json
```

The candidate is always full-action audited, but these runs expose a convergence/step-size problem rather than solving it.

## Restricted-game LP double oracle

For a more direct mathematical optimization, `double_oracle_lp.py` now solves the primal and dual zero-sum LPs on generated row/column strategy pools. Its payoff matrix uses the exact separability of Game 1: against any opponent mixture, each castle contributes from its one-dimensional soldier-count marginals. The restricted pool includes the incumbent mixture as a meta-action, plus pure actions. After each restricted LP, exact integer-DP best responses against the quantized row and column mixtures add new actions; the symmetric average is audited over the full action space. Thus an LP candidate can never replace the incumbent unless its exact certificate is better.

With exact rational restricted LP solutions and exact full-action responses, this double oracle is a finite complete algorithm: each unsuccessful round adds a previously absent profitable pure action, and the action set is finite. The current implementation uses HiGHS floating-point LPs, so it is a candidate-generation/approximation method rather than an exact equilibrium proof. Its saved full-action gaps remain exact. The first HiPerGator run (`49327028`) completed 50 iterations; the restricted primal/dual LP gaps were near numerical precision, but no LP-generated symmetric average improved the incumbent's `0.0007688900` exact full-action gap. The follow-up (`49327950`) completed 20 rounds with batches of 200 responses; its final LP average still had a `0.0134` full-action gap, so the saved exact-audited incumbent remained unchanged. The resumed larger-batch run (`49329832`, 400 responses per round) also completed without improving its older `0.0007688900` incumbent; after ten rounds its latest restricted average still had a `0.00402` full-action gap. The LP search has therefore not improved the newer polishing result. Iteration logs, resumable pool state, and best-so-far exact certificates were checkpointed in `results/double-oracle-lp.json` on the cluster. A restricted LP equilibrium by itself is not a certificate for omitted allocations.

## Regularized-response experiment

We also implemented exact logit-response marginals by a log-space coefficient DP, exploiting separability. A fixed-point continuation was unstable at lower temperatures; at temperature 0.1 it converged to a mixture with exact full-action gap about 0.1034. Averaging logit responses for 10,000 iterations at temperature 0.1 gave gap 0.1023. This did not improve on long fictitious play. Lower temperatures performed worse in short runs. The method and caveats are in `src/castle_challenges/games/head_to_head/logit_equilibrium.py`; no logit result is presented as an equilibrium.

## Interpretation and next computation

Game 1 now has a zero-gap exact equilibrium certificate under the encoded rules. Game 2 remains unsolved, and the challenge's external rule semantics still need confirmation.
