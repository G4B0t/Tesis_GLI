# Pressure symbol map — Santos Model I

This map is the mandatory pressure contract for the corrected A→G chain. All
production equations must use SI absolute pressure. A gauge value may enter
only through an explicit unit conversion at the API/base-case boundary.

| Symbol | Physical location and meaning | Internal unit/reference | Authoritative use |
|---|---|---|---|
| `P_c1` | Annulus/casing gas pressure at the surface | Pa absolute | Casing EOS and motor-valve boundary |
| `P_c2` | Annulus/casing gas pressure at GLV depth `H_gv` | Pa absolute | GLV upstream pressure; Santos 4.1.13 and 4.1.16 |
| `P_t1` | Tubing pressure at GLV depth `H_gv` | Pa absolute | GLV downstream pressure and upper boundary of the liquid column below the GLV; Santos explicitly defines this location below 4.1.13 and 4.1.27 |
| `P_t2` | Tubing pressure at the top of the gas bubble | Pa absolute | Bubble momentum balance; Santos 4.1.27 |
| `P_t3` | Tubing gas pressure at the lower end of the stage-4.3 gas core, immediately above the lower liquid column | Pa absolute | Lower gas boundary in 4.1.94–4.1.101 and the corrected G momentum residual |
| `P_ts` | Tubing pressure at the surface | Pa absolute | Surface boundary in 4.1.89 and 4.1.94–4.1.103 |
| `P_r` | Static reservoir pressure at perforation depth `H_w` | Pa absolute | Linear IPR upstream pressure |
| `P_wb` / `P_wf` | Flowing bottom-hole pressure at perforation depth `H_w` | Pa absolute | Dynamic IPR downstream pressure: `P_wb = P_t1 + rho_l g (H_w - H_gv)` |
| `P_to` | Initial tubing pressure at GLV depth | Pa absolute | Legacy decompression diagnostic only; it is not the corrected G terminal condition |

## Required transformations

1. `P_wb` is obtained from the instantaneous `P_t1`, not from `P_ts`:
   `P_wb(t) = P_t1(t) + rho_l g [H_w - H_gv]`.
2. Stage 4.3 maps its lower-core state to `P_t1` through the lower liquid
   column: `P_t1 = P_t3 + rho_l g h_l` under the hydrostatic closure presently
   used by the implementation.
3. The corrected G event is the zero-velocity limit of Santos 4.1.98–4.1.102:
   `R_G = P_t3 - P_ts - rho_g g (H_gv - h_l) = 0`.
4. The historical condition `P_t1 - P_to = 0` remains available only as a
   diagnostic root on the same unterminated F→G trajectory.

## Forbidden substitutions

- `P_ts` must not substitute for `P_t1` or `P_wb` in the reservoir IPR.
- `P_t1`, `P_t3`, and `P_wb` are not interchangeable; they are at different
  vertical locations and require the declared hydrostatic transformations.
- Gauge kgf/cm² or MPa values must not be inserted directly into SI equations.
- A negative `P_r - P_wb` must not be clipped to zero or to a minimum rate; it
  is an explicit physically-invalid state for the current production-only IPR.

## Source reconciliation

Santos Table 4.1 describes the end of decompression generically as recovery of
the initial bottom gas pressure. The specific stage-4.3 equations are more
restrictive: 4.1.98 gives the gas-core momentum balance, 4.1.99 its velocity,
and 4.1.102 relates that velocity to the surface velocity. Their zero-velocity
limit is the corrected momentum residual above. The legacy pressure-recovery
root is therefore retained for comparison but is not allowed to terminate the
corrected stage.
