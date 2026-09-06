"""Santos stage E->F: gas decompression until film velocity crosses zero."""
from dataclasses import dataclass
from math import pi, sqrt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from .base_case import santos_50_70_80
from .block6p_parameters import FrictionClosure, ProvenanceClass, ScalarParameter, friction_factor
from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .stage_de_dynamic import StageDEResult, simulate_stage_d_to_e
from .reservoir import reservoir_inflow_from_pt1

@dataclass(frozen=True)
class StageEFParameters:
    roughness: ScalarParameter
    surface_discharge_cd: ScalarParameter
    entrainment_model: str = "santos_no_mass_exchange_stage4"

def default_stage_ef_parameters(roughness_m=4.5e-5):
    return StageEFParameters(
        ScalarParameter(roughness_m,"m",ProvenanceClass.BIBLIOGRAPHIC,
            "commercial steel uncertainty range; user-replaceable",1e-6,2e-4),
        ScalarParameter(.865,"1",ProvenanceClass.BIBLIOGRAPHIC,
            "Santos gas-lift discharge coefficient reused for surface core",.75,.95))

@dataclass(frozen=True)
class StageEFResult:
    time_s: np.ndarray; gas_density_kg_m3: np.ndarray; tubing_pressure_pa: np.ndarray
    gas_velocity_m_s: np.ndarray; film_thickness_m: np.ndarray; film_velocity_m_s: np.ndarray
    gas_mass_kg: np.ndarray; surface_gas_rate_kg_s: np.ndarray
    interfacial_shear_pa: np.ndarray; film_volume_m3: np.ndarray
    produced_film_volume_m3: np.ndarray; entrained_volume_m3: np.ndarray
    reservoir_accumulated_m3: np.ndarray; valve_open: np.ndarray
    event_f_reached: bool; event_f_time_s: float
    gas_balance_relative_error: float; liquid_balance_relative_error: float
    initial_state_source: str
    fallback_volume_m3: np.ndarray | None = None
    corrected_certified: bool = False
    rhs_mode: str = "legacy"
    reservoir_inflow_valid: bool = True
    gas_pressure_at_liquid_top_pa: np.ndarray | None = None
    liquid_height_m: np.ndarray | None = None
    physical_lower_liquid_volume_m3: np.ndarray | None = None
    surface_gas_velocity_m_s: np.ndarray | None = None
    gas_momentum_condition_number: np.ndarray | None = None
    source_certification_status: str = "NOT_SOURCE_CERTIFIED_A_TO_F"


@dataclass(frozen=True)
class Stage42InitialStateAudit:
    liquid_height_m: float
    pressure_t1_pa: float
    pressure_t3_pa: float
    gas_mass_kg: float
    gas_density_from_inventory_kg_m3: float
    gas_density_from_eos_kg_m3: float
    eos_density_relative_residual: float
    hydrostatic_residual_pa: float
    gas_volume_required_by_eos_m3: float
    maximum_geometric_gas_volume_m3: float
    compatible: bool


class Stage42InitialStateIncompatibility(ValueError):
    """Raised when terminal D->E cannot initialize Santos stage 4.2 by identity."""

    def __init__(self, audit: Stage42InitialStateAudit):
        self.audit = audit
        super().__init__(
            "NOT_SOURCE_CERTIFIED_A_TO_F: terminal D->E violates the simultaneous "
            "Stage 4.2 gas-inventory, 4.1.88 hydrostatic and 4.1.90 EOS closures "
            f"(scaled density residual={audit.eos_density_relative_residual:.9g})"
        )

