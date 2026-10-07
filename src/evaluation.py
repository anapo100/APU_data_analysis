"""APU staged analysis: functions have no import-time data processing."""
import sys
sys.dont_write_bytecode = True
import math
import numpy as np
import pandas as pd

def make_context(frame,event_frame):
    f=frame.reset_index(drop=True)
    ns=f.cycle_end.to_numpy(dtype='datetime64[ns]').astype('int64');blocks=f.raw_block.to_numpy()
    ends=np.r_[np.flatnonzero(blocks[1:]!=blocks[:-1])+1,len(f)] if len(f) else np.array([],int)
    block_end=np.empty(len(f),int);left=0
    for right in ends:block_end[left:right]=right;left=right
    ep_ids=event_frame.episode_id.to_numpy();lookup={v:i for i,v in enumerate(ep_ids)}
    code=np.array([lookup.get(v,-1) for v in f.next_episode_id_eval],int)
    kind=f.category.to_numpy();early=(kind=='early')&(code>=0)
    coverage=np.bincount(code[early],minlength=len(ep_ids))
    return {'frame':f,'events':event_frame.reset_index(drop=True),'ns':ns,'blocks':blocks,'block_end':block_end,
            'next_after_hour':np.minimum(np.searchsorted(ns,ns+int(3600e9),side='left'),block_end),
            'kind':kind,'code':code,'eligible':f.eligible.to_numpy(),'y':f.y.to_numpy(),
            'lead':f.lead_eval.to_numpy(),'coverage':coverage,'hours':float(f.loc[f.eligible,'cycle_seconds'].sum()/3600)}

def emit_alerts(positive,ctx,interval_hours=1.):
    positive=np.asarray(positive,bool);idx=np.flatnonzero(positive)
    if not len(idx):return np.array([],int)
    if np.isscalar(interval_hours):
        if interval_hours==1.:next_index=ctx['next_after_hour']
        else:next_index=np.minimum(np.searchsorted(ctx['ns'],ctx['ns']+int(interval_hours*3600e9)),ctx['block_end'])
    else:
        # 정기 알림 간격이 월별로 바뀌면 해당 시점의 간격을 적용합니다.
        interval=np.asarray(interval_hours,float)
        out=[];last=None;block=None
        for i in range(len(positive)):
            if ctx['blocks'][i]!=block:last=None;block=ctx['blocks'][i]
            if positive[i] and (last is None or ctx['ns'][i]-last>=interval[i]*3600e9):out.append(i);last=ctx['ns'][i]
        return np.asarray(out,int)
    out=[];j=0
    while j<len(idx):
        i=idx[j];out.append(i)
        j=int(np.searchsorted(idx,max(i+1,next_index[i]),side='left'))
    return np.asarray(out,int)

def metrics_from_alerts(idx,ctx,predicted=None):
    kinds=ctx['kind'][idx]
    hit=idx[(kinds=='early')&(ctx['code'][idx]>=0)]
    codes,first=np.unique(ctx['code'][hit],return_index=True)
    leads=ctx['lead'][hit[first]] if len(first) else np.array([])
    false=int((kinds=='background').sum());true=int((kinds=='early').sum())
    n=len(ctx['events']);covered=int((ctx['coverage']>0).sum())
    r={'events_detected':len(codes),'events_total':n,'events_covered':covered,
       'event_recall':len(codes)/n if n else np.nan,'false_alerts':false,
       'eligible_hours':ctx['hours'],'false_per_24h':false*24/ctx['hours'] if ctx['hours'] else np.nan,
       'early_alerts':true,'late_alerts':int((kinds=='late').sum()),'all_alerts':len(idx),
       'excluded_alerts':int(np.isin(kinds,['failure','recovery','unknown']).sum()),
       'notification_precision':true/(true+false) if true+false else 0.,
       'median_lead_hours':float(np.median(leads)) if len(leads) else np.nan}
    if predicted is not None:
        m=ctx['eligible'];y=ctx['y'][m];p=np.asarray(predicted)[m]
        tp=int(((y==1)&p).sum());fp=int(((y==0)&p).sum());fn=int(((y==1)&~p).sum());tn=int(((y==0)&~p).sum())
        pr=tp/(tp+fp) if tp+fp else 0.;rc=tp/(tp+fn) if tp+fn else 0.
        r.update(tp=tp,fp=fp,fn=fn,tn=tn,precision=pr,recall=rc,f1=2*pr*rc/(pr+rc) if pr+rc else 0.)
    return r

