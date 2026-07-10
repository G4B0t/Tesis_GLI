"""Audit-only transcription helpers for Santos (1997), stage 4 phase I.

This module deliberately does not implement the E->F integrator.  It exposes
algebraic residuals so the recovered equations can be tested in isolation.
"""
from __future__ import annotations

from math import pi


def area_film(r: float, y: float) -> float:
    return pi * (2.0 * r * y - y * y)


def residual_4157(r, z_v, y, dy_dt, v_f, q_res):
    a_f = area_film(r, y)
    return 2*pi*z_v*(r-y)*dy_dt + v_f*a_f - q_res


def residual_4169(r, z_v, y, dy_dt, v_f, dvf_dt, rho_l, rho_g,
                  v_g, f_g, f_f, p_t1, p_ts, g=9.80665):
    a_f = area_film(r, y)
    return (a_f*(dvf_dt + g)
            + 2*pi*(r-y)*(v_f*dy_dt - f_g*rho_g*v_g**2/(8*rho_l))
            + f_f*v_f**2*pi*r/4
            - a_f*(p_t1-p_ts)/(rho_l*z_v))


def residual_4172(a_b, z_v, drhog_dt, rho_g, r, y, dy_dt,
                  rho_gs, v_gs, m_dot_gv):
    return (a_b*z_v*drhog_dt - 2*pi*z_v*rho_g*(r-y)*dy_dt
            + rho_gs*v_gs*a_b - m_dot_gv)


def residual_4173(z_v, dp_t1_dt, f_g, v_g, diameter, g,
                  drhog_dt, rho_g, dv_g_dt):
    return (dp_t1_dt/z_v - (f_g*v_g**2/(2*diameter)+g)*drhog_dt
            - f_g*rho_g*v_g*dv_g_dt/diameter)


def rho_g_4174(molar_mass, gas_constant, p_ts, z_ts, t_ts,
               p_t1, z_t1, t_t1):
    return 0.5*(molar_mass*p_ts/(z_ts*gas_constant*t_ts)
                + molar_mass*p_t1/(z_t1*gas_constant*t_t1))


def residual_4175(dp_t1_dt, z_t1, gas_constant, t_t1,
                  molar_mass, drhog_dt):
    return dp_t1_dt - 2*z_t1*gas_constant*t_t1*drhog_dt/molar_mass