def simulate_stage_e_to_f(params: GLIParameters, *, stage_d_e: StageDEResult|None=None,
        closure: StageEFParameters|None=None, max_time_s=240., max_step_s=.05,
        rtol=1e-8, atol=1e-10, rhs_mode: str = "legacy"):
    de=stage_d_e or simulate_stage_d_to_e(params)
    if rhs_mode == "santos_corrected":
        return _simulate_stage_e_to_f_santos_stage42(
            params, de, closure=closure, max_time_s=max_time_s, max_step_s=max_step_s, rtol=rtol, atol=atol
        )
    if rhs_mode == "milestone15_corrected":
        return _simulate_stage_e_to_f_milestone15(
            params, de, closure=closure, max_time_s=max_time_s, max_step_s=max_step_s, rtol=rtol, atol=atol
        )
    if rhs_mode != "legacy":
        raise ValueError(f"unknown E->F rhs_mode: {rhs_mode}")
    if not de.event_e_reached or bool(de.valve_open[-1]):
        raise ValueError("E must be reached with GLV closed")
    c=closure or default_stage_ef_parameters()
    H=params.geometry.valve_depth_m; D=params.geometry.tubing_diameter_m; r=D/2
    At=tubing_area(D); film0=float(de.film_volume_m3[-1]); Af0=film0/H
    y0=r-sqrt(max(r*r-Af0/pi,0)); Ab0=At-Af0
    mg0=float(de.bubble_mass_kg[-1]); rho0=mg0/(Ab0*H); pt0=float(de.p_tubing_pa[-1])
    gas=params.gas; rho_s=gas.gas_molar_mass_kg_mol*params.operating.surface_tubing_pressure_pa/(gas.z_ts*gas.gas_constant_j_mol_k*gas.temp_ts_k)
    vg0=c.surface_discharge_cd.value*sqrt(max(2*(pt0-params.operating.surface_tubing_pressure_pa)/rho0,0))
    fc=FrictionClosure(c.roughness); rho_l=initial_stage_1(params)['rho_l']; mu_l=params.fluids.liquid_viscosity_pa_s

    def factors(vg,vf,y,rho):
        Ab=pi*(r-y)**2; Af=At-Ab
        fg,_=friction_factor(max(rho*abs(vg)*2*(r-y)/1.1e-5,1e-9),max(2*(r-y),1e-9),fc)
        # Film hydraulic diameter follows 4A/P with both wetted boundaries.
        dhf=max(4*Af/(2*pi*r+2*pi*(r-y)),1e-9)
        ff,_=friction_factor(max(rho_l*abs(vf)*dhf/mu_l,1e-9),dhf,fc)
        return Ab,Af,fg,ff

    def derivatives(state):
        rho,pt,vg,y,vf,mg,film,vprod,vres=state
        Ab,Af,fg,ff=factors(vg,vf,y,rho)
        dy=-vf*Af/(2*pi*H*max(r-y,1e-12)) # (4.1.57), q_res=0 for film
        mdot=rho_s*max(vg,0)*Ab
        drho=(2*pi*H*rho*(r-y)*dy-mdot)/(Ab*H) # (4.1.72), m_gv=0
        dpt=2*gas.z_t1*gas.gas_constant_j_mol_k*gas.temp_t1_k*drho/gas.gas_molar_mass_kg_mol # (4.1.75)
        denom=fg*rho*vg/max(D,1e-12)
        dvg=(dpt/H-(fg*vg*vg/(2*D)+GRAVITY_M_S2)*drho)/max(abs(denom),1e-12)
        shear=fg*rho*vg*vg/8
        dvf=(-GRAVITY_M_S2 - 2*pi*(r-y)/Af*(vf*dy-shear/rho_l)
              -ff*vf*abs(vf)*pi*r/(4*Af)+(pt-params.operating.surface_tubing_pressure_pa)/(rho_l*H)) # (4.1.69)
        qfilm=vf*Af
        return np.array([drho,dpt,dvg,dy,dvf,-mdot,-qfilm,max(qfilm,0),params.operating.reservoir_liquid_rate_m3_s]),mdot,shear

    # E contains film geometry but the legacy D->E vector has no vf. Recover
    # the missing algebraic component from (4.1.69), dvf/dt=0, without a fit.
    def equilibrium(v):
        st=np.array([rho0,pt0,vg0,y0,v,mg0,film0,0.,0.]); return derivatives(st)[0][4]
    grid=np.linspace(1e-8,max(vg0,1.),300); vf0=None
    for a,b in zip(grid[:-1],grid[1:]):
        if equilibrium(a)*equilibrium(b)<=0: vf0=brentq(equilibrium,a,b);break
    if vf0 is None: raise ValueError("No positive Santos film-velocity closure exists at E")
    state0=np.array([rho0,pt0,vg0,y0,vf0,mg0,film0,0.,0.])
    def rhs(_t,s): return derivatives(s)[0]
    def event_f(_t,s): return s[4]
    event_f.terminal=True;event_f.direction=-1
    sol=solve_ivp(rhs,(0,max_time_s),state0,events=event_f,dense_output=True,max_step=max_step_s,rtol=rtol,atol=atol)
    reached=bool(sol.t_events[0].size);end=float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    t=np.linspace(0,end,max(2,int(np.ceil(end/max_step_s))+1));s=sol.sol(t)
    derived=[derivatives(s[:,i]) for i in range(s.shape[1])];md=np.array([x[1] for x in derived]);tau=np.array([x[2] for x in derived])
    gas_inventory=s[5]+np.concatenate(([0.],np.cumsum((md[1:]+md[:-1])*.5*np.diff(t))))
    ge=float(np.max(abs(gas_inventory-gas_inventory[0]))/max(mg0,1))
    liquid=s[6]+s[7];le=float(np.max(abs(liquid-liquid[0]))/max(film0,1e-12))
    return StageEFResult(t,s[0],s[1],s[2],s[3],s[4],s[5],md,tau,s[6],s[7],np.zeros_like(t),s[8],np.zeros_like(t,dtype=bool),reached,end,ge,le,
        "Exact E inventories and pressures; vf recovered algebraically from Santos 4.1.69 because legacy D->E did not store vf",
        np.zeros_like(t), False, "legacy")


