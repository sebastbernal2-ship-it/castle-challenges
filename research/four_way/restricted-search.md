# Game 2: restricted-population response search

## Exact full-action deviation oracle

`full_action_best_response.cpp` enumerates every legal allocation and every unordered opponent triple from a finite mixture. Castle points are compared as exact integer twelfths (`12` is divisible by each possible leader count 1–4); rank payouts are compared/averaged as integer quarters. Mixture probabilities use `long double`, not exact rationals, so reported expected values are numerical. For support size `K`, the intended work is `4,598,126 * C(K+2,3)` profile evaluations; underflow can still suppress extraordinarily small triple probabilities. `response_distribution.py` independently audits a fixed response over every positive-probability triple using exact fractions reconstructed from the decimal weights.

The Python rules were updated to use the same integer-twelfths score comparison. This avoids a subtle issue where two mathematically tied totals could compare unequal after different floating-point summation paths.

## Response expansion

Starting with equal mass on the even allocation and five corners, successive uniform additions of full-action best responses produced the response sequence and values in `results/restricted_search.json`. At supports 6–9, the best response still earned 8.27–8.40 payout against the current mixture.

A more strategic restricted search used multiplicative-weights/replicator dynamics over pools of 9, 10, and 11. The restricted dynamics concentrated on only a few pool actions. The full-action search printed responses with payout `9.0` at its floating-point precision. This does **not** mean the response wins every support profile; low-probability tails can create losses hidden by rounding. Treat these as highly exploitable mixtures, not exact 9-point guarantees.

These are negative results about the attempted restricted solver—not equilibrium estimates. They also reveal a serious support-generation challenge: best responses to small, artificial pools can exploit their structural holes spectacularly.

## Diversified support expansion

To test whether the failure was caused only by the corner-heavy initial pool, I built an 18-action pool containing the even allocation, all five corners, five hand-designed spreads, and seven actions discovered by prior response searches. Restricted multiplicative-weights dynamics ran for 10,000 iterations at `eta=0.02`. The full-action oracle selected `(21,24,28,25,2)` and rounded its expected payout to 9.0.

An exact-rational audit of that fixed response over **all 1,140** unordered triples found that it is not guaranteed first: payout 4 occurs with probability `5.0485586e-20`, and other lower payouts have smaller total mass. Its expected payout is `9 - 2.5242793e-19`, which rounds to 9.0 in ordinary double precision. Thus this is an extreme exploit, but not a literal always-win certificate. The exact payout distribution and rational audit are in `results/response_profile_audit.json`; reproduce with `response_distribution.py`.

The 18-action pool and dynamics output are saved in `results/diverse-pool18.json` and `results/replicator_runs/diverse-pool18.json`. This broader-pool test still fails to approach equilibrium; support diversity alone is not enough.

## Response-chain stress test

I mixed the first response into that 18-action mixture at 1%, 10%, and 30%, then searched the full action space. The same counter-strategy `(21,25,29,0,25)` had computed payouts 8.9989–9.0000. Adding successive responses increased support to 20 and 21; the replies `(22,26,30,0,22)` and `(23,27,31,0,19)` had computed payouts 8.9994 and 8.9985. These response-chain numbers were produced by the earlier double-precision runner and are rounded estimates, not rational certificates. The current runner uses long-double probabilities; the displayed four-decimal conclusions are unchanged. Results are in `results/response_chain.json`.

This response chain shows why naively adding one pure response is ineffective: it creates another exploitable response cycle and barely reduces the best-response payout. The restricted mixtures remain roughly 5.25 points above the symmetric-game value.

## Structural proof: no pure symmetric equilibrium

No allocation can be a symmetric pure Nash equilibrium.

Let all three opponents use the same allocation `a`.

- If `a_5 < 100`, deviating to `(0,0,0,0,100)` wins castle 5 and earns at least 5 castle points. Each opponent can earn at most `(1+2+3+4)/3 = 10/3` points from the other castles, since the three opponents tie there (and a zero-allocation tie with the deviator only reduces their share). The deviator is uniquely first and receives 9.
- If `a_5 = 100`, then `a=(0,0,0,0,100)`. Deviating to `(0,0,0,100,0)` earns 4 from castle 4 plus 1.5 from four-way ties on castles 1–3, total 5.5. Each incumbent earns `5/3 + 1.5 = 19/6`, so the deviator is uniquely first and receives 9.

Therefore any equilibrium must genuinely mix. This does not rule out mixed symmetric Nash equilibria, which exist for finite symmetric games.

## Current status

There is still no equilibrium. Exact best responses are now computationally feasible for modest finite supports, but full-game equilibrium search needs a robust method for constructing a broad mixed strategy and solving its nonlinear multiplayer equilibrium conditions. The restricted replicator outputs must not be used as recommendations.
