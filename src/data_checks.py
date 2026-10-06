import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

def inspect_data(raw, events):
    quality = []
    for col in raw:
        s = raw[col]
        quality.append({'variable': col, 'rows': len(s), 'missing': int(s.isna().sum()), 'nunique': s.nunique(), 'minimum': str(s.min()), 'maximum': str(s.max()), 'use': 'input/segmentation' if col in ['timestamp', 'TP3', 'Motor_current', 'COMP'] else 'not_selected_in_A16'})
    assert raw.timestamp.notna().all()
    assert raw.timestamp.is_monotonic_increasing
    assert not raw.timestamp.duplicated().any()
    assert raw[['TP3', 'Motor_current', 'COMP']].notna().all().all()
    delta = raw.timestamp.diff().dt.total_seconds()
    overview = pd.DataFrame([{'rows': len(raw), 'first': raw.timestamp.min(), 'last': raw.timestamp.max(), 'failure_records': len(events), 'gaps_over_30_seconds': int(delta.gt(30).sum()), 'median_positive_step_seconds': float(delta.loc[delta.gt(0)].median())}])
    coverage = []
    for month, d in raw.loc[raw.timestamp.lt('2020-08-01')].groupby(raw.timestamp.dt.to_period('M')):
        dt = d.timestamp.diff().dt.total_seconds()
        coverage.append({'month': str(month), 'rows': len(d), 'connected_hours': dt.loc[dt.gt(0) & dt.le(30)].sum() / 3600})
    return {'quality':pd.DataFrame(quality),'overview':overview,'coverage':pd.DataFrame(coverage),'records':events.copy()}


from paths import repository_root

def read_sensor(all_columns=False):
    columns = None if all_columns else ['timestamp','TP3','Motor_current','COMP']
    return pd.read_csv(repository_root()/'data/MetroPT3(AirCompressor).csv',usecols=columns,parse_dates=['timestamp'])

def read_failure_records():
    return pd.read_csv(repository_root()/'data/apu_failure_events.csv',parse_dates=['failure_start','failure_end'])
