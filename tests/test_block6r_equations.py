import math
from gli.block6r_equations import *


def test_4157_mass_balance_closes():
    r,y,z,v,q = .03175,.0012,1700.,.3,1.0e-5
    af=area_film(r,y)
    dydt=(q-v*af)/(2*math.pi*z*(r-y))
    assert abs(residual_4157(r,z,y,dydt,v,q)) < 1e-15


def test_4172_gas_balance_closes():
    a,z,r,y,rho,rhos,vgs,md=.0028,1700,.03175,.0012,18.,1.2,6.,.025
    dydt=-2e-7
    dr=(md+2*math.pi*z*rho*(r-y)*dydt-rhos*vgs*a)/(a*z)
    assert abs(residual_4172(a,z,dr,rho,r,y,dydt,rhos,vgs,md)) < 1e-14


def test_4174_density_positive_and_pressure_monotone():
    args=(.018,8.314462618,1.2e5,1.,300.,2.0e6,1.,330.)
    lo=rho_g_4174(*args); hi=rho_g_4174(*args[:-3],3.0e6,1.,330.)
    assert 0 < lo < hi


def test_4175_constitutive_residual():
    z,R,T,M,dr=0.92,8.314462618,330.,.018,-.01
    dp=2*z*R*T*dr/M
    assert abs(residual_4175(dp,z,R,T,M,dr)) < 1e-12
