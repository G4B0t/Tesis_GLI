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

def simulate_stage_e_to_f(params: GLIParameters, *, stage_d_e: StageDEResult|None=None,
        closure: StageEFParameters|None=None, max_time_s=240., max_step_s=.05,
        rtol=1e-8, atol=1e-10, rhs_mode: str = "legacy"):
    de=stage_d_e or simulate_stage_d_to_e(params)
    if rhs_mode == "santos_corrected":
        return _simulate_stage_e_to_f_santos_corrected(
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


def _simulate_stage_e_to_f_santos_corrected(params: GLIParameters, de: StageDEResult, *,
        closure: StageEFParameters|None=None, max_time_s=240., max_step_s=.05,
        rtol=1e-8, atol=1e-10):
    """Parallel corrected E->F route.

    The corrected boundary map is identity-based for the states with memory
    delivered by D->E santos_corrected: rho_g, m_g, P_t1, v_g, v_f, y and
    film inventory.  It keeps cumulative liquid ledgers instead of restarting
    production at zero.  The public API does not call this mode yet.
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
        mg, vg, y, vf, film, produced, fallback, gas_out = state
        Ab, Af = geometry(y)
        rho = mg / max(Ab * H, 1e-18)
        pt = mg * gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k / (
            gas.gas_molar_mass_kg_mol * max(Ab * H, 1e-18)
        )
        return rho, pt, Ab, Af

    def derivatives(state):
        mg, vg, y, vf, film, produced, fallback, gas_out = state
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
        return np.array([dmg, dvg, dy, dvf, -qfilm, qfilm, 0.0, mdot]), mdot, shear

    state0 = np.array([mg0, vg0, y0, vf0, film0, prod0, fallback0, 0.0], dtype=float)

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
    certified = bool(
        reached
        and descending
        and gas_error <= 1e-8
        and liquid_error <= 1e-8
        and not bool(np.zeros_like(t, dtype=bool).any())
        and abs(float(s[3][0]) - vf0) / max(abs(vf0), 1.0) <= 1e-12
        and abs(float(s[1][0]) - vg0) / max(abs(vg0), 1.0) <= 1e-12
    )
    return StageEFResult(
        t, rho, pt, s[1], s[2], s[3], s[0], md, tau, s[4], s[5],
        np.zeros_like(t), np.zeros_like(t), np.zeros_like(t, dtype=bool),
        reached, end, gas_error, liquid_error,
        "Identity E map from D->E santos_corrected; rho_g, m_g, P_t1, v_g, v_f, y, film, fallback and produced ledgers transported without projection",
        s[6], certified, "santos_corrected"
    )
