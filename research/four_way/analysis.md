# Game 2 — mathematical analysis and solver plan

## 1. Formal game

Each player chooses `a in A`, where `A={a in Z_+^5: sum_i a_i=100}`. For castle `i`, let `M_i=max_j a_{ji}`. If `k_i` players attain the maximum, each receives `v_i/k_i`; a player's castle-point total is the sum of those shares. Rank players by total castle points. A tie occupying rank positions `r..s` receives the average of payouts in those positions, from `(9,4,2,0)`.

For every realized four-player profile, rank payouts sum to 15 (rank ties redistribute positions but do not change the pool). This is a symmetric constant-sum four-player normal-form game, not a two-player zero-sum matrix game. A symmetric mixed equilibrium `p` must satisfy

`E_{a~p,b,c~p} U(x,a,b,c) <= E_{x,a,b,c~p} U(x,a,b,c)`

for every pure deviation `x`, where all draws are independent. Symmetry implies every player's equilibrium expected payout is `15/4=3.75`. The equilibrium distribution need not be unique; other concepts (evolutionary stability, field-specific expected payout, robust performance) are distinct objectives.

## 2. Why naive “all combinations” simulation is not an equilibrium method

There are 4,598,126 pure allocations. Sampling random allocations measures payoff against the chosen sampling distribution, not strategic stability. Even sampling all pure actions as a uniform opponent baseline does not model rational opponents. Four-way outcomes also depend on joint ranks, not just each castle's marginal win probability. A solver must search for profitable deviations against its own candidate population and establish a small deviation gap.

## 3. Exact evaluation of a finite mixed strategy

Given a finite support `S` and probabilities `p`, expected payoff of a deviation `x` can be computed by summing over all ordered opponent triples in `S^3`:

`BRpayoff(x;p) = sum_{a,b,c in S} p_a p_b p_c U(x,a,b,c)`.

This is exact but cubic in support size per deviation. Cache opponent triples and their weights; exploit symmetry to aggregate unordered multisets with multiplicity (three draws with replacement). Evaluate all pure deviations only if feasible, or develop an exact branch-and-bound / specialized search with a certified upper bound. Heuristics can find deviations but cannot certify equilibrium. An approximate equilibrium certificate requires a valid upper bound on the best deviation as well as a lower bound from a found action.

## 4. Structure and useful invariants

- Castle points sum to 15 in every profile, since each castle's value is fully allocated among its leaders.
- Rank payouts also sum to 15 in every profile. These are strong implementation invariants.
- Players can receive fractional castle totals and fractional rank payouts; floating comparisons should not silently merge distinct scores. Use integer-scaled/rational score arithmetic for deterministic rules if practical.
- A player's allocation affects both the castle points it wins and the point totals/rank order against three opponents. There is no independent-per-castle additive utility or simple marginal DP analogous to Game 1.
- With iid opponents from `p`, the objective is a symmetric four-player constant-sum game. Its symmetric equilibrium payoff is fixed at 3.75, but its strategy is not fixed by that fact.

## 5. Solver research plan

1. Lock down actual tie rule, group sampling (with/without replacement), and whether all applicants are exchangeable.
2. Build exact profile scoring with rational comparisons and exhaustive small-instance tests.
3. Implement support-based expected payoff calculation and exact opponent-triple aggregation.
4. Generate candidate actions using structural search (local soldier transfers, multistart search, evolutionary proposals, and perhaps constraint/MIP formulations); use them to discover deviations, not certify absence of deviations.
5. For restricted support games, solve symmetric equilibrium conditions / regret minimization and add discovered deviations. A finite restricted-game equilibrium alone says nothing about actions outside its support.
6. Pursue a full-game deviation certificate (branch-and-bound, integer optimization, or rigorous upper bounds). If unavailable, report an empirical best-response gap and clearly label it uncertified.
7. Validate candidate populations on independent seeds and broader deviation search; separate equilibrium claims from performance against an estimated applicant field.

## 6. Status

No equilibrium has been computed. Current Monte Carlo baseline code is a smoke-test and benchmark helper only. It is not evidence for GTO play.
