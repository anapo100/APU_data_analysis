"""APU staged analysis: functions have no import-time data processing."""
import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits
from features import A16

def error_feature_summary(p, feat, metrics):
    COLS = ['pressure_cycle_mean', 'current_cycle_mean', 'pressure_run_mean', 'pressure_idle_mean', 'current_run_mean', 'current_idle_mean', 'cycle_minutes', 'run_fraction']
    extra = ['cycle_id', 'normal_candidate', 'duty_stratum'] + COLS + [f'{s}_mean_B{i}' for s in ['TP3', 'MC'] for i in range(1, 8)]
    errors = p.merge(feat[extra], on='cycle_id', validate='many_to_one')
    errors = errors.loc[errors.eligible].copy()
    errors['outcome'] = np.select([errors.y.eq(0) & ~errors.prediction, errors.y.eq(0) & errors.prediction, errors.y.eq(1) & ~errors.prediction, errors.y.eq(1) & errors.prediction], ['TN', 'FP', 'FN', 'TP'], default='INVALID')
    assert not errors.outcome.eq('INVALID').any()
    for mr in metrics.itertuples():
        counts = errors.loc[errors.period.eq(mr.period) & errors.method.eq(mr.method), 'outcome'].value_counts()
        for kind in ['TN', 'FP', 'FN', 'TP']:
            assert counts.get(kind, 0) == getattr(mr, kind.lower())
    summ = []
    for (period, m), d in errors.groupby(['period', 'method'], sort=False):
        for kind in ['TN', 'FP', 'FN', 'TP']:
            q = d.loc[d.outcome.eq(kind)]
            for col in COLS:
                v = q[col]
                summ.append({'period': period, 'method': m, 'outcome': kind, 'feature': col, 'n': len(v), 'median': v.median(), 'q25': v.quantile(0.25), 'q75': v.quantile(0.75), 'min': v.min(), 'max': v.max(), 'mean': v.mean()})
    feature_summary = pd.DataFrame(summ)
    effects = []
    for (period, m), d in errors.groupby(['period', 'method'], sort=False):
        for error, control in [('FP', 'TN'), ('FN', 'TP')]:
            for col in COLS:
                for state in [0, 1, 2, 3]:
                    z = d if state == 0 else d.loc[d.duty_stratum.eq(state)]
                    a = z.loc[z.outcome.eq(error), col].to_numpy()
                    b = np.sort(z.loc[z.outcome.eq(control), col].to_numpy())
                    prob = float((np.searchsorted(b, a, 'left') + np.searchsorted(b, a, 'right')).sum() / (2 * len(a) * len(b))) if len(a) and len(b) else np.nan
                    effects.append({'period': period, 'method': m, 'error': error, 'control': control, 'duty_stratum': state, 'feature': col, 'n_error': len(a), 'n_control': len(b), 'median_error': np.median(a) if len(a) else np.nan, 'median_control': np.median(b) if len(b) else np.nan, 'median_difference': np.median(a) - np.median(b) if len(a) and len(b) else np.nan, 'prob_error_greater_half_ties': prob})
    effects = pd.DataFrame(effects)
    return {'errors':errors,'summary':feature_summary,'effects':effects}

