# Reservoir inflow model — Milestone 1.5

## Contract

The corrected chain uses the linear productivity relation

`q_r(t) = PI_SI [P_r - P_wb(t)]`

with

`P_wb(t) = P_t1(t) + rho_l g (H_w - H_gv)`.

All production equations receive `q_r` in m³/s, pressures in absolute Pa,
depths in m and density in kg/m³. `P_t1` is the instantaneous tubing pressure
at GLV depth; surface tubing pressure is not a substitute. The authoritative
location definitions are in `PRESSURE_SYMBOL_MAP.md`.

## PI conversion

The user/API productivity index is declared as m³/day/(kgf/cm²). At the input
boundary:

`PI_SI = PI_source / (86400 × 98066.5)`.

For the Santos base value `PI_source=1`, `PI_SI=1.1802270983540835e-10
m³/(s Pa)`. Reservoir pressure supplied as kgf/cm²(g) is converted once to
absolute Pa. Pressure differences use the same 98066.5 Pa/(kgf/cm²) scale.

## Sign and validity policy

No `max(0, …)`, minimum-rate floor or absolute value is applied. The raw value
is returned and classified as:

- `VALID_PRODUCTION`: `P_r>P_wb`, `q_r>0`;
- `ZERO_DRAWDOWN`: `P_r=P_wb`, `q_r=0`;
- `INVALID_REVERSE_FLOW_FOR_LINEAR_IPR`: `P_r<P_wb`, `q_r<0`.

The last condition is outside the production-only linear IPR domain. Keeping
its signed value makes the model defect observable and preserves the balance;
it does not assert that the reverse-flow physics is valid.

## A→G consumption audit

| Segment | Use of reservoir influx in corrected route |
|---|---|
| A→B | None: gas injection/casing stage has no reservoir-liquid balance |
| B→C | Instantaneous `q_r(P_t1)` in Santos film/slug balance |
| C→D | Instantaneous `q_r(P_t1)` in film balance and liquid ledger |
| D→E | Instantaneous `q_r(P_t1)` in film balance; independent quadrature ledger exposed in `StageDEResult` |
| E→F | Instantaneous `q_r(P_t1)` integrated as lower-column provenance ledger; stage-4.2 core dynamics do not consume that lower-column volume |
| F→G | Instantaneous `q_r(P_t1)` in Santos 4.1.107 and the signed reservoir ledger |
| G→H | Not implemented |

Manually constructed legacy parameter objects that omit `P_r` or `PI_SI` may
still use `reservoir_liquid_rate_m3_s` and are marked
`LEGACY_CONSTANT_INPUT`. The Santos base case and API adapter always populate
the dynamic model; the compatibility path is not the production definition.

## Base-case finding

A→F remains inside the positive-inflow IPR domain. Immediately after the F
mean-to-bottom pressure transformation required by the current stage-4.3 map,
however, `P_wb≈10.241 MPa > P_r≈8.457 MPa`, giving
`q_r=-2.10549e-4 m³/s`. The raw rate crosses back to positive at approximately
32.737 s into F→G. This is classified and reported; it is not clipped.
