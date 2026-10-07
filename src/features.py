import numpy as np
import pandas as pd

RUN_COMP_VALUE = 0
A16 = [f'{sensor}_B{i}' for sensor in ['TP3', 'MC'] for i in range(1, 8)] + ['Trun_seconds', 'Tidle_seconds']

def extract_cycle_features(source, min_samples=1):
    timestamps = source['timestamp'].to_numpy(dtype='datetime64[ns]')
    values = source[['TP3', 'Motor_current']].to_numpy(dtype=float)
    state = source['COMP'].to_numpy()
    blocks = source['block'].to_numpy()
    valid = source['valid'].to_numpy()
    change = np.r_[True, (state[1:] != state[:-1]) | (blocks[1:] != blocks[:-1])]
    starts = np.flatnonzero(change)
    ends = np.r_[starts[1:], len(source)]
    records, rejected = ([], [])
    for k, left in enumerate(starts):
        if not valid[left] or state[left] != RUN_COMP_VALUE:
            continue
        reason = None
        if left == 0 or blocks[left - 1] != blocks[left]:
            reason = 'run_start_not_observed'
        elif k + 2 >= len(starts):
            reason = 'cycle_end_not_observed'
        elif blocks[starts[k + 2]] != blocks[left]:
            reason = 'gap_or_invalid_row_before_cycle_end'
        elif state[starts[k + 1]] == RUN_COMP_VALUE or state[starts[k + 2]] != RUN_COMP_VALUE:
            reason = 'invalid_state_sequence'
        if reason:
            rejected.append({'run_start': timestamps[left], 'reason': reason})
            continue
        middle, right = (starts[k + 1], starts[k + 2])
        run_s = float((timestamps[middle] - timestamps[left]) / np.timedelta64(1, 's'))
        idle_s = float((timestamps[right] - timestamps[middle]) / np.timedelta64(1, 's'))
        means, counts = ([], [])
        for a, b, bins in [(left, middle, 2), (middle, right, 5)]:
            offsets = (timestamps[a:b] - timestamps[a]) / np.timedelta64(1, 's')
            duration = float((timestamps[b] - timestamps[a]) / np.timedelta64(1, 's'))
            edges = np.linspace(0, duration, bins + 1)
            positions = np.searchsorted(offsets, edges, side='left')
            for lo, hi in zip(positions[:-1], positions[1:]):
                counts.append(int(hi - lo))
                means.append(values[a + lo:a + hi].mean(axis=0) if hi > lo else [np.nan, np.nan])
        if min(counts) < min_samples:
            rejected.append({'run_start': timestamps[left], 'cycle_end': timestamps[right], 'Trun_seconds': run_s, 'Tidle_seconds': idle_s, 'min_bin_samples': min(counts), 'reason': 'insufficient_bin_samples'})
            continue
        assert sum(counts) == right - left
        features = np.asarray(means) * (run_s + idle_s)
        row = {'cycle_id': f'cycle_{left:07d}', 'cycle_start': timestamps[left], 'idle_start': timestamps[middle], 'cycle_end': timestamps[right], 'n_samples': int(right - left), 'min_bin_samples': min(counts), 'cycle_seconds': run_s + idle_s, 'Trun_seconds': run_s, 'Tidle_seconds': idle_s}
        row.update({f'TP3_B{i + 1}': v for i, v in enumerate(features[:, 0])})
        row.update({f'MC_B{i + 1}': v for i, v in enumerate(features[:, 1])})
        records.append(row)
    if not records:
        raise ValueError('No complete cycles remain. Inspect sampling gaps and COMP states.')
    return (pd.DataFrame(records).sort_values('cycle_end').reset_index(drop=True), pd.DataFrame(rejected).reindex(columns=['run_start', 'cycle_end', 'Trun_seconds', 'Tidle_seconds', 'min_bin_samples', 'reason']))