def match_error_cases(p, feat):
    extra = [c for c in feat.columns if c not in p.columns or c == 'cycle_id']
    e = p.loc[p.period.eq('July') & p.eligible].merge(feat[extra], on='cycle_id', validate='many_to_one')
    e['outcome'] = np.select([e.y.eq(0) & ~e.prediction, e.y.eq(0) & e.prediction, e.y.eq(1) & ~e.prediction, e.y.eq(1) & e.prediction], ['TN', 'FP', 'FN', 'TP'], default='INVALID')
    rules = {'maximum_time_hours': 24, 'cycle_duration_ratio': [0.8, 1.25], 'absolute_run_fraction_difference': 0.03, 'absolute_mean_run_current_A': 0.5, 'absolute_mean_run_pressure_bar': 0.3, 'selection': 'earliest error with any eligible match; closest time control then cycle id; FP must have notification; FN control TP same episode', 'limitations': 'COMP duty and mean load proxies; actual operating load and maintenance state unavailable'}
    pairs = []
    selection_attempts = []
    selected_cases = []
    for method, kind, control in [('LOF', 'FP', 'TN'), ('IF', 'FN', 'TP')]:
        candidates = e.loc[e.method.eq(method) & e.outcome.eq(kind)]
        if kind == 'FP':
            candidates = candidates.loc[candidates.notification]
        candidates = candidates.sort_values(['cycle_end', 'cycle_id'])
        for _, r in candidates.iterrows():
            pool = e.loc[e.method.eq(method) & e.outcome.eq(control)].copy()
            if kind == 'FN':
                pool = pool.loc[pool.next_episode_id_eval.eq(r.next_episode_id_eval)]
            else:
                pool = pool.loc[pool.normal_candidate]
            pool['dt_hours'] = (pool.cycle_end - r.cycle_end).abs().dt.total_seconds() / 3600
            ratio = pool.cycle_minutes / r.cycle_minutes
            mask = pool.dt_hours.le(24) & ratio.between(0.8, 1.25) & pool.run_fraction.sub(r.run_fraction).abs().le(0.03) & pool.current_run_mean.sub(r.current_run_mean).abs().le(0.5) & pool.pressure_run_mean.sub(r.pressure_run_mean).abs().le(0.3)
            q = pool.loc[mask].sort_values(['dt_hours', 'cycle_end', 'cycle_id'])
            selection_attempts.append({'method': method, 'error': r.cycle_id, 'error_time': r.cycle_end, 'eligible_controls': len(q)})
            if len(q):
                z = q.iloc[0]
                pairs.append({'method': method, 'error_kind': kind, 'error_id': r.cycle_id, 'control_id': z.cycle_id, 'time_gap_hours': z.dt_hours, 'duration_ratio': z.cycle_minutes / r.cycle_minutes, 'run_fraction_difference': z.run_fraction - r.run_fraction, 'current_run_mean_difference': z.current_run_mean - r.current_run_mean, 'pressure_run_mean_difference': z.pressure_run_mean - r.pressure_run_mean, 'eligible_controls': len(q)})
                for role, row in [('error', r), ('control', z)]:
                    selected_cases.append({'case': kind, 'role': role, **row.to_dict()})
                break
        else:
            pairs.append({'method': method, 'error_kind': kind, 'matched': False})
    cases = pd.DataFrame(selected_cases) if selected_cases else pd.DataFrame(columns=['case', 'role'] + e.columns.tolist())
    return {'cases':cases,'pairs':pd.DataFrame(pairs),'attempts':pd.DataFrame(selection_attempts),'eligible_rows':e,'rules':rules}

def score_feature_associations(e):
    values = ['cycle_minutes', 'pressure_cycle_mean', 'current_cycle_mean', 'pressure_cycle_sd', 'current_cycle_sd', 'pressure_cycle_p95_p05', 'current_cycle_p95_p05', 'run_fraction']
    correlations = []
    for (method, group), d in e.groupby(['method', 'category']):
        for col in values + ['current_idle_mean', 'current_run_mean']:
            rho = float(spearmanr(d[col], d.score).statistic)
            correlations.append({'method': method, 'label_group': group, 'feature': col, 'n_cycles': len(d), 'spearman_rho': rho, 'inferential_p_value_reported': False})
    return pd.DataFrame(correlations)

