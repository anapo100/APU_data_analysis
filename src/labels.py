import numpy as np
import pandas as pd

REPORT_END = pd.Timestamp('2020-08-01')
MIN_LEAD = 2.
MAX_LEAD = 24.
RECOVERY_H = 2.

def merge_failure_records(events):
    events = events.copy()
    events['end_exclusive'] = events.failure_end.dt.floor('min') + pd.Timedelta(minutes=1)
    merged = []
    for ep in events.sort_values('failure_start').itertuples():
        if merged and ep.failure_start <= merged[-1]['end_exclusive']:
            merged[-1]['end_exclusive'] = max(merged[-1]['end_exclusive'], ep.end_exclusive)
            merged[-1]['event_ids'] += '|' + str(ep.event_id)
        else:
            merged.append({'start':ep.failure_start, 'end_exclusive':ep.end_exclusive, 'event_ids':str(ep.event_id)})
    episodes = pd.DataFrame(merged)
    episodes.insert(0, 'episode_id', [f'episode_{i+1:02d}' for i in range(len(merged))])
    for column in ['start','end_exclusive']:
        episodes[column] = episodes[column].astype('datetime64[ns]')
    membership = episodes.assign(event_id=episodes.event_ids.str.split('|')).explode('event_id')
    mapping = events.merge(membership[['episode_id','event_id','start','end_exclusive']], on='event_id', suffixes=('_record','_episode'), validate='one_to_one')
    return episodes, mapping

def label_frame(frame, episodes, knowledge_end=REPORT_END):
    f=frame.copy().reset_index(drop=True);t=f.cycle_end
    nxt=pd.merge_asof(f[['cycle_end']],episodes[['start','episode_id']],left_on='cycle_end',right_on='start',direction='forward',allow_exact_matches=False)
    f['next_episode_id_eval']=nxt.episode_id.fillna('')
    f['lead_eval']=(nxt.start-t).dt.total_seconds()/3600
    overlap=np.zeros(len(f),bool);recovery=overlap.copy()
    for ep in episodes.itertuples():
        overlap|=(((f.cycle_start<ep.end_exclusive)&(t>ep.start))|t.between(ep.start,ep.end_exclusive,inclusive='left')).to_numpy()
        recovery|=t.between(ep.end_exclusive,ep.end_exclusive+pd.Timedelta(hours=RECOVERY_H),inclusive='left').to_numpy()
    f['category']='background'
    f.loc[f.lead_eval.between(MIN_LEAD,MAX_LEAD),'category']='early'
    f.loc[f.lead_eval.ge(0)&f.lead_eval.lt(MIN_LEAD),'category']='late'
    f.loc[t+pd.Timedelta(hours=MAX_LEAD)>=knowledge_end,'category']='unknown'
    f.loc[recovery,'category']='recovery';f.loc[overlap,'category']='failure'
    f['eligible']=f.category.isin(['early','background']);f['y']=f.category.eq('early').astype(int)
    return f

def connect_labels(cycles, episodes):
    f = label_frame(cycles, episodes)
    guard = np.zeros(len(f), bool)
    for ep in episodes.itertuples():
        guard |= ((f.cycle_start < ep.end_exclusive + pd.Timedelta(hours=2)) & (f.cycle_end >= ep.start - pd.Timedelta(hours=24))).to_numpy()
    f['normal_candidate'] = ~guard
    return f

def split_membership(f):
    train = f.cycle_start.ge('2020-03-01') & (f.cycle_end + pd.Timedelta(hours=24) < pd.Timestamp('2020-05-01')) & f.eligible & f.y.eq(0) & f.normal_candidate
    validation = f.cycle_end.ge('2020-05-01') & (f.cycle_end + pd.Timedelta(hours=24) < pd.Timestamp('2020-07-01'))
    july = f.cycle_end.ge('2020-07-01') & f.cycle_end.lt('2020-08-01')
    assert not (train & validation).any() and not (validation & july).any() and not (train & july).any()
    return pd.DataFrame({'cycle_id':f.cycle_id, 'train':train, 'validation':validation, 'july':july})
