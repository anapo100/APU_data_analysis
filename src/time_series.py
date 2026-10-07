import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

def cycle_signal_statistics(raw, f, train_ids):
    feat = f.copy()
    ns = raw.timestamp.to_numpy(dtype='datetime64[ns]')
    idx = {k: np.searchsorted(ns, f[k].to_numpy(dtype='datetime64[ns]')) for k in ['cycle_start', 'idle_start', 'cycle_end']}
    for sensor, label in [('TP3', 'pressure'), ('Motor_current', 'current')]:
        x = raw[sensor].to_numpy(float)
        cs = np.r_[0.0, x.cumsum()]
        ss = np.r_[0.0, (x * x).cumsum()]
        for phase, a, b in [('cycle', 'cycle_start', 'cycle_end'), ('run', 'cycle_start', 'idle_start'), ('idle', 'idle_start', 'cycle_end')]:
            n = idx[b] - idx[a]
            mean = (cs[idx[b]] - cs[idx[a]]) / n
            feat[f'{label}_{phase}_mean'] = mean
            feat[f'{label}_{phase}_sd'] = np.sqrt(np.maximum(0, (ss[idx[b]] - ss[idx[a]]) / n - mean ** 2))
        feat[f'{label}_cycle_p95_p05'] = [np.quantile(x[a:b], 0.95) - np.quantile(x[a:b], 0.05) for a, b in zip(idx['cycle_start'], idx['cycle_end'])]
    feat['cycle_minutes'] = feat.cycle_seconds / 60
    feat['run_fraction'] = feat.Trun_seconds / feat.cycle_seconds
    for s in ['TP3', 'MC']:
        for i in range(1, 8):
            feat[f'{s}_mean_B{i}'] = feat[f'{s}_B{i}'] / feat.cycle_seconds
    train = feat.loc[feat.cycle_id.isin(train_ids)]
    cut = train.run_fraction.quantile([1 / 3, 2 / 3]).to_numpy()
    feat['duty_stratum'] = np.searchsorted(cut, feat.run_fraction, side='right') + 1
    return feat

def summarize_time_series(feat):
    values = ['cycle_minutes', 'pressure_cycle_mean', 'current_cycle_mean', 'pressure_cycle_sd', 'current_cycle_sd', 'pressure_cycle_p95_p05', 'current_cycle_p95_p05', 'run_fraction']
    ts = feat.loc[feat.cycle_end.between('2020-03-01', '2020-07-31 23:59:59')].copy()
    ts['date'] = ts.cycle_end.dt.floor('D')
    ts['month'] = ts.cycle_end.dt.strftime('%Y-%m')
    daily = []
    summary = []
    for day, d in ts.groupby('date'):
        for col in values:
            daily.append({'date': day, 'feature': col, 'n_cycles': len(d), 'median': d[col].median(), 'q25': d[col].quantile(0.25), 'q75': d[col].quantile(0.75), 'mean': d[col].mean(), 'sd_across_cycles': d[col].std(ddof=0)})
    for (month, kind), d in ts.loc[ts.eligible].groupby(['month', 'category']):
        for col in values:
            summary.append({'month': month, 'category': kind, 'feature': col, 'n_cycles': len(d), 'median': d[col].median(), 'q25': d[col].quantile(0.25), 'q75': d[col].quantile(0.75), 'mean': d[col].mean()})
    rolling = ts[['cycle_id', 'cycle_end', 'raw_block'] + values[:3]].copy().set_index('cycle_end')
    for col in values[:3]:
        rolling[col + '_past24h_mean'] = rolling[col].rolling('24h', min_periods=3).mean()
        rolling[col + '_past24h_sd'] = rolling[col].rolling('24h', min_periods=3).std(ddof=0)
        rolling[col + '_change'] = rolling[col].diff().where(rolling.raw_block.eq(rolling.raw_block.shift()))
    return {'daily':pd.DataFrame(daily),'monthly':pd.DataFrame(summary),'rolling':rolling.reset_index()}


from paths import repository_root
OUTPUT_FILES = {
    'signal_statistics':'data/APU_cycle_signal_statistics.csv',
    'figure03':'figures/그림03_일별_중앙값과_관측분포.png',
}

def output_paths():
    return {key:repository_root()/relative for key,relative in OUTPUT_FILES.items()}

def save_signal_statistics(table):
    table.to_csv(output_paths()['signal_statistics'],index=False,encoding='utf-8-sig')

def load_signal_statistics(frame):
    stats=pd.read_csv(output_paths()['signal_statistics'],float_precision='round_trip')
    assert stats.cycle_id.is_unique and set(stats.cycle_id)==set(frame.cycle_id)
    return frame.merge(stats,on='cycle_id',how='left',validate='one_to_one')
