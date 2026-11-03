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

### Certified support truncation bound

For a rationalized mixture `p`, retain a subset of support mass `1-delta` and renormalize it to `p_R`; write `p=(1-delta)p_R+delta p_T`. Since every action's payout lies in `[0,9]`, the global response value satisfies

`BR(p) <= (1-delta) BR(p_R) + 9 delta`.

Thus an exact full-action oracle on a small retained support plus the discarded mass gives a rigorous upper bound for the original mixture, without pretending the truncated best response is exact for it. More generally, for the exact input distribution `p` and the retained oracle distribution `r`, compute their exact total variation distance `tau`; then `max(0, BR(r)-9*tau-3.75) <= exploitability(p) <= min(9, BR(r)+9*tau)-3.75`. The runner reports this interval, accounting for both probability quantization and support pruning. It is useful only when `tau` is small and `BR(r)` is itself low; on the equal six-action baseline, retaining half the mass only recovers the trivial bound.

## 4. Structure and useful invariants

- Castle points sum to 15 in every profile, since each castle's value is fully allocated among its leaders.
- Rank payouts also sum to 15 in every profile. These are strong implementation invariants.
- Players can receive fractional castle totals and fractional rank payouts; floating comparisons should not silently merge distinct scores. Use integer-scaled/rational score arithmetic for deterministic rules if practical.
- A player's allocation affects both the castle points it wins and the point totals/rank order against three opponents. There is no independent-per-castle additive utility or simple marginal DP analogous to Game 1.
- With iid opponents from `p`, the objective is a symmetric four-player constant-sum game. Its symmetric equilibrium payoff is fixed at 3.75, but its strategy is not fixed by that fact.

## 5. Complete symmetric double-oracle method

Game 2 is not a two-player zero-sum LP, but a mathematically complete finite-game method is available in principle: a **symmetric Nash double oracle**, with an exact solver for each restricted game and an exact global best-response oracle.

For a finite action pool `P`, define the exact payoff tensor `T[i,j,k,l] = U(a_i,a_j,a_k,a_l)`. Against a symmetric mixed strategy `p` on `P`, the payoff to pure action `a_i` is the cubic polynomial

`g_i(p) = sum_{j,k,l in P} T[i,j,k,l] p_j p_k p_l`.

Since every realized profile distributes the 15-point pool and the game is symmetric, a symmetric equilibrium has payoff `15/4`. Its complementarity conditions are

- `p_i >= 0`, `sum_i p_i = 1`;
- `g_i(p) <= 15/4` for every action in `P`;
- `p_i * (15/4 - g_i(p)) = 0` for every `i`.

A complete restricted-game solver can enumerate supports `S subset P`, solve `g_i(p)=15/4` for `i in S` together with normalization, and certify positivity and all off-support inequalities. The equations have rational coefficients (the implemented payout rule has exact quarter-point payouts); a real-algebraic solver such as CAD/root isolation can, in principle, certify all required real solutions. Numerical homotopy or nonlinear optimization is useful for finding candidates but is not by itself a completeness certificate.

For each restricted equilibrium `p`, run a **full-action** best-response oracle against the three independent draws from `p`. If a pure response earns more than `15/4`, add it to `P` and solve the expanded restricted game. A profitable full-game response cannot already be in `P`, because `p` is a restricted equilibrium. Thus the pool strictly grows on every unsuccessful exact iteration; because the action set is finite, this procedure terminates in at most `|A|` additions. When the global oracle finds no profitable deviation, the restricted equilibrium is a full-game symmetric Nash equilibrium. The worst case is intractable—the method can require millions of actions and solving high-degree systems—but it is a genuine complete algorithm, unlike restricted replicator dynamics.

The exact best-response oracle can enumerate all 4,598,126 allocations and evaluate each against the unordered opponent triples with multiplicities 1/3/6. For a rational frequency strategy, use integer triple weights and quarter-point utilities (arbitrary-precision integers if needed), so response comparisons are exact. With support size `K`, the straightforward cost is `O(|A| K^3)`; reducing this cost or deriving certified branch-and-bound upper bounds is the central computational obstacle. Any approximate early stop must report a rigorous global upper bound on deviation payoff, not just the best response found.

## 6. Implementation status and next work

- `rules.py` scores a realized profile with exact integer score comparisons and quarter-point rank payouts.
- `full_action_best_response.cpp` is the long-double candidate generator. The new `exact_full_action_best_response.cpp` enumerates all 4,598,126 actions and compares expected payouts with exact integer numerators for an integer-frequency mixture; `run_exact_full_best_response.py` performs probability quantization and invokes it. With frequency total at most `10^12`, the numerator is bounded by `36 N^3`, which fits unsigned 128-bit arithmetic. Complexity is `O(|A| K^3)`, so it is useful for small support but not yet for the large mixtures found by population search.
- `response_distribution.py` gives exact rational audits of the payout distribution for a **supplied response**. It does not prove that response is globally optimal.
- The exact oracle was checked on the six-action baseline with equal frequencies (`N=1,000,002`): it returns `(1,21,21,21,36)` with exact expected payout `33611312778181111380 / 4000024000048000032 = 8.402777777...`. This is a fixed-mixture global best-response calculation, not an equilibrium certificate.
- `restricted_two_support_search.py` enumerates pure and two-action supports in a finite pool, isolates cubic indifference roots numerically, rationalizes each root, and exact-audits it against all 4,598,126 actions. The best candidate on both the six-action baseline and 18-action diverse pool has exact exploitability `21/4 = 5.25`.
- `restricted_support3_search.py` adds multi-start Newton for the two indifference equations on each three-action support, checks the restricted pool inequalities, then exact-audits surviving candidates globally. On the six-action baseline it found a restricted support-three equilibrium, but its exact full-game gap is still `21/4 = 5.25`; the global best response is `(20,21,21,0,38)`. This is a useful failure certificate for that restricted pool, not a full-game result. See `results/support3_baseline.json`.
- Both support solvers use numerical root search and are not complete algebraic solvers. Restricted pools and replicator/portfolio experiments remain diagnostics. The next implementation step is certified support solving beyond size three, followed by the expanding-pool loop above. The exact oracle's cubic support cost and the enormous support search are the main bottlenecks.

No Game 2 equilibrium has been computed. The complete method is specified, an exact response-oracle component exists, and numerical restricted support searches through size three are implemented. A certified restricted polynomial solver for general supports and a scalable global oracle remain unfinished. Do not label current results GTO.
