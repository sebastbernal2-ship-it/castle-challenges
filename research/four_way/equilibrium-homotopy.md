# Game-theoretic structure and an equilibrium homotopy route

Game 2 is a finite symmetric four-player constant-sum game. Let `A` be its legal allocations and let `G_a(p)` be the expected payout from action `a` against three iid draws from `p`.

## Exact equilibrium condition

For every normalized `p`, symmetry and total payout 15 give

\[
\sum_{a\in A}p_aG_a(p)=15/4.
\]

Consequently `p` is a symmetric Nash equilibrium iff `G_a(p) <= 15/4` for every legal `a`. If `p_a>0`, then necessarily `G_a(p)=15/4`. This is a cubic complementarity problem: the `G_a` are homogeneous cubics before imposing `sum(p)=1`. It is not a linear program; replacing `p^{\otimes3}` by an arbitrary opponent-triple distribution relaxes away the iid constraint and can produce correlated-coalition strategies that are not Nash strategies.

## A useful exact theorem: no pure symmetric equilibrium

If all players choose the same allocation `a`, each scores `15/4` and receives `15/4`. If `a_5<100`, deviating to `(0,0,0,0,100)` wins castle 5 outright and scores at least 5; the three opponents each score `(15-S)/3 < 15/4`, where `S>=5` is the deviator's score. The deviation therefore pays 9. If `a_5=100`, deviation to `(25,25,25,25,0)` wins castles 1–4 and scores 10, again paying 9. Thus **every pure symmetric profile is exploitable for the maximum payout 9**. Any symmetric equilibrium must genuinely mix.

This rules out pure-action fixed-point searches as a solution, though pure profiles are useful starting points for a continuation method.

## Proposed game-theoretic route: trace equilibria from a strict-dominance game

Choose a starting action `a0`, for example `(20,20,20,20,20)`, and a nonnegative cost `c` on allocations with `c(a0)=0`. Define a symmetric constant-sum auxiliary game

\[
U_i^0(a_1,a_2,a_3,a_4)=15/4-\lambda c(a_i)
   + (\lambda/3)\sum_{j\ne i}c(a_j),\qquad \lambda>0.
\]

The four payoffs sum to 15 profile by profile. Against any opponent strategies, choosing `a` rather than `a0` changes a player's expected auxiliary payoff by exactly `-lambda*c(a)`, so `a0` is strictly dominant and `delta_(a0)` is the unique equilibrium at `t=0`. Interpolate to the actual game by

\[
U_i^t=(1-t)U_i^0+tU_i,\qquad 0\le t\le1.
\]

At each `t`, track a symmetric equilibrium support `S(t)`. On a fixed support, solve the cubic indifference equations `G_a^t(p)=15/4` for `a in S(t)`, with `sum(p)=1`. When a support probability reaches zero, remove that action; when an excluded action reaches payoff `15/4`, add it. A full-action best-response oracle is the separation step that detects omitted entering actions. At `t=1`, an exact audit of all allocations certifies the result.

This is an equilibrium homotopy/active-set method, not global minimization from random starts. A generic homotopy and branch handling are essential: following one arbitrary local root is not a proof that the path reaches `t=1`. The final full-game inequalities remain the certificate.

### Hand-calculated first pivot

For `a0=(20,20,20,20,20)`, let `a1=(19,20,20,20,21)`. Against three `a0` players, `a1` wins and pays 9, so its target-game gain over `a0` is `9-15/4=21/4`. Set `c(a1)=1` and `c(a)=2` for every other `a != a0,a1`. Since no target-game gain can exceed `21/4`, `a1` is the unique first action to enter the homotopy support, at

\[
t_1=\frac{\lambda}{\lambda+21/4}.
\]

Against a profile with exactly `k` of the three opponents using `a1` and the rest using `a0`, the target-game payoffs are

| `k` | 0 | 1 | 2 | 3 |
|---:|---:|---:|---:|---:|
| own `a0` | 3.75 | 2 | 1 | 0 |
| own `a1` | 9 | 6.5 | 5 | 3.75 |

Thus `a1` strictly beats `a0` throughout this two-action restricted game. This gives an exact first homotopy segment, but not a full-game equilibrium: the pure profile `a1` is itself exploitable by the theorem above. The next support event must bring in further allocations.

## Implemented auxiliary-response continuation probe

`exact_auxiliary_best_response.cpp` and `trace_auxiliary_homotopy.py` now implement a numerical fixed-`t` continuation/column-generation probe with an exact full-action response oracle. To break broad payoff ties, the experiment uses

\[
c(a_0)=0,\quad c(a_1)=1,\quad
c(a)=2+\frac{a_1+2a_2+3a_3+4a_4+5a_5}{5000}
\]

for other allocations. The cost perturbation does not change the target game at `t=1`; at `t=0`, `a0` remains uniquely dominant. The auxiliary oracle ranks all legal allocations exactly for a quantized mixture and rational `t`.

On the two-action branch `{a0,a1}`, the numerical indifference continuation puts about `0.728` mass on `a1` near `t=0.1996`. At that point `(58,21,0,21,0)` is an omitted action reaching the auxiliary equilibrium payoff (within quantization error); it pays 9 in the target game. This demonstrates that the homotopy encounters new full-game responses very early, not just at its endpoint.

A fixed-parameter experiment at `t=0.202` did not close the auxiliary-game gap. The exact-response expansion repeatedly changed support; retaining 248 discovered columns reduced the largest audited auxiliary payoff gap to about `0.0070`, but subsequent rounds remained around `0.008`. A multi-start refit on a 259-action pool lowered the exact auxiliary gap to `0.00526` (support size 22; best omitted response `(67,0,0,0,33)`). A mixture over the earlier active-support history had gap `0.00793`. These are auxiliary-game gaps, **not** target-game exploitability certificates. The best full audit checkpoint is `results/auxiliary_homotopy/t0202-best.json`.

This is useful progress on implementing the proposed path, but it also exposes its difficulty: even a nearby homotopy slice has many changing responses, and the column-generation branch can cycle. No endpoint at `t=1` has been reached, and this does not solve Game 2.

## What the exploratory checks rule out

- Comparing actions coordinatewise against the current 55-action support leaves 3,057,040 exact payoff classes, only a modest reduction from 4,598,126 allocations.
- Within that 55-action support, no action is purely dominated across its 29,260 opponent triples. A floating-point LP check also found no weak domination by mixtures of the other support actions; this is a diagnostic, not an exact certificate.
- A one-step active-support root from the saved mixture plus its exact best response produced negative probabilities; pivoting to a smaller restricted support gave a full-game gap about `0.780`. This confirms the need for systematic branch/path handling rather than dropping all negative coordinates and calling the result an equilibrium.
- A restricted logit-QRE continuation was also tested. Its limit branch approached restricted equilibria but retained a large full-game response gap; it is not currently a better route.

No Game 2 equilibrium has been found. The homotopy above is a concrete next method, not a claim of success. Any endpoint must still pass the exact global-response audit.