def _film_thickness_from_volume(params: GLIParameters, film_volume_m3: float) -> float:
    r = params.geometry.tubing_diameter_m / 2.0
    area = film_volume_m3 / params.geometry.valve_depth_m
    return r - sqrt(max(r * r - area / pi, 0.0))


def _stage_42_surface_density(params: GLIParameters) -> float:
    gas = params.gas
    return (
        gas.gas_molar_mass_kg_mol * params.operating.surface_tubing_pressure_pa
        / (gas.z_ts * gas.gas_constant_j_mol_k * gas.temp_ts_k)
    )


def _stage_42_k_t3(params: GLIParameters) -> float:
    gas = params.gas
    return gas.z_t3 * gas.gas_constant_j_mol_k * gas.temp_t3_k / gas.gas_molar_mass_kg_mol


def audit_stage_42_initial_state(
    params: GLIParameters,
    de: StageDEResult,
    *,
    relative_tolerance: float = 1.0e-6,
) -> Stage42InitialStateAudit:
    """Audit the identity E map against 4.1.83, 4.1.88 and 4.1.90.

    E and a source-derived lower column must exist before this audit runs.
    Absence of Phase I alone does not prescribe a zero lower column.
    """

    if not de.event_e_reached:
        raise ValueError("Physical E is unavailable: " + de.terminal_reason)
    if bool(de.valve_open[-1]):
        raise ValueError("Stage 4.2 requires GLV closure; Phase I entry must be audited first")
    if de.lower_liquid_height_m is None or not de.lower_liquid_height_source:
        raise ValueError("Stage 4.2 requires a source-derived lower liquid height at E")
    if de.gas_pressure_at_liquid_top_pa is None or de.film_thickness_m is None:
        raise ValueError("Stage 4.2 requires explicit E pressure and film memory")
    H = float(params.geometry.valve_depth_m)
    r = float(params.geometry.tubing_diameter_m) / 2.0
    y = float(de.film_thickness_m[-1])
    Ab = pi * (r - y) ** 2
    h_l = float(de.lower_liquid_height_m[-1])
    pt1 = float(de.p_tubing_pa[-1])
    pt3 = float(de.gas_pressure_at_liquid_top_pa[-1])
    gas_mass = float(de.bubble_mass_kg[-1])
    gas_volume = Ab * (H - h_l)
    if not (0 <= h_l < H and 0 < y < r and gas_mass > 0 and pt1 > 0 and pt3 > 0):
        raise ValueError("Stage 4.2 E outside positive physical geometry/pressure domain")
    rho_inventory = gas_mass / gas_volume
    rho_surface = _stage_42_surface_density(params)
    k_t3 = _stage_42_k_t3(params)
    rho_eos = 0.5 * (pt3 / k_t3 + rho_surface)
    relative = abs(rho_inventory - rho_eos) / max(abs(rho_eos), 1.0e-18)
    rho_l = initial_stage_1(params)["rho_l"]
    hydrostatic = pt1 - pt3 - rho_l * GRAVITY_M_S2 * h_l
    return Stage42InitialStateAudit(
        liquid_height_m=h_l,
        pressure_t1_pa=pt1,
        pressure_t3_pa=pt3,
        gas_mass_kg=gas_mass,
        gas_density_from_inventory_kg_m3=rho_inventory,
        gas_density_from_eos_kg_m3=rho_eos,
        eos_density_relative_residual=relative,
        hydrostatic_residual_pa=hydrostatic,
        gas_volume_required_by_eos_m3=gas_mass / max(rho_eos, 1.0e-18),
        maximum_geometric_gas_volume_m3=Ab * H,
        compatible=bool(0 <= h_l < H and relative <= relative_tolerance
                        and abs(hydrostatic) <= 1.0e-6
                        and de.gas_density_kg_m3 is not None
                        and abs(float(de.gas_density_kg_m3[-1])-rho_inventory)
                        <= relative_tolerance*max(abs(rho_inventory),1e-18)
                        and abs(float(de.film_volume_m3[-1])-(tubing_area(2*r)-Ab)*H)
                        <= relative_tolerance*max(abs(float(de.film_volume_m3[-1])),1e-18)),
    )


