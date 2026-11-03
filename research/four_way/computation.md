# Game 2 computation log

## Exact finite-mixture expected payout

Added `games/four_way/best_response.py`. Given a finite population support of size `K`, it enumerates the `C(K+2,3)` unordered opponent triples, applies the correct multinomial weight for iid draws with replacement, and computes a candidate allocation's expected tournament payout exactly (up to floating point). This is exact only against the supplied mixture. `best_candidate` compares a caller-supplied action set; it is deliberately not called a full-game best-response oracle.

A diagnostic population was defined with equal probability on six allocations: `(20,20,20,20,20)` and the five single-castle corners. Exact expected payouts for selected candidate allocations:

| Candidate allocation | Expected payout against this six-action mixture |
|---|---:|
| `(20,20,20,20,20)` | 6.732639 |
| `(20,0,21,21,38)` | 7.708333 |
| `(0,0,0,45,55)` | 6.347222 |
| `(0,0,0,0,100)` | 5.850694 |
| `(0,0,25,25,50)` | 7.513889 |
| `(5,10,20,30,35)` | 8.048611 |

This population is an intentionally simple diagnostic, not an estimate of applicants and not an equilibrium. These values show why a generic/even allocation can be exploited by structured opponents; they do not identify a tournament-optimal or equilibrium strategy. Against four copies of the even allocation, `(20,0,21,21,38)` earns 9 points in that profile, illustrating a profitable response to a pure strategy (not to a mixed equilibrium).

## Current status / what remains

The evaluator now supports exact expected payoff against a finite support, but no strategic population has been solved. A full response search remains difficult: unlike Game 1, changing soldiers at one castle changes the player's total castle points and rank against each opponent triple, so the utility is not separable by castle. Restricted-support equilibrium computation and candidate search need to be added, and a global deviation bound is needed before any full-game equilibrium claim. The existing Monte Carlo evaluator is still only a sampling diagnostic.

Tests verify the multiset aggregation against explicit ordered-triple enumeration and verify the constant-sum payout invariant. They do not certify strategy quality.
