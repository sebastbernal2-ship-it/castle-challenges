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

## 4. Caveats / research questions

- Ties score half the castle value exactly. This rule is encoded; verify it in the actual challenge.
- Strategies are independently randomized and hidden simultaneously. If the UI/game lets players observe allocations or draws without replacement, the model changes.
- A distribution that is strong against uniform random compositions is not thereby close to equilibrium.
- The DP best response finds a pure deviation. That suffices for exploitability against a mixed strategy because a linear objective over a simplex has a pure maximizer.
- This project has not yet computed an equilibrium. Do not present a guessed allocation as GTO.

## 5. Next implementation steps

1. Implement exact marginal payoff tables and DP, test against brute-force enumeration for small soldier counts and sampled 100-soldier cases.
2. Add restricted matrix-game LP as an optional `scipy` solver dependency (or implement rational simplex for final small supports).
3. Add double-oracle orchestration, dominated/redundant strategy checks, and deterministic result serialization.
4. Run multiple initial supports; independently verify each result with the exact DP oracle and report exploitability.
5. Analyze support geometry and sensitivity to challenge-rule ambiguities.