def santos_stage_42_derivatives(
    params: GLIParameters,
    state: np.ndarray,
    *,
    closure: StageEFParameters | None = None,
) -> tuple[np.ndarray, dict[str, float | object]]:
    """Evaluate the seven-variable Santos 4.2 differential system.

    State order is ``[h_l, P_t1, P_t3, rho_g, v_f, v_g, y]``.  The local
    4.1.83/4.1.84 derivative pair is solved as a scaled 2x2 linear system; the
    returned condition number is a numerical diagnostic, not a tuned closure.
    """

    h_l, pt1, pt3, rho_g, vf, vg, y = map(float, state)
    H = float(params.geometry.valve_depth_m)
    D = float(params.geometry.tubing_diameter_m)
    r = D / 2.0
    At = tubing_area(D)
    if not (0.0 <= h_l < H):
        raise ValueError("Stage 4.2 h_l must remain in [0, z_v)")
    if not (0.0 <= y < r):
        raise ValueError("Stage 4.2 y must remain in [0, r)")
    if min(pt1, pt3, rho_g) <= 0.0:
        raise ValueError("Stage 4.2 pressures and gas density must be positive")

    c = closure or default_stage_ef_parameters()
    rho_l = float(initial_stage_1(params)["rho_l"])
    mu_l = float(params.fluids.liquid_viscosity_pa_s)
    fc = FrictionClosure(c.roughness)
    Ab = pi * (r - y) ** 2
    Af = max(At - Ab, 1.0e-18)
    gas_length = H - h_l
    gas_diameter = max(2.0 * (r - y), 1.0e-9)
    fg, _ = friction_factor(
        max(rho_g * abs(vg) * gas_diameter / 1.1e-5, 1.0e-9),
        gas_diameter,
        fc,
    )
    film_diameter = max(4.0 * Af / (2.0 * pi * r + 2.0 * pi * (r - y)), 1.0e-9)
    ff, _ = friction_factor(
        max(rho_l * abs(vf) * film_diameter / mu_l, 1.0e-9),
        film_diameter,
        fc,
    )
    rho_surface = _stage_42_surface_density(params)
    vgs = 2.0 * vg
    qres = reservoir_inflow_from_pt1(params, pt1, rho_l)

    # 4.1.76 and 4.1.87.
    dy = -vf * Af / (2.0 * pi * H * (r - y))
    dh_l = (qres.rate_m3_s + 2.0 * pi * (r - y) * h_l * dy) / Ab

    # 4.1.83 and 4.1.84, after substituting 4.1.90.  Row two is
    # pressure-scaled before solving so the reported conditioning is useful.
    drho_rhs = (
        2.0 * rho_g * dy / (r - y)
        + rho_g * dh_l / gas_length
        - rho_surface * vgs / gas_length
    )
    k_t3 = _stage_42_k_t3(params)
    a84 = 2.0 * k_t3 - (
        fg * vg * vg * gas_length / (2.0 * D) + gas_length * GRAVITY_M_S2
    )
    b84 = -fg * rho_g * vg * gas_length / D
    rhs84 = -(fg * rho_g * vg * vg / (2.0 * D) + rho_g * GRAVITY_M_S2) * dh_l
    pressure_scale = max(abs(2.0 * k_t3), abs(a84), abs(b84), 1.0)
    matrix = np.array([[1.0, 0.0], [a84 / pressure_scale, b84 / pressure_scale]], dtype=float)
    rhs_pair = np.array([drho_rhs, rhs84 / pressure_scale], dtype=float)
    condition = float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition > 1.0e12:
        raise ValueError(f"Santos 4.1.83/4.1.84 derivative system is ill-conditioned: {condition}")
    drho_g, dvg = np.linalg.solve(matrix, rhs_pair)

    # 4.1.90 and 4.1.89.
    dpt3 = 2.0 * k_t3 * drho_g
    dpt1 = dpt3 + rho_l * GRAVITY_M_S2 * dh_l

    # 4.1.80.  Its source form assumes the upward-film branch v_f >= 0,
    # which is precisely the interval integrated before terminal F.
    dvf = (
        -GRAVITY_M_S2
        - 2.0 * pi * (r - y) / Af
        * (vf * dy - fg * rho_g * vg * vg * gas_length / (8.0 * rho_l * H))
        - ff * vf * vf * pi * r / (4.0 * Af)
        + (pt1 - params.operating.surface_tubing_pressure_pa) / (rho_l * H)
    )
    derivative = np.array([dh_l, dpt1, dpt3, drho_g, dvf, dvg, dy], dtype=float)
    return derivative, {
        "Ab": Ab,
        "Af": Af,
        "gas_length": gas_length,
        "rho_surface": rho_surface,
        "surface_gas_velocity": vgs,
        "surface_gas_rate": rho_surface * vgs * Ab,
        "q_res": qres,
        "fg": fg,
        "ff": ff,
        "condition_number": condition,
        "film_rate": vf * Af,
        "gas_mass": rho_g * Ab * gas_length,
        "film_volume": Af * H,
        "lower_liquid_volume": Ab * h_l,
    }


