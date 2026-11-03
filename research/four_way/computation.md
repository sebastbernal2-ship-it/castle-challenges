# Game 2 computation log

## Finite-mixture expected payout

Added `games/four_way/best_response.py`. Given a finite population support of size `K`, it enumerates the `C(K+2,3)` unordered opponent triples, applies the correct multinomial weight for iid draws with replacement, and numerically computes a candidate's payout against that supplied mixture. `best_candidate` compares a caller-supplied action set; it is deliberately not a full-game best-response oracle. `response_distribution.py` audits a fixed strategy with exact rational arithmetic over decimalized input weights.

A diagnostic population was defined with equal probability on six allocations: `(20,20,20,20,20)` and the five single-castle corners. Exact expected payouts for selected candidate allocations:

| Candidate allocation | Expected payout against this six-action mixture |
|---|---:|
| `(20,20,20,20,20)` | 6.732639 |
| `(20,0,21,21,38)` | 7.708333 |
| `(0,0,0,45,55)` | 6.347222 |
| `(0,0,0,0,100)` | 5.850694 |
| `(0,0,25,25,50)` | 7.513889 |
| `(5,10,20,30,35)` | 8.048611 |

This population is an intentionally simple diagnostic, not an estimate of applicants and not an equilibrium. The exhaustive full-action search over all 4,598,126 allocations finds `(1,21,21,21,36)`, with numerically computed payout `8.402778` against that mixture. Since symmetric self-play has expected payout 3.75, the diagnostic mixture has a pure deviation gain of about `4.652778` points. Add this response at equal mass to the six original actions and rerun the full-action search: the next response is `(2,1,22,22,53)`, with payout `8.291545` against the resulting seven-action mixture. This confirms the baseline is extremely far from equilibrium; it does not by itself produce a convergent learning process. Full outputs are in `results/full_action_responses.json`.

Against four copies of the even allocation, `(20,0,21,21,38)` earns 9 points in that profile, illustrating a profitable response to a pure strategy (not to a mixed equilibrium).

## Further search and structural result

The follow-up restricted replicator plus full-action oracle experiments are documented in `restricted-search.md`. On 9-, 10-, and 11-action pools, the restricted dynamics produced mixtures for which the exhaustive response search printed `9.0` at floating-point precision. This does not mean the action earns 9 against every support triple; see the rational payout audit in `restricted-search.md`. These results demonstrate extreme restricted-support exploitability, not progress toward a solved equilibrium.

A pure symmetric allocation cannot be a Nash equilibrium; the direct deviation proof is in `restricted-search.md`. Any equilibrium must genuinely mix.

A native C++ restricted multiplicative-weights implementation was added in `restricted_replicator.cpp` with a Python runner. On the six-action diagnostic pool, its 1,000-step probabilities agree with the Python reference to within `5.6e-16`. It enabled a support-expansion stress test: restricted-pool payoff gaps fell below `1e-14` on 24 actions, while the full-action reply was still 8.8482; adding that reply led to another pool with a near-9 deviation. See [`double-oracle.md`](double-oracle.md) and `results/double_oracle_chain.json`. This is a strong failure diagnostic for fixed-pool methods, not an equilibrium computation.

## Current status / what remains

The evaluator exhaustively sums profile payouts against a finite support using floating-point mixture weights, but no strategic population has been solved. A full response search remains difficult: unlike Game 1, changing soldiers at one castle changes the player's total castle points and rank against each opponent triple, so the utility is not separable by castle. The restricted-support dynamics and candidate generation now exist, but they do not solve the nonlinear symmetric equilibrium conditions robustly. A global deviation bound is still needed before any full-game equilibrium claim. The existing Monte Carlo evaluator is still only a sampling diagnostic.

Tests verify the multiset aggregation against explicit ordered-triple enumeration and verify the constant-sum payout invariant. They do not certify strategy quality.
