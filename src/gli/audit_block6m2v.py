"""Block 6M-2V validation audit; no calibration is performed."""
from dataclasses import dataclass
import numpy as np
from .initial_conditions import initial_stage_1
from .stage1_dynamic import state_from_mass
from .units import KGF_CM2_TO_PA

SANTOS_EVENTS={"A":0.0,"B":25.0,"C":55.0,"D":290.0}
REFERENCE={
 "h_l":([55,120,190,255,290],[540,760,1050,1320,1500]),
 "h_b":([75,140,205,265],[220,520,830,1140]),
 "v_b":([45,140,250,290],[4.5,4.6,4.6,4.8]),
 "v_l":([45,140,250,290],[4.0,4.0,4.0,4.2]),
 "pwf":([45,210,315,380,500],[70.5,66.5,62,55,20]),
}

@dataclass(frozen=True)
class EventAudit:
    event:str; absolute_s:float; duration_s:float; reference_s:float; error_s:float

def event_table(ab,bc,cd):
    vals=[("A",0.,0.),("B",ab.opening_time_s,ab.opening_time_s),
          ("C",ab.opening_time_s+bc.event_c_time_s,bc.event_c_time_s),
          ("D",ab.opening_time_s+bc.event_c_time_s+cd.event_d_time_s,cd.event_d_time_s)]
    return [EventAudit(k,t,d,SANTOS_EVENTS[k],t-SANTOS_EVENTS[k]) for k,t,d in vals]

def trajectory_rmse(params,ab,bc,cd):
    offset=ab.opening_time_s; tc=offset+bc.event_c_time_s
    t=np.r_[offset+bc.time_s,tc+cd.time_s[1:]]
    ini=initial_stage_1(params)
    values={"h_l":np.r_[bc.states[9],cd.states[9,1:]],"h_b":np.r_[bc.states[8],cd.states[8,1:]],
      "v_b":np.r_[bc.states[4],cd.states[4,1:]],"v_l":np.r_[bc.states[10],cd.states[10,1:]],
      "pwf":np.r_[bc.states[3],cd.states[3,1:]]/KGF_CM2_TO_PA}
    out={}
    for key,(xr,yr) in REFERENCE.items():
        x=np.asarray(xr,float);y=np.asarray(yr,float);m=(x>=t[0])&(x<=t[-1]);pred=np.interp(x[m],t,values[key])
        out[key]=float(np.sqrt(np.mean((pred-y[m])**2)))
    # Pc1 includes A->D and its six compatible digitized points.
    ta=np.r_[ab.time_s,offset+bc.time_s[1:],tc+cd.time_s[1:]]
    pc=np.r_[ab.p_c1_pa,[state_from_mass(x,params)['p_c1'] for x in bc.states[0,1:]],[state_from_mass(x,params)['p_c1'] for x in cd.states[0,1:]]]/KGF_CM2_TO_PA
    x=np.array([0,18,55,120,240,320.]);y=np.array([54,58.8,62.5,60.2,56.8,54.2]);out['pc1']=float(np.sqrt(np.mean((np.interp(x,ta,pc)-y)**2)))
    return out

def valve_case_audit(params):
    return {"case_id":"santos-gli-50-70-80","mode":"legacy_force_proxy",
      "bellows_area_status":"inferred proxy","rv_status":"inferred proxy",
      "port_area_status":"bibliographic 2001, not 1997 case datasheet",
      "quantitatively_validated":False}