def _simulate_stage_e_to_f_santos_stage42(params: GLIParameters, de: StageDEResult, *,
        closure: StageEFParameters|None=None, max_time_s=240., max_step_s=.05,
        rtol=1e-8, atol=1e-10):
    """Integrate exact Santos Stage 4.2 or reject a non-identity E map."""

    if not de.event_e_reached:
        raise ValueError("E must be reached before E->F")
    if bool(de.valve_open[-1]) or abs(float(de.gl_mass_rate_kg_s[-1])) > 1.0e-12:
        raise ValueError("E->F Stage 4.2 requires GLV closed and latched")
    if de.film_velocity_m_s is None:
        raise ValueError("E->F Stage 4.2 requires D->E film-velocity memory")
    initial_audit = audit_stage_42_initial_state(params, de)
    if not initial_audit.compatible:
        raise Stage42InitialStateIncompatibility(initial_audit)

    H = float(params.geometry.valve_depth_m)
    D = float(params.geometry.tubing_diameter_m)
    r = D / 2.0
    y0 = float(de.film_thickness_m[-1])
    physical0 = np.array([
        initial_audit.liquid_height_m,
        initial_audit.pressure_t1_pa,
        initial_audit.pressure_t3_pa,
        float(de.gas_density_kg_m3[-1]),
        float(de.film_velocity_m_s[-1]),
        float(de.v_b_m_s[-1]),
        y0,
    ], dtype=float)
    produced0 = float(de.produced_volume_m3[-1])
    fallback0 = float(de.fallback_volume_m3[-1])
    if de.reservoir_accumulated_m3 is None:
        raise ValueError("E->F Stage 4.2 requires the D->E reservoir provenance ledger")
    reservoir0 = float(de.reservoir_accumulated_m3[-1])
    state0 = np.concatenate((physical0, [produced0, fallback0, reservoir0, 0.0]))

    def derivatives(state):
        dphysical, algebraic = santos_stage_42_derivatives(params, state[:7], closure=closure)
        ledgers = np.array([
            algebraic["film_rate"],
            0.0,
            algebraic["q_res"].rate_m3_s,
            algebraic["surface_gas_rate"],
        ], dtype=float)
        return np.concatenate((dphysical, ledgers)), algebraic

    def rhs(_time_s, state):
        return derivatives(state)[0]

    def event_f(_time_s, state):
        return state[4]

    event_f.terminal = True
    event_f.direction = -1.0
    sol = solve_ivp(
        rhs, (0.0, max_time_s), state0, events=event_f, dense_output=True,
        max_step=max_step_s, rtol=rtol, atol=atol, method="Radau",
    )
    if not sol.success:
        raise RuntimeError(f"E->F Stage 4.2 integration failed: {sol.message}")
    reached = bool(sol.t_events[0].size)
    end = float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    t = np.linspace(0.0, end, max(2, int(np.ceil(max(end, max_step_s) / max_step_s)) + 1))
    states = sol.sol(t)
    algebraics = [derivatives(states[:, i])[1] for i in range(t.size)]
    arr = lambda name: np.asarray([item[name] for item in algebraics], dtype=float)
    gas_mass = arr("gas_mass")
    film = arr("film_volume")
    lower = arr("lower_liquid_volume")
    gas_balance = gas_mass + states[10]
    liquid_balance = film + lower + states[7] + states[8] - states[9]
    gas_error = float(np.max(np.abs(gas_balance - gas_balance[0])) / max(abs(gas_balance[0]), 1.0e-18))
    liquid_error = float(np.max(np.abs(liquid_balance - liquid_balance[0])) / max(abs(liquid_balance[0]), 1.0e-18))
    inflow_valid = bool(all(item["q_res"].physically_valid for item in algebraics))
    descending = bool(reached and states.shape[1] >= 2 and states[4, -2] > states[4, -1] >= -1.0e-7)
    certified = bool(
        reached and descending and gas_error <= 1.0e-8 and liquid_error <= 1.0e-8
        and inflow_valid and float(np.max(arr("condition_number"))) <= 1.0e12
    )
    return StageEFResult(
        time_s=t,
        gas_density_kg_m3=states[3],
        tubing_pressure_pa=states[1],
        gas_velocity_m_s=states[5],
        film_thickness_m=states[6],
        film_velocity_m_s=states[4],
        gas_mass_kg=gas_mass,
        surface_gas_rate_kg_s=arr("surface_gas_rate"),
        interfacial_shear_pa=arr("fg") * states[3] * states[5] ** 2 / 8.0,
        film_volume_m3=film,
        produced_film_volume_m3=states[7],
        entrained_volume_m3=np.zeros_like(t),
        reservoir_accumulated_m3=states[9],
        valve_open=np.zeros_like(t, dtype=bool),
        event_f_reached=reached,
        event_f_time_s=end,
        gas_balance_relative_error=gas_error,
        liquid_balance_relative_error=liquid_error,
        initial_state_source=(
            "Identity D->E terminal state; h_l(E)=0 from Santos Stage 4.2 onset; "
            "P_t3(E)=P_t1(E) from 4.1.88"
        ),
        fallback_volume_m3=states[8],
        corrected_certified=certified,
        rhs_mode="santos_stage42",
        reservoir_inflow_valid=inflow_valid,
        gas_pressure_at_liquid_top_pa=states[2],
        liquid_height_m=states[0],
        physical_lower_liquid_volume_m3=lower,
        surface_gas_velocity_m_s=arr("surface_gas_velocity"),
        gas_momentum_condition_number=arr("condition_number"),
        source_certification_status=("SOURCE_CERTIFIED_A_TO_F" if certified else "NOT_SOURCE_CERTIFIED_A_TO_F"),
    )


