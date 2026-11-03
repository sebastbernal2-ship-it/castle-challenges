# Game 2 research: Four-Way Battle

Keep Game 2-specific experiments, solver implementations, population models, and conclusions here.

Suggested progression:
1. Validate rank and payout tie semantics against the challenge.
2. Define the equilibrium/optimization target (symmetric Nash, evolutionary stability, or field-specific expected payout).
3. Implement reproducible group simulation and sampled deviation search.
4. Track uncertainty, population assumptions, and best-response gaps.

Latest findings and solver limitations: [`analysis.md`](analysis.md), [`restricted-search.md`](restricted-search.md), [`double-oracle.md`](double-oracle.md), [`robust-portfolio.md`](robust-portfolio.md), and [`computation.md`](computation.md). The native restricted replicator can be run with `run_native_restricted_replicator.py`; it remains a restricted-support heuristic. `run_exact_full_best_response.py` provides an exact integer-arithmetic best response over all legal allocations for an explicitly quantized, finite-support mixture (practical for small supports), and an optional `--max-support` mode adds a rigorous payout-range bound for discarded probability mass. `restricted_two_support_search.py`, `restricted_support3_search.py`, and `restricted_support4_search.py` numerically search supports through size four and audit surviving candidates globally. `symmetric_minimax_expansion.py` adds multistart restricted-equilibrium solving with exact full-action response expansion; its best audited deviation gap is about 1.094, still far from zero, so it has not solved the game. HPG job 49377453 is continuing that search. Fixed-response exact-rational payout audits use `response_distribution.py`.

Do not put head-to-head matrix-game analyses here.
