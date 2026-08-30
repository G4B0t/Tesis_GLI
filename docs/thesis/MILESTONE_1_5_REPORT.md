# Milestone 1.5 — pre-G→H scientific reconciliation

Status: **NOT_READY_FOR_GH**.

1. Backend branch verified as `feature/gli-thesis-completion`.
2. Pre-change backend commit recorded as `51f9876dc91dc19919798caeb63f29ae8f48673e`.
3. Frontend branch/commit inspected; no frontend file changed.
4. Pre-change suite: 150 collected, 150 passed, 0 failed, 0 skipped.
5. Santos scanned pages were rendered and inspected directly.
6. `P_t1` was confirmed as tubing pressure at GLV depth.
7. `P_ts` was confirmed as surface tubing pressure.
8. `P_c2` was confirmed as annulus pressure at GLV depth.
9. Stage-4.3 equations 4.1.94–4.1.108 were reconciled.
10. `PRESSURE_SYMBOL_MAP.md` was created before production-equation edits.
11. Gauge/absolute pressure boundaries are explicit.
12. API PI units are explicit: m³/day/(kgf/cm²).
13. PI converts to m³/(s Pa) at the boundary.
14. Reservoir pressure converts from kgf/cm²(g) to Pa(a).
15. Dynamic `P_wb=P_t1+rho_l g(H_w-H_gv)` is centralized.
16. Dynamic `q_r=PI(P_r-P_wb)` is centralized.
17. Negative raw `q_r` is not clipped.
18. Negative raw `q_r` is classified as invalid reverse flow for this IPR.
19. A→B correctly has no reservoir-liquid term.
20. B→C now consumes instantaneous `q_r(P_t1)`.
21. C→D now consumes instantaneous `q_r(P_t1)`.
22. D→E now consumes instantaneous `q_r(P_t1)`.
23. D→E exposes an independently integrated reservoir ledger.
24. E→F integrates dynamic inflow as lower-column provenance.
25. F→G uses dynamic inflow in Santos 4.1.107.
26. Legacy constant inflow remains compatibility-only and is explicitly tagged.
27. The former API rate floor was removed.
28. The former surface-pressure IPR driver was removed from production ODEs.
29. Corrected G residual is `P_t3-P_ts-rho_g g(H_gv-h_l)`.
30. Corrected G is linked to the zero-velocity limit of 4.1.98–4.1.102.
31. The former `P_t1-P_to` event is retained non-terminally.
32. The event comparison runs on the same F→G trajectory.
33. The legacy candidate has one root at 101.846418 s.
34. The corrected candidate has no root through 10,000 s.
35. Corrected residual remains +1.49808e-5 Pa at 10,000 s.
36. No multiple roots were found.
37. F→G gas balance remains closed at approximately `2.59e-12` normalized.
38. F→G liquid balance remains closed at approximately `1.14e-13` normalized.
39. The F transformation causes `q_r<0` until about 32.737 s, a physical blocker.
40. Post-change suite: 156 collected, 156 passed, 0 failed, 0 skipped.

The scientific blocker is not numerical divergence. The present A→F state
representation and its F spatial transformation do not yield a finite,
physically admissible corrected G boundary for the Santos base case. No
coefficient was tuned and no event was substituted to manufacture readiness.
G→H, multicycle, frontend expansion, commit and push remain outside this milestone.