def _simulate_stage_e_to_f_milestone15(params: GLIParameters, de: StageDEResult, *,
        closure: StageEFParameters|None=None, max_time_s=240., max_step_s=.05,
        rtol=1e-8, atol=1e-10):
    """Frozen Milestone-1.5 reference route; not source-certified Stage 4.2.

    The historical boundary map is identity-based for the states with memory
    delivered by D->E, but it omits h_l/P_t3 and uses the pre-1.6 momentum
    approximation. It is retained only to reproduce the requested comparison.
    """
    if not de.event_e_reached:
        raise ValueError("E must be reached before E->F")
    if bool(de.valve_open[-1]) or abs(float(de.gl_mass_rate_kg_s[-1])) > 1e-12:
        raise ValueError("E->F santos_corrected requires GLV closed and latched")
    if de.film_velocity_m_s is None or de.gas_density_kg_m3 is None:
        raise ValueError("E->F santos_corrected requires D->E memory states v_f and rho_g")

    c = closure or default_stage_ef_parameters()
    H = params.geometry.valve_depth_m
    D = params.geometry.tubing_diameter_m
    r = D / 2.0
    At = tubing_area(D)
    gas = params.gas
    rho_l = initial_stage_1(params)["rho_l"]
    mu_l = params.fluids.liquid_viscosity_pa_s
    fc = FrictionClosure(c.roughness)
    rho_surface = (
        gas.gas_molar_mass_kg_mol * params.operating.surface_tubing_pressure_pa
        / (gas.z_ts * gas.gas_constant_j_mol_k * gas.temp_ts_k)
    )

    film0 = float(de.film_volume_m3[-1])
    y0 = _film_thickness_from_volume(params, film0)
    Ab0 = pi * (r - y0) ** 2
    mg0 = float(de.bubble_mass_kg[-1])
    rho0 = float(de.gas_density_kg_m3[-1])
    pt0 = float(de.p_tubing_pa[-1])
    vg0 = float(de.v_b_m_s[-1])
    vf0 = float(de.film_velocity_m_s[-1])
    prod0 = float(de.produced_volume_m3[-1])
    fallback0 = float(de.fallback_volume_m3[-1])
    eos_pt0 = mg0 * gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k / (
        gas.gas_molar_mass_kg_mol * max(Ab0 * H, 1e-18)
    )
    if abs(rho0 - mg0 / max(Ab0 * H, 1e-18)) / max(abs(rho0), 1.0) > 1e-6:
        raise ValueError("E gas density is incompatible with m_g and film geometry")
    if abs(pt0 - eos_pt0) / max(abs(pt0), 1.0) > 1e-5:
        raise ValueError("E tubing pressure is incompatible with gas EOS")

    def geometry(y):
        Ab = pi * max(r - y, 1e-12) ** 2
        Af = max(At - Ab, 1e-12)
        return Ab, Af

    def closures(rho, vg, vf, y):
        Ab, Af = geometry(y)
        try:
            fg, _ = friction_factor(
                min(max(rho * abs(vg) * 2 * max(r - y, 1e-12) / 1.1e-5, 1e-9), 1e8),
                max(2 * (r - y), 1e-5),
                fc,
            )
        except OverflowError:
            fg = 0.02
        dhf = max(4 * Af / (2 * pi * r + 2 * pi * max(r - y, 1e-12)), 1e-5)
        try:
            ff, _ = friction_factor(min(max(rho_l * abs(vf) * dhf / mu_l, 1e-9), 1e8), dhf, fc)
        except OverflowError:
            ff = 0.02
        return Ab, Af, fg, ff

    def derived(state):
        mg, vg, y, vf, film, produced, fallback, gas_out, reservoir = state
        Ab, Af = geometry(y)
        rho = mg / max(Ab * H, 1e-18)
        pt = mg * gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k / (
            gas.gas_molar_mass_kg_mol * max(Ab * H, 1e-18)
        )
        return rho, pt, Ab, Af

    def derivatives(state):
        mg, vg, y, vf, film, produced, fallback, gas_out, reservoir = state
        rho, pt, Ab, Af = derived(state)
        _Ab, _Af, fg, ff = closures(rho, vg, vf, y)
        qfilm = max(vf, 0.0) * Af
        mdot = rho_surface * max(vg, 0.0) * Ab
        dmg = -mdot
        dy = -qfilm / (2 * pi * H * max(r - y, 1e-12))
        dAb = -2 * pi * max(r - y, 1e-12) * dy
        drho = dmg / max(Ab * H, 1e-18) - mg * dAb / max(Ab * Ab * H, 1e-18)
        dpt = gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k * drho / gas.gas_molar_mass_kg_mol
        # Corrected mode keeps v_g as a memory state.  During E->F the top
        # boundary is open to surface; the gas core velocity is reduced by
        # conservative convective depletion plus Darcy friction/gravity losses,
        # rather than being reinitialized from a discharge algebraic law.
        depletion = mdot / max(mg, 1e-18)
        dvg = -vg * depletion - fg * vg * abs(vg) / max(2 * D, 1e-12) - GRAVITY_M_S2
        shear = fg * rho * vg * abs(vg) / 8.0
        dvf = (
            -GRAVITY_M_S2
            - 2 * pi * max(r - y, 1e-12) / Af * (vf * dy - shear / rho_l)
            - ff * vf * abs(vf) * pi * r / (4 * Af)
            + (pt - params.operating.surface_tubing_pressure_pa) / (rho_l * H)
        )
        qres = reservoir_inflow_from_pt1(params, pt, rho_l)
        return np.array([dmg, dvg, dy, dvf, -qfilm, qfilm, 0.0, mdot, qres.rate_m3_s]), mdot, shear, qres

    initial_liquid = At * params.geometry.initial_slug_length_m
    reservoir0 = (
        float(de.slug_volume_m3[-1]) + film0 + fallback0 + prod0 - initial_liquid
    )
    state0 = np.array([mg0, vg0, y0, vf0, film0, prod0, fallback0, 0.0, reservoir0], dtype=float)

    def rhs(_t, state):
        return derivatives(state)[0]

    def event_f(_t, state):
        return state[3]

    event_f.terminal = True
    event_f.direction = -1
    sol = solve_ivp(
        rhs, (0.0, max_time_s), state0, events=event_f, dense_output=True,
        max_step=max_step_s, rtol=rtol, atol=atol, method="Radau"
    )
    reached = bool(sol.t_events[0].size)
    end = float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    t = np.linspace(0.0, end, max(2, int(np.ceil(max(end, max_step_s) / max_step_s)) + 1))
    s = sol.sol(t)
    diagnostics = [derivatives(s[:, i]) for i in range(s.shape[1])]
    md = np.array([x[1] for x in diagnostics])
    tau = np.array([x[2] for x in diagnostics])
    inflow_valid = bool(all(x[3].physically_valid for x in diagnostics))
    rho = np.empty_like(t)
    pt = np.empty_like(t)
    for i in range(t.size):
        rho[i], pt[i], _ab, _af = derived(s[:, i])
    gas_inventory = s[0] + s[7]
    liquid_inventory = s[4] + s[5] + s[6]
    gas_error = float(np.max(np.abs(gas_inventory - gas_inventory[0])) / max(abs(gas_inventory[0]), 1.0))
    liquid_error = float(
        np.max(np.abs(liquid_inventory - liquid_inventory[0])) / max(abs(liquid_inventory[0]), 1.0)
    )
    descending = reached and (len(s[3]) < 2 or float(s[3][-2]) > float(s[3][-1]) >= -1e-7)
    return StageEFResult(
        t, rho, pt, s[1], s[2], s[3], s[0], md, tau, s[4], s[5],
        np.zeros_like(t), s[8],
        np.zeros_like(t, dtype=bool),
        reached, end, gas_error, liquid_error,
        "Milestone 1.5 reference only: identity memory map but Stage 4.2 h_l/P_t3 and 4.1.84 are absent",
        s[6], False, "milestone15_corrected", inflow_valid
    )
