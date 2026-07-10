"""Canonical event/segment/sample contract for simulation consumers."""
from bisect import bisect_right
from .schemas import EventRecord,SimulationResult,SimulationSample,SimulationTimeline,StageSegment

FIELDS=("pressure","force","gasRate","annulusPressure","bubblePressure","slugTop","slugBase",
        "filmThickness","bubbleVelocity","slugVelocity","bottomPressure","fallbackVolume",
        "gasLiftValveOpen","liquidRate","producedVolume","slugVolume","filmVolume")

def _sample(p, event=None):
    return SimulationSample(t=p.t,stage=p.stage or "UNKNOWN",
        values={k:getattr(p,k) for k in FIELDS},exactEvent=event)

def build_timeline(result:SimulationResult,interval_s:float=1.0)->SimulationTimeline:
    if interval_s<=0: raise ValueError("A positive resampling interval is required")
    points=result.points; native=[_sample(p) for p in points]
    segments=[]; start=0
    for i in range(1,len(points)+1):
        if i==len(points) or points[i].stage!=points[start].stage:
            segments.append(StageSegment(stage=points[start].stage or "UNKNOWN",startTime=points[start].t,
                endTime=points[i-1].t,startIndex=start,endIndex=i-1)); start=i
    ids=["A_INITIAL_STATE","B_GAS_LIFT_VALVE_OPENS","C_MOTOR_VALVE_CLOSES",
         "D_SLUG_TOP_REACHED_SURFACE","E_SLUG_BASE_REACHED_SURFACE","F_FILM_VELOCITY_ZERO"]
    events=[]
    for i,seg in enumerate(segments):
        if i==0: events.append(EventRecord(eventId=ids[0],t=seg.startTime,stageAfter=seg.stage))
        if i+1<len(segments): events.append(EventRecord(eventId=ids[i+1],t=seg.endTime,
            stageBefore=seg.stage,stageAfter=segments[i+1].stage))
    events.append(EventRecord(eventId=ids[len(segments)],t=segments[-1].endTime,
        stageBefore=segments[-1].stage,terminal=True))
    event_by_t={round(e.t,9):e.eventId for e in events}
    for s in native: s.exactEvent=event_by_t.get(round(s.t,9))
    times=[p.t for p in points]; out=[]; t=times[0]
    while t<times[-1]:
        j=max(0,min(bisect_right(times,t)-1,len(points)-2)); a,b=points[j],points[j+1]
        f=0 if b.t==a.t else (t-a.t)/(b.t-a.t); vals={}
        for k in FIELDS:
            x,y=getattr(a,k),getattr(b,k)
            vals[k]=x if isinstance(x,bool) or x is None or y is None else float(x+(y-x)*f)
        out.append(SimulationSample(t=t,stage=a.stage or "UNKNOWN",values=vals)); t+=interval_s
    out.append(_sample(points[-1],result.terminalEvent))
    return SimulationTimeline(caseId=result.caseId,physicalScope=result.physicalScope,nativeSamples=native,
        events=events,segments=segments,resampledSeries=out,resampleInterval=interval_s,
        adaptiveSolverOutputAvailable=False)
