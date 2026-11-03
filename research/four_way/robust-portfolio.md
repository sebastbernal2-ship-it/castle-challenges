# Robustness checks and a finite-scenario portfolio

## Are the near-9 replies just numerical tails?

`support_threshold_audit.py` drops low-probability support actions, renormalizes the remainder, and exactly audits the fixed reply over all resulting opponent triples. Results are saved in `results/support_threshold_audit.json`.

- In pool 18, the reply `(21,24,28,25,2)` earns 9 against every triple in the six-action core (each retained action has probability at least `1e-8`). That core retains `0.999999999953` of the original mass.
- In pool 22, `(0,0,32,33,35)` earns 9 against every triple in the six-action core at cutoff `1e-16`; the full-support audit's lower payouts arise only in extremely low-mass tails.
- Pool 20 similarly has an all-9 core containing 7 actions and `0.999999999789` of its probability mass.
- Pool 19 is importantly different: `(21,25,29,0,25)` still loses on a material core profile. It pays 4 when the opponents draw `(0,10,20,30,40)` and two copies of `(21,24,28,25,2)`. This profile has probability `0.01618548`, explaining the audited expected payout `8.91907261`. Thus at least one response's losses are genuine counterplay, while several later near-9 responses are not explained by numerical tails.

These cutoffs are diagnostics, not changes to the original strategies. Every omitted mass is reported; a truncated-support guarantee says nothing about profiles involving omitted actions.

## Maximin portfolio against saved populations

I formed a finite meta-game whose row actions are the union of actions in the five saved pools (18 through 22), and whose columns are those five opponent populations. A row payoff is its expected tournament payout against three iid draws from that one population. Fictitious play in this 22-by-5 matrix produced a candidate portfolio. I then added two successive full-game replies to its candidate action set and reran the meta-game.

After 2,000,000 updates in the 24-action by 5-population meta-game, the portfolio put about `0.6875` on `(0,0,32,26,42)` and `0.3125` on `(22,27,31,0,20)`. Its estimated worst-scenario payout was `5.705795`; the meta-game duality gap was `0.001717`. Full portfolio and scenario results are in `results/robust_candidate_portfolio_round2_2m.json`.

This portfolio is not robust in the original game: exhaustive full-action search found `(0,0,33,27,40)`, which the exact-rational audit shows earns 9 against **all 20** opponent triples in the portfolio's support. The audit is `results/robust_candidate_portfolio_round2_2m_audit.json`. Adding that counteraction to the finite candidate set barely changed the portfolio and did not remove the deviation.

The meta-game only protects against the five selected populations and a finite row action set. Its maximin value is not an equilibrium value for the original symmetric multiplayer game. This experiment demonstrates that scenario robustness and full-game strategic stability are different objectives; no GTO strategy has been found.
