from pathlib import Path
import argparse, sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
from features import A16, extract_cycle_features
from labels import REPORT_END, merge_failure_records, connect_labels, split_membership

MAX_GAP_SECONDS = 30.0

def prepare_cycle_source(data, max_gap_seconds):
    columns = ['timestamp', 'TP3', 'Motor_current', 'COMP']
    source = data[columns].copy()
    source['timestamp'] = pd.to_datetime(source['timestamp'], errors='coerce')
    if source['timestamp'].isna().any():
        raise ValueError('Invalid timestamps: repair their source before segmenting.')
    original_rows = len(source)
    source = source.drop_duplicates().sort_values('timestamp', kind='stable').reset_index(drop=True)
    sensors = ['TP3', 'Motor_current', 'COMP']
    source[sensors] = source[sensors].apply(pd.to_numeric, errors='coerce')
    duplicate_time = source['timestamp'].duplicated(keep=False)
    finite = np.isfinite(source[sensors].to_numpy(dtype=float)).all(axis=1)
    source['valid'] = finite & source['COMP'].isin([0, 1]) & ~duplicate_time
    delta = source['timestamp'].diff().dt.total_seconds()
    linked = source['valid'] & source['valid'].shift(fill_value=False) & delta.gt(0) & delta.le(max_gap_seconds)
    source['block'] = (~linked).cumsum()
    audit = {'input_rows': original_rows, 'exact_duplicates_removed': original_rows - len(source), 'conflicting_timestamp_rows': int(duplicate_time.sum()), 'invalid_sensor_or_timestamp_rows': int((~source['valid']).sum()), 'gaps_over_limit': int(delta.gt(max_gap_seconds).sum()), 'median_step_seconds': float(delta[delta.gt(0)].median()), 'max_gap_seconds_observed': float(delta.max())}
    return (source, audit)

def preprocessing_flow(raw, source, audit, full, rejected, f):
    in_range = full.cycle_start.ge('2020-02-01') & full.cycle_end.lt(REPORT_END)
    rows = [
        {'stage':'raw_sensor_rows','unit':'rows','before':len(raw),'excluded':audit['exact_duplicates_removed'],'remaining':len(source),'reason':'exact duplicate rows'},
        {'stage':'source_valid_rows','unit':'rows','before':len(source),'excluded':int((~source.valid).sum()),'remaining':int(source.valid.sum()),'reason':'nonfinite/invalid COMP/conflicting time'},
        {'stage':'COMP_run_segments','unit':'run segments','before':len(full)+len(rejected),'excluded':len(rejected),'remaining':len(full),'reason':'unobserved boundary, gap, insufficient bin samples'},
        {'stage':'complete_cycles_Feb_July','unit':'cycles','before':len(full),'excluded':int((~in_range).sum()),'remaining':int(in_range.sum()),'reason':'outside complete-cycle date scope'}]
    for name,start,end in [('training','2020-03-01','2020-05-01'),('validation','2020-05-01','2020-07-01'),('July','2020-07-01','2020-08-01')]:
        d = f.loc[(f.cycle_start.ge(start) if name=='training' else f.cycle_end.ge(start)) & f.cycle_end.lt(end)].copy()
        mature = d.cycle_end + pd.Timedelta(hours=24) < pd.Timestamp(end) if name!='July' else pd.Series(True,index=d.index)
        rows.append({'stage':name+'_mature','unit':'cycles','before':len(d),'excluded':int((~mature).sum()),'remaining':int(mature.sum()),'reason':'last 24 hours require future labels' if name!='July' else 'all July rows retained'})
        d = d.loc[mature]
        keep = d.eligible & d.y.eq(0) & d.normal_candidate if name=='training' else d.eligible
        rows.append({'stage':name+('_normal_guard' if name=='training' else '_metric_eligible'),'unit':'cycles','before':len(d),'excluded':int((~keep).sum()),'remaining':int(keep.sum()),'reason':'normal candidate guard' if name=='training' else 'cycle metric eligibility'})
    return pd.DataFrame(rows)

from paths import repository_root
OUTPUT_FILES = {
    'features_and_labels':'data/APU_cycle_features_and_labels.csv',
    'splits':'data/APU_cycle_splits.csv',
    'episodes':'data/APU_failure_episodes.csv',
    'figure01':'figures/그림01_원자료와_완전주기_전처리.png',
    'figure02':'figures/그림02_정상주기_압력전류와_7구간.png',
}
CYCLE_DATES = ['cycle_start','idle_start','cycle_end']

