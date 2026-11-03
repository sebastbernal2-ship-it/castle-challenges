# Game 1 — mathematical analysis and solver plan

## 1. Formal game

Let `A = {a in Z_+^5 : sum_i a_i = 100}` and castle values `v=(1,2,3,4,5)`. For pure allocations `a,b`, define

`u(a,b) = sum_i v_i [1(a_i>b_i) + 1/2 1(a_i=b_i)]`.

Then `u(a,b)+u(b,a)=15` for every pair, including ties. The centered payoff `g(a,b)=u(a,b)-7.5` is antisymmetric. Thus Game 1 is a finite symmetric constant-sum (equivalently, zero-sum after centering) game. A symmetric equilibrium is a mixed strategy `p` satisfying `E_{a~p} u(a,b) <= 7.5` for every pure deviation `b`; the equilibrium value is 7.5 in original score units. Multiple equilibrium distributions may exist.

The pure strategy count is `C(104,4)=4,598,126`; a dense payoff matrix would contain about 21.1 trillion entries. Enumerating or storing it is not a viable baseline.

## 2. Exact best response against a mixed population

The payoff is additive by castle. If the opponent distribution is `p`, let `F_i(x)=Pr_{b~p}(b_i<x)` and `m_i(x)=Pr_{b~p}(b_i=x)`. The expected contribution from assigning `x` soldiers to castle `i` is exactly

`q_i(x)=v_i * (F_i(x) + m_i(x)/2)`.

Therefore the exact pure best response is

`max_{x_1+...+x_5=100, x_i>=0 integer} sum_i q_i(x_i)`.

A dynamic program over castles and soldier totals computes this in `O(5*100^2)` time and `O(100)` memory. This is an exact oracle, not a Monte Carlo estimate. It is the key primitive for a restricted-game / double-oracle method.

For a finite opponent sample, estimate `F_i,m_i` from its empirical marginal counts; then the DP is exact against that empirical distribution. In column generation, use exact weights of the current mixed strategy, not samples.

## 3. Restricted-game equilibrium and certificates

Start with a strategically diverse restricted strategy set `S`. Build only its payoff matrix, solve its zero-sum matrix game, and compute an exact DP best response to each equilibrium mixture. Add a best response when it violates the equilibrium inequality; repeat. For a candidate mixture `p`, define exploitability gap

`epsilon = max_{b in A} E_{a~p} u(b,a) - 7.5`.

By antisymmetry, this is the maximum profitable pure deviation over the baseline value. If the exact oracle returns `epsilon <= tolerance`, the mixture is an epsilon-equilibrium against the entire 4.6-million-action game, regardless of whether the restricted matrix itself has converged. Exact arithmetic/rational LP output is preferable for a final certificate; floating LP tolerances and tie handling must be reported otherwise.

Restricted-game LP (centered payoffs `G[j,k]=u(s_j,s_k)-7.5`): find `p>=0, sum p=1` maximizing `z` subject to `sum_j p_j G[j,k] >= z` for every restricted opponent action `s_k`. The security value is at least zero due symmetry; the full-game best-response oracle checks all omitted actions.

### Exact equilibrium certificate under the encoded rules

`results/exact-equilibrium-flow-lp.json` gives a legal 194-allocation mixture with integer frequency total 410. Its exact marginal counts are particularly simple (each row totals 410): castle 1 has counts 50 on even soldiers `0..12` and 10 on odd soldiers; castle 2 has 20 on even `0..26` and 10 on odd; castle 3 has count 10 at every soldier count `0..40`; castle 4 has 5 on even `0..54` and 10 on odd; castle 5 has 2 on even `0..68` and 10 on odd. The saved path-flow coupling proves these marginals arise from legal allocations summing to 100.

The exact integer-DP verifier checks every legal opponent allocation and returns best-response score `6150/820 = 7.5`, exploitability `0/820`, and one best response `(12,26,40,22,0)`. Since the game is symmetric and constant-sum 15, the self-play value is 7.5; this zero-gap full-action certificate proves the saved mixture is a Nash equilibrium for the encoded Game 1 rules. Reproduce the audit with `PYTHONPATH=src python3 research/head_to_head/verify_strategy.py research/head_to_head/results/exact-equilibrium-flow-lp.json`.

## 4. Compact path-flow formulation

The convex hull of legal allocations has an exact layered-network representation. At layer `i`, a node records the soldiers `s` already assigned to the first `i` castles. An arc labeled `x` goes from `(i,s)` to `(i+1,s+x)`, and paths run from `(0,0)` to `(5,100)`. A unit flow in this DAG is exactly a distribution over legal allocations; conversely any allocation mixture induces such a flow. There are only `5 * sum_{s=0}^{100}(101-s) = 25,755` arcs. The marginal probability of assigning `x` to castle `i` is the total flow on arcs in layer `i` labeled `x`.

Both players choose points in this path-flow polytope. Their payoff is a bilinear function of the projected castle marginals, with per-castle payoff matrix `v_i * (1[x>y] + 1/2 1[x=y])`. This avoids enumerating the 4.6 million path vertices when generating strategies. Entropic mirror-prox updates have Gibbs form `Pr(a) proportional to exp(sum_i theta_i[a_i])`; forward/backward sum-product DP computes the marginals and edge flows in `O(5*100^2)` per update. `mirror_prox_flow.cpp` implements this update and `run_mirror_prox_flow.py` decomposes the averaged flow into legal allocations before quantization and exact audit.

The earlier mirror-prox implementation used floating-point updates and a probability floor for stability; its tested candidates had positive gaps and did not solve the game. A different cutting-plane LP on the same path-flow polytope has since produced the exact certificate above.

## 5. Caveats / research questions

- Ties score half the castle value exactly. This rule is encoded; verify it in the actual challenge.
- Strategies are independently randomized and hidden simultaneously. If the UI/game lets players observe allocations or draws without replacement, the model changes.
- A distribution that is strong against uniform random compositions is not thereby close to equilibrium.
- The DP best response finds a pure deviation. That suffices for exploitability against a mixed strategy because a linear objective over a simplex has a pure maximizer.
- The saved strategy is an exact equilibrium only for the encoded rules. Confirm those rules against the actual challenge before calling it the challenge's definitive answer.

## 6. What remains for a full solution

1. Confirm challenge tie and sampling semantics; the proof certifies the rules encoded here.
2. Preserve the exact mixture, rational marginals, integer path-flow coupling, and full-action verifier output as the reproducible equilibrium certificate.
3. Game 2 remains unsolved; its multiplayer ranking payoffs do not reduce to this marginal LP.