def diagnose_cases(cases, raw, train, bundle):
    scaler = bundle['scaler']
    Xtrain = scaler.transform(train[A16].to_numpy(float))
    bundles = {m: {'model': model, 'scaler': scaler} for m, model in bundle['models'].items()}
    raw_windows = {}
    decomposition = {}
    neighbor_rows = []
    neighbor_summary = []
    contributions = []
    paths = []
    swaps = []
    for _, row in cases.iterrows():
        x = scaler.transform(row[A16].to_numpy(float)[None, :])
        model = bundles[row.method]['model']
        with threadpool_limits(limits=1):
            score = float(-model.score_samples(x)[0])
        assert np.isclose(score, row.score, atol=1e-12, rtol=0)
        if row.method == 'LOF':
            distances, inds = model.kneighbors(x, n_neighbors=model.n_neighbors_)
            distances = distances[0]
            inds = inds[0]
            kth = model._distances_fit_X_[inds, -1]
            reach = np.maximum(distances, kth)
            lrd = 1 / (reach.mean() + 1e-10)
            rebuilt = float(np.mean(model._lrd[inds] / lrd))
            assert np.isclose(rebuilt, score, atol=1e-12, rtol=0)
            sq = (x - Xtrain[inds]) ** 2
            shares = sq.mean(axis=0) / sq.sum(axis=1).mean()
            assert np.isclose(shares.sum(), 1)
            for j in range(len(inds)):
                neighbor_rows.append({'role': row.role, 'query_cycle': row.cycle_id, 'neighbor_rank': j + 1, 'train_cycle': train.iloc[inds[j]].cycle_id, 'train_end': train.iloc[inds[j]].cycle_end, 'distance': distances[j], 'neighbor_k_distance': kth[j], 'reachability_distance': reach[j], 'neighbor_lrd': model._lrd[inds[j]]})
            for name, val in zip(A16, shares):
                contributions.append({'role': row.role, 'feature': name, 'mean_squared_distance_share': val})
            neighbor_summary.append({'role': row.role, 'cycle_id': row.cycle_id, 'score': score, 'threshold': row.threshold, 'mean_distance': distances.mean(), 'mean_reachability_distance': reach.mean(), 'query_local_reachability_density': lrd, 'mean_neighbor_density': model._lrd[inds].mean(), 'rebuilt_score': rebuilt})
        else:
            tree_lengths = []
            for tree, features in zip(model.estimators_, model.estimators_features_):
                xx = x[:, features].astype(np.float32)
                leaf = tree.apply(xx)
                n = tree.tree_.n_node_samples[leaf][0]
                adjustment = 0 if n <= 1 else 1 if n == 2 else 2 * (np.log(n - 1) + np.euler_gamma) - 2 * (n - 1) / n
                depth = tree.decision_path(xx).sum(axis=1).A1[0] - 1
                tree_lengths.append(depth + adjustment)
            n = model.max_samples_
            denom = 2 * (np.log(n - 1) + np.euler_gamma) - 2 * (n - 1) / n
            rebuilt = 2 ** (-np.mean(tree_lengths) / denom)
            assert np.isclose(rebuilt, score, atol=1e-12, rtol=0)
            paths.append({'role': row.role, 'cycle_id': row.cycle_id, 'score': score, 'threshold': row.threshold, 'mean_adjusted_path_length': np.mean(tree_lengths), 'path_q25': np.quantile(tree_lengths, 0.25), 'path_q75': np.quantile(tree_lengths, 0.75), 'rebuilt_score': rebuilt})
    if len(cases.loc[cases.method.eq('IF')]) == 2:
        a = cases.loc[cases.method.eq('IF') & cases.role.eq('error')].iloc[0]
        b = cases.loc[cases.method.eq('IF') & cases.role.eq('control')].iloc[0]
        model = bundles['IF']['model']
        matrix = {}
        for s, profile in [('FN', a), ('TP', b)]:
            for t, timing in [('FN', a), ('TP', b)]:
                v = np.r_[profile[A16[:14]].to_numpy(float) / profile.cycle_seconds * timing.cycle_seconds, timing[A16[14:]].to_numpy(float)]
                with threadpool_limits(limits=1):
                    score = float(-model.score_samples(scaler.transform(v[None, :]))[0])
                matrix[s, t] = score
                swaps.append({'sensor_profile_from': s, 'timing_from': t, 'IF_score': score, 'threshold': a.threshold, 'interpretation': 'constructed pairwise sensitivity, not observed cycle or causal attribution'})
        profile_effect = 0.5 * (matrix['TP', 'FN'] - matrix['FN', 'FN'] + (matrix['TP', 'TP'] - matrix['FN', 'TP']))
        timing_effect = 0.5 * (matrix['FN', 'TP'] - matrix['FN', 'FN'] + (matrix['TP', 'TP'] - matrix['TP', 'FN']))
        assert np.isclose(profile_effect + timing_effect, b.score - a.score)
        decomposition = {'profile_score_change': profile_effect, 'timing_score_change': timing_effect, 'total_observed_score_change': b.score - a.score, 'not_causal': True}
    for _, row in cases.iterrows():
        rr = raw.loc[raw.timestamp.ge(row.cycle_start) & raw.timestamp.lt(row.cycle_end)]
        for sensor, label in [('TP3', 'pressure'), ('Motor_current', 'current')]:
            assert np.isclose(rr[sensor].mean(), row[f'{label}_cycle_mean'], atol=1e-07)
            assert np.isclose(rr[sensor].std(ddof=0), row[f'{label}_cycle_sd'], atol=1e-06)
        view = raw.loc[raw.timestamp.ge(row.cycle_start - pd.Timedelta(minutes=40)) & raw.timestamp.le(row.cycle_end + pd.Timedelta(minutes=40)), ['timestamp', 'TP3', 'Motor_current', 'COMP']]
        raw_windows[row['case'], row.role] = view
    return {'neighbors':pd.DataFrame(neighbor_rows),'neighbor_summary':pd.DataFrame(neighbor_summary),'distance_contributions':pd.DataFrame(contributions),'if_paths':pd.DataFrame(paths),'if_swaps':pd.DataFrame(swaps),'if_decomposition':decomposition,'raw_windows':raw_windows}
