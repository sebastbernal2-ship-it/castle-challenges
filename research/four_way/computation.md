# Game 2 computation log

## Finite-mixture expected payout

`games/four_way/best_response.py` enumerates the `C(K+2,3)` unordered opponent triples for a support of size `K`, applies their iid multiplicities, and computes a candidate payout against that supplied mixture. `best_candidate` only compares a caller-supplied action set; it is not a full-game oracle. `response_distribution.py` audits a fixed strategy with exact rational arithmetic.

A diagnostic population assigns equal probability to the even allocation `(20,20,20,20,20)` and five single-castle corners. Against it, the exhaustive full-action search finds `(1,21,21,21,36)` with payout `8.402778`, a gain of about `4.652778` above the symmetric self-play value 3.75. Adding that response at equal mass yields another profitable response `(2,1,22,22,53)` with payout `8.291545`. This confirms the simple baseline is highly exploitable, not that the expansion process converges. Results are in `results/full_action_responses.json`.

Against four copies of the even allocation, `(20,0,21,21,38)` earns 9, illustrating a profitable response to a pure strategy.

## Further search and structural result

Restricted replicator plus full-action oracle experiments are documented in `restricted-search.md`. On 9-, 10-, and 11-action pools, the restricted dynamics produced mixtures against which full-action search printed `9.0` at floating-point precision. Exact rational audits show why that is not a guarantee of 9 against every support triple. A pure symmetric allocation cannot be a Nash equilibrium; see the direct deviation proof in `restricted-search.md`.

A native C++ restricted multiplicative-weights implementation agrees with the Python reference on the six-action pool to within `5.6e-16`. On 24 actions, restricted payoff gaps fell below `1e-14` while a full-action reply still earned 8.8482; the response-expanded pool remained exploitable. See [`double-oracle.md`](double-oracle.md) and `results/double_oracle_chain.json`.

## Restricted support search (sizes one through three)

`restricted_two_support_search.py` enumerates pure and two-action supports in a finite pool. For a pair `(a,b)`, the indifference condition `g_a(x)=g_b(x)` is cubic in `x=P(a)`; unit-interval roots are isolated numerically, rationalized to integer frequencies, and audited with the exact global response oracle.

`restricted_support3_search.py` builds the small-pool payoff tensor, uses multi-start Newton to find roots of the two indifference equations on each three-action support, checks every omitted pool action, and exact-audits surviving candidates against the whole game. On the six-action baseline it finds a restricted support-three equilibrium, but the exact full-game response `(20,21,21,0,38)` gives exploitability `21/4 = 5.25`. Support-two searches on the six-action and 18-action pools find the same minimum gap. This illustrates why restricted equilibria do not certify full-game equilibria.

Reproduce these diagnostics with:

```sh
PYTHONPATH=src python3 research/four_way/restricted_two_support_search.py \
  research/four_way/baseline_population.json \
  --output research/four_way/results/two_support_baseline.json
PYTHONPATH=src python3 research/four_way/restricted_two_support_search.py \
  research/four_way/results/diverse-pool18.json \
  --max-actions 18 --output research/four_way/results/two_support_diverse18.json
PYTHONPATH=src python3 research/four_way/restricted_support3_search.py \
  research/four_way/baseline_population.json --max-actions 6 \
  --grid-denominator 8 --output research/four_way/results/support3_baseline.json
```

These are numerical candidate generators, not complete algebraic support solvers; they do not search supports larger than three. Root tolerance and frequency rounding preclude an equilibrium claim, while the reported full-action deviation gap is exact for each rationalized mixture.

## Current status / what remains

No strategic population has been solved. Game 2's payoff depends on the final ranking against three opponents, so castle marginals do not make utility separable as in Game 1. Restricted dynamics, numerical support searches through size three, and exact fixed-mixture response checks exist, but they do not solve the nonlinear symmetric equilibrium conditions robustly. The exact response runner also supports `--max-support K`: it solves against the retained highest-mass actions and bounds the original response by `(1-delta)*BR(retained)+9*delta`, where `delta` is discarded mass. This helps only when the tail is tiny and the retained-mixture response is low; discarding half the equal six-action baseline's mass yields only the trivial 9-point upper bound. A global deviation bound is needed before any full-game equilibrium claim. Monte Carlo evaluation remains diagnostic only.

Tests cover multiset aggregation, the constant-sum invariant, support-two cubic roots, support-three derivatives, and the exact response kernel. They do not certify a Game 2 equilibrium.
