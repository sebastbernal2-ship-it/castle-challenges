# Game 1 research: Head to Head

Keep Game 1-specific experiments, solver implementations, datasets, and conclusions here.

## Status

An exact symmetric equilibrium under the encoded rules is saved at `results/exact-equilibrium-flow-lp.json`. Its 194-allocation mixture has frequency total 410, and the integer-DP verifier certifies a full-action best-response score of 7.5 (zero exploitability). See `analysis.md` and `computation.md` for the proof structure and reproduction commands. Challenge implementation semantics still require confirmation.

Suggested progression:
1. Establish exact pairwise payoff and useful analytic properties.
2. Build a restricted zero-sum matrix game over candidate allocations.
3. Expand the restricted set using best-response search.
4. Report support, value, exploitability diagnostics, and reproducible parameters.

Do not place four-way tournament experiments here.
