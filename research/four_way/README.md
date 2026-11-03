# Game 2 research: Four-Way Battle

Keep Game 2-specific experiments, solver implementations, population models, and conclusions here.

Suggested progression:
1. Validate rank and payout tie semantics against the challenge.
2. Define the equilibrium/optimization target (symmetric Nash, evolutionary stability, or field-specific expected payout).
3. Implement reproducible group simulation and sampled deviation search.
4. Track uncertainty, population assumptions, and best-response gaps.

Latest findings and solver limitations: [`restricted-search.md`](restricted-search.md), [`double-oracle.md`](double-oracle.md), [`robust-portfolio.md`](robust-portfolio.md), and [`computation.md`](computation.md). The native restricted replicator can be run with `run_native_restricted_replicator.py`; it is faster than the Python reference but remains a restricted-support heuristic. Fixed-response exact-rational audits use `response_distribution.py`.

Do not put head-to-head matrix-game analyses here.
