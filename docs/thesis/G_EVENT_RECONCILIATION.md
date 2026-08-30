# G-event reconciliation — Milestone 1.5

## Competing definitions

The historical implementation terminated F→G at
`R_legacy=P_t1-P_to,initial=0`, following the generic decompression wording in
Santos Table 4.1. The stage-specific equations provide a stricter condition:

`R_G=P_t3-P_ts-rho_g g (H_gv-h_l)`.

Santos 4.1.98 is the gas-core momentum balance; 4.1.99 solves it for `v_g`,
and 4.1.102 relates `v_g` to `v_gs`. Therefore `R_G=0` is exactly the
zero-velocity boundary `v_g=v_gs=0`. It is the only production terminal G.
The pressure-recovery residual remains a non-terminal diagnostic.

## Same-trajectory experiment

`gli.audit_milestone15.run_milestone15_diagnostic()` integrates the same F→G
state trajectory, records the legacy event non-terminally and looks for the
corrected terminal event. No coefficient is changed between candidates.

| Candidate | Roots in base run | First root | Residual at 10,000 s | Classification |
|---|---:|---:|---:|---|
| `P_t1-P_to,initial` | 1 | 101.846418 s | +3.545913 MPa | historical diagnostic only |
| `P_t3-P_ts-rho_g g(H_gv-h_l)` | 0 | none | +1.49808e-5 Pa | approaches zero without a finite crossing in the guard horizon |

At the legacy root the corrected residual is still approximately +2.713 MPa,
so the two definitions are not interchangeable. No multiple root was found for
either candidate. There is no “first physically admissible corrected root” to
select.

At the standard 1200 s guard the corrected residual is still +12.9118 Pa and
`v_g≈0.0991 m/s`; at 10,000 s it remains positive. The production solver
therefore reports `event_g_reached=False`. It uses a zero-valued numerical
extension of the 4.1.99 radicand only while Radau attempts to bracket the
boundary; materially negative radicands raise a domain error, and no
post-event state is returned.

## Conservation and physical admissibility

At 10,000 s the normalized gas and liquid balance residuals are approximately
`2.59e-12` and `1.14e-13`. Numerical conservation is therefore not the reason
for rejecting G. The blockers are physical/event contracts:

1. corrected momentum equilibrium has no finite root in the tested horizon;
2. the current F spatial transformation creates negative raw reservoir influx
   for the first 32.737 s of F→G.

Status: **NOT_READY_FOR_GH**. G→H must not be initialized from the safety
horizon or from the legacy root.
