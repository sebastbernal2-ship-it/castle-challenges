# Game 2: restricted-population response search

## Exact full-action deviation oracle

`full_action_best_response.cpp` enumerates every legal allocation and every unordered opponent triple from a finite mixture. Castle points are compared as exact integer twelfths (`12` is divisible by each possible leader count 1–4); rank payouts are compared/averaged as integer quarters. Only mixture probabilities use floating point. For support size `K`, work is `4,598,126 * C(K+2,3)` profile evaluations.

The Python rules were updated to use the same integer-twelfths score comparison. This avoids a subtle issue where two mathematically tied totals could compare unequal after different floating-point summation paths.

## Response expansion

Starting with equal mass on the even allocation and five corners, successive uniform additions of full-action best responses produced the response sequence and values in `results/restricted_search.json`. At supports 6–9, the best response still earned 8.27–8.40 payout against the current mixture.

A more strategic restricted search used multiplicative-weights/replicator dynamics over a pool of 9, then added its full-game best response and reran over pools of 10 and 11. The restricted dynamics concentrated on only a few pool actions. In each case, exhaustive search of all 4,598,126 actions found a response worth the maximum possible payout, 9.0, against every triple in the tested mixture's support. Thus these restricted strategies are not close to full-game equilibrium despite their within-pool dynamics.

These are negative results about the attempted restricted solver—not equilibrium estimates. They also reveal a serious support-generation challenge: best responses to small, artificial pools can exploit their structural holes spectacularly.

## Diversified support expansion

To test whether the failure was caused only by the corner-heavy initial pool, I built an 18-action pool containing the even allocation, all five corners, five hand-designed spreads, and seven actions discovered by prior exact response searches. Restricted multiplicative-weights dynamics ran for 10,000 iterations at `eta=0.02`. Its time-average mixture still had a full-action best response `(21,24,28,25,2)` earning the maximum payout 9.0 across 1,104 unordered opponent triples.

The complete 18-action pool, dynamics output, and response summary are saved in `results/diverse-pool18.json`, `results/replicator_runs/diverse-pool18.json`, and `results/diverse_pool18_response.json`. The response was independently checked by the Python exact finite-mixture evaluator. This broader-pool test still fails to approach equilibrium; support diversity alone is not enough.

## Response-chain stress test

I mixed the first 9-point response into that 18-action mixture at 1%, 10%, and 30%, then exhaustively searched all legal responses. The same counter-strategy `(21,25,29,0,25)` remained worth 8.9989–9.0000. Adding successive responses with equal 10% mass (while retaining 70–80% of the base mixture) increased support to 20 and 21; the best replies `(22,26,30,0,22)` and `(23,27,31,0,19)` still earned 8.9994 and 8.9985. The calculations are saved in `results/response_chain.json`.

This shows why naively adding one pure response is ineffective: it creates another exploitable response cycle and barely reduces the maximum payoff. The restricted mixture remains far from equilibrium by over five payout points.

## Structural proof: no pure symmetric equilibrium

No allocation can be a symmetric pure Nash equilibrium.

Let all three opponents use the same allocation `a`.

- If `a_5 < 100`, deviating to `(0,0,0,0,100)` wins castle 5 and earns at least 5 castle points. Each opponent can earn at most `(1+2+3+4)/3 = 10/3` points from the other castles, since the three opponents tie there (and a zero-allocation tie with the deviator only reduces their share). The deviator is uniquely first and receives 9.
- If `a_5 = 100`, then `a=(0,0,0,0,100)`. Deviating to `(0,0,0,100,0)` earns 4 from castle 4 plus 1.5 from four-way ties on castles 1–3, total 5.5. Each incumbent earns `5/3 + 1.5 = 19/6`, so the deviator is uniquely first and receives 9.

Therefore any equilibrium must genuinely mix. This does not rule out mixed symmetric Nash equilibria, which exist for finite symmetric games.

## Current status

There is still no equilibrium. Exact best responses are now computationally feasible for modest finite supports, but full-game equilibrium search needs a robust method for constructing a broad mixed strategy and solving its nonlinear multiplayer equilibrium conditions. The restricted replicator outputs must not be used as recommendations.
