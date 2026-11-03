# Four-Way double-oracle stress test

## Procedure

Starting from the diversified 18-action population, I repeatedly (1) ran restricted multiplicative-weights dynamics on the current pool, (2) measured the maximum pure-action payoff within that pool against its time-average mixture, (3) exhaustively searched all 4,598,126 legal allocations for a full-game reply, and (4) appended that reply to the pool. The native solver evaluates integer-quarter profile payoffs and runs 10,000 or 100,000 updates at `eta=0.02`. The full-action oracle uses long-double probabilities; the fixed-response audits use exact fractions reconstructed from the stored decimal weights.

This is a diagnostic double-oracle loop, not a certified equilibrium method: restricted multiplicative weights can cycle, last-half averages are finite-time estimates, and best-response expected values from the C++ search remain floating-point computations. The exact audits certify the payoffs of the listed responses against their saved mixtures, not that those responses are globally optimal under exact rational arithmetic.

## Results

| Pool | MW iterations | Estimated max payoff within pool | Full-action reply | Audited expected payout | Probability reply gets less than 9 |
|---:|---:|---:|---|---:|---:|
| 18 (starting population) | 10,000 | 3.75335914 | `(21,24,28,25,2)` | `9 - 2.5243e-19` | `5.0486e-20` |
| 19 | 10,000 | `3.75000000012` | `(21,25,29,0,25)` | `8.919072608999207` | `0.01618548` |
| 20 | 10,000 | `3.75003684429` | `(6,26,30,32,6)` | `8.999999999598376` | `1.2684e-10` |
| 21 | 100,000 | `3.75000573600` | `(22,27,31,0,20)` | `8.99999999102311` | `1.7954e-9` |
| 22 | 100,000 | `3.75000311354` | `(0,0,32,33,35)` | `9 - 8.8366e-55` | `1.1636e-55` |
| 23 | 100,000 | within `3e-15` | `(23,28,33,0,16)` | `8.997811132739372` | `0.00043777` |
| 24 | 100,000 | within `5e-16` | `(1,29,34,34,2)` | `8.84818476390958` | `0.05599083` |
| 25 | 500,000 | `3.4506e-7` | `(24,30,35,0,11)` | `9 - 2.0953e-10` | `4.1906e-11` |

At each round, the exact expected payout is computed by `response_distribution.py` from the saved mixture weights; full payout histograms and exact rational totals are in `results/double_oracle_round*_audit.json`. Mixture files and native solver settings are in `results/replicator_runs/diverse-pool{19,20,21,22,23,24,25}-*.json`.

## Interpretation

The first added full-game reply reduced the next deviation's value from essentially 9 to 8.9191. A later expansion to 24 actions produced a materially stronger counter-mixture: the best response fell to 8.8482, with 5.6% probability of payouts below 9. Its largest losses involve the castle-4 corner, castle-5 corner, and the preceding response, so this is genuine high-mass counterplay rather than a numerical tail. But after adding that response and re-solving, the best response returned to essentially 9 at pool size 25. Pool 25's restricted gap is about `3.5e-7`, yet its full-action response still earns `9 - 2.1e-10`.

The deviation value therefore does not improve monotonically with support expansion: one round reduced it materially, then the next response cycle restored a near-certain first-place deviation. Restricted-pool stability remains a poor proxy for full-game stability. This is evidence against the current support-generation procedure, not evidence that the game has no mixed equilibrium. The results also illustrate why numerical values near 9 need exact fixed-response auditing: a reported `9.0` may conceal small losses, and long-double output cannot resolve gaps below its precision.