def curve_for_scores(scores,ctx,candidate_scope='all'):
    scores=np.asarray(scores,float)
    if not len(scores):
        return pd.DataFrame([{'threshold':np.inf,**metrics_from_alerts(np.array([],int),ctx)}])
    selected=scores if candidate_scope=='all' else scores[ctx['eligible']]
    assert np.isfinite(selected).all()
    values=np.unique(selected)
    if not len(values):values=np.array([float(scores.max())])
    thresholds=np.r_[np.nextafter(values[0],-np.inf),values]
    n=len(scores);m=len(thresholds)
    emitted=np.zeros((n,m),dtype=bool)
    last=np.full(m,ctx['ns'][0]-int(48*3600e9),dtype=np.int64)
    previous=None
    for i in range(n):
        if ctx['blocks'][i]!=previous:
            last[:]=ctx['ns'][i]-int(48*3600e9)
            previous=ctx['blocks'][i]
        hit=(scores[i]>thresholds)&(ctx['ns'][i]-last>=int(3600e9))
        emitted[i]=hit;last[hit]=ctx['ns'][i]
    kind=ctx['kind'];code=ctx['code']
    false=emitted[kind=='background'].sum(axis=0)
    early=emitted[kind=='early'].sum(axis=0)
    event_count=len(ctx['events'])
    lead=np.full((event_count,m),np.nan)
    detected=np.zeros((event_count,m),bool)
    for j in range(event_count):
        ids=np.flatnonzero((kind=='early')&(code==j))
        if len(ids):
            sub=emitted[ids];has=sub.any(axis=0);detected[j]=has
            first=sub.argmax(axis=0)
            lead[j,has]=ctx['lead'][ids[first[has]]]
    counts=detected.sum(axis=0)
    median=np.full(m,np.nan);ok=counts>0
    if ok.any():median[ok]=np.nanmedian(lead[:,ok],axis=0)
    rate=np.divide(early,early+false,out=np.zeros(m,float),where=(early+false)>0)
    return pd.DataFrame({'threshold':thresholds,'events_detected':counts,'events_total':event_count,
        'events_covered':int((ctx['coverage']>0).sum()),'event_recall':counts/event_count if event_count else np.nan,
        'false_alerts':false,'eligible_hours':ctx['hours'],
        'false_per_24h':false*24/ctx['hours'] if ctx['hours'] else np.nan,'early_alerts':early,
        'late_alerts':emitted[kind=='late'].sum(axis=0),'all_alerts':emitted.sum(axis=0),
        'excluded_alerts':emitted[np.isin(kind,['failure','recovery','unknown'])].sum(axis=0),
        'notification_precision':rate,'median_lead_hours':median})

def select_at_target(curve,target):
    total=int(curve.events_total.iloc[0]);required=int(math.ceil(target*total-1e-12))
    feasible=curve.loc[curve.events_detected.ge(required)].copy()
    if feasible.empty:return {'feasible':False,'required_events':required,'threshold':np.nan,'interval_hours':np.nan}
    feasible['_lead']=feasible.median_lead_hours.fillna(-np.inf)
    last='threshold' if 'threshold' in feasible else 'interval_hours'
    # 동률에서 더 많이 탐지하는 후보를 우선하되, 같은 실제 탐지수 여부는 평가에서 따로 확인합니다.
    best=feasible.sort_values(['false_alerts','events_detected','_lead',last],ascending=[True,False,False,False]).iloc[0].drop('_lead').to_dict()
    return {'feasible':True,'required_events':required,**best}

def reference_alerts(positive,ctx,hours=1.):
    result=[];last=None;previous=None
    for i,flag in enumerate(positive):
        if ctx['blocks'][i]!=previous:last=None;previous=ctx['blocks'][i]
        if flag and (last is None or ctx['ns'][i]-last>=hours*3600e9):result.append(i);last=ctx['ns'][i]
    return np.asarray(result,int)
