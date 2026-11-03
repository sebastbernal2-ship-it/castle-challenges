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

## 4. Compact path-flow formulation

The convex hull of legal allocations has an exact layered-network representation. At layer `i`, a node records the soldiers `s` already assigned to the first `i` castles. An arc labeled `x` goes from `(i,s)` to `(i+1,s+x)`, and paths run from `(0,0)` to `(5,100)`. A unit flow in this DAG is exactly a distribution over legal allocations; conversely any allocation mixture induces such a flow. There are only `5 * sum_{s=0}^{100}(101-s) = 25,755` arcs. The marginal probability of assigning `x` to castle `i` is the total flow on arcs in layer `i` labeled `x`.

Both players choose points in this path-flow polytope. Their payoff is a bilinear function of the projected castle marginals, with per-castle payoff matrix `v_i * (1[x>y] + 1/2 1[x=y])`. This avoids enumerating the 4.6 million path vertices when generating strategies. Entropic mirror-prox updates have Gibbs form `Pr(a) proportional to exp(sum_i theta_i[a_i])`; forward/backward sum-product DP computes the marginals and edge flows in `O(5*100^2)` per update. `mirror_prox_flow.cpp` implements this update and `run_mirror_prox_flow.py` decomposes the averaged flow into legal allocations before quantization and exact audit.

The formulation is exact, but the current solver is not yet effective: it uses floating-point updates and a probability floor for stability. Exact-audited candidates had gaps `0.17618056` (1,000 iterations, step 0.03), `4.41000924` (100,000, step 0.03), and `1.00263072` (200,000, step 0.0002), all worse than the incumbent. This demonstrates the compact representation, not a solved optimization; step-size control, convergence, and a useful saddle certificate remain open.

## 5. Caveats / research questions

- Ties score half the castle value exactly. This rule is encoded; verify it in the actual challenge.
- Strategies are independently randomized and hidden simultaneously. If the UI/game lets players observe allocations or draws without replacement, the model changes.
- A distribution that is strong against uniform random compositions is not thereby close to equilibrium.
- The DP best response finds a pure deviation. That suffices for exploitability against a mixed strategy because a linear objective over a simplex has a pure maximizer.
- This project has not yet computed an equilibrium. Do not present a guessed allocation as GTO.

## 6. What remains for a full solution

1. Stabilize a first-order saddle solver on the compact path-flow polytope (or use a convergent column-generation LP), and check it against the exact full-action DP gap at every checkpoint.
2. Turn the positive gap into a true certificate: either drive it to zero with exact rational primal/dual bounds, or report a rigorous epsilon-equilibrium bound. The current best exact gap is `30,514 / 40,000,520`.
3. Confirm challenge tie and sampling semantics. The current results certify only the encoded rules.
4. Do not label the current candidate GTO or an exact equilibrium.