def output_paths():
    root = repository_root()
    return {key:root/relative for key,relative in OUTPUT_FILES.items()}

def run_preprocessing(data_dir=None):
    package = repository_root()
    data_dir = (package / 'data') if data_dir is None else Path(data_dir).resolve()
    sensor = data_dir / 'MetroPT3(AirCompressor).csv'
    event_file = data_dir / 'apu_failure_events.csv'
    paths = output_paths()
    raw = pd.read_csv(sensor,usecols=['timestamp','TP3','Motor_current','COMP'],parse_dates=['timestamp'])
    assert raw.timestamp.notna().all() and raw.timestamp.is_monotonic_increasing
    assert not raw.timestamp.duplicated().any()
    assert raw[['TP3','Motor_current','COMP']].notna().all().all()
    source,audit = prepare_cycle_source(raw,MAX_GAP_SECONDS)
    full,rejected = extract_cycle_features(source,min_samples=1)
    cycles = full.copy()
    ns = source.timestamp.to_numpy(dtype='datetime64[ns]').astype('int64')
    ends = cycles.cycle_end.to_numpy(dtype='datetime64[ns]').astype('int64')
    right = np.searchsorted(ns,ends,side='left')
    cycles['raw_block'] = source.block.to_numpy()[right-1]
    cycles = cycles.loc[cycles.cycle_start.ge('2020-02-01') & cycles.cycle_end.lt(REPORT_END)].reset_index(drop=True)
    cycles['segment'] = (cycles.cycle_start.ne(cycles.cycle_end.shift()) | cycles.raw_block.ne(cycles.raw_block.shift())).cumsum()
    assert (cycles.cycle_start < cycles.idle_start).all() and (cycles.idle_start < cycles.cycle_end).all()
    events = pd.read_csv(event_file,parse_dates=['failure_start','failure_end'])
    episodes,mapping = merge_failure_records(events)
    f = connect_labels(cycles,episodes)
    membership = split_membership(f)
    flow = preprocessing_flow(raw,source,audit,full,rejected,f)
    train = f.loc[membership.train].copy().reset_index(drop=True)
    rows=[]
    for name in ['train','validation','july']:
        selected=f.loc[membership[name]]
        rows.append({'split':name,'all_cycles':len(selected),'eligible':int(selected.eligible.sum()),'positive':int(selected.loc[selected.eligible,'y'].sum()),'first_end':selected.cycle_end.min(),'last_end':selected.cycle_end.max(),'eligible_hours':selected.loc[selected.eligible,'cycle_seconds'].sum()/3600})
    split_summary = pd.DataFrame(rows)
    # Only the downstream model inputs are persisted; summaries stay in memory.
    tables = {'features_and_labels':f, 'splits':membership, 'episodes':episodes}
    for name,table in tables.items():
        table.to_csv(paths[name],index=False,encoding='utf-8-sig')
    from plot_preprocessing import create_figures
    example_values = create_figures(source,train,flow,paths)
    return {'output_files':paths,'features':cycles,'labeled':f,'splits':membership,
            'episodes':episodes,'record_links':mapping,'rejected':rejected,
            'summary':split_summary,'flow':flow,'example_values':example_values}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=None, help='Input directory; default: repository root/data')
    args=parser.parse_args()
    result=run_preprocessing(args.data_dir)
    print(result['summary'].to_string(index=False))
    for path in result['output_files'].values():print(path)

if __name__=='__main__':main()


def _read_table(key, dates=()):
    return pd.read_csv(output_paths()[key],parse_dates=list(dates),float_precision='round_trip')

def load_cycles():
    frame=_read_table('features_and_labels',CYCLE_DATES)
    frame['next_episode_id_eval']=frame.next_episode_id_eval.fillna('')
    assert frame.cycle_id.is_unique and frame.cycle_end.is_monotonic_increasing
    return frame

def load_splits(frame):
    split=_read_table('splits')
    assert split.cycle_id.is_unique and set(split.cycle_id)==set(frame.cycle_id)
    split=split.set_index('cycle_id').loc[frame.cycle_id].reset_index()
    for name in ['train','validation','july']:
        assert pd.api.types.is_bool_dtype(split[name]), name
    assert split[['train','validation','july']].sum(axis=1).le(1).all()
    return split

def load_episodes():
    return _read_table('episodes',['start','end_exclusive'])
