"""APU staged analysis: functions have no import-time data processing."""
import sys
sys.dont_write_bytecode = True
import itertools
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from features import A16
from evaluation import make_context, emit_alerts, metrics_from_alerts
from modeling import score_model
METHODS=['ZScore','IF','LOF']
CATS=['early','background','late','failure','recovery','unknown']

def summarize_predictions(p, episodes):
    metric_rows = []
    event_rows = []
    for (period, method), points in p.groupby(['period', 'method'], sort=False):
        points = points.sort_values('cycle_end').reset_index(drop=True)
        begin, end = ('2020-05-01', '2020-07-01') if period == 'validation' else ('2020-07-01', '2020-08-01')
        event_frame = episodes.loc[episodes.start.ge(begin) & episodes.start.lt(end)]
        ctx = make_context(points, event_frame)
        predicted = points.score.to_numpy() > points.threshold.to_numpy()
        assert np.array_equal(predicted, points.prediction.to_numpy())
        idx = emit_alerts(predicted, ctx)
        assert np.array_equal(idx, np.flatnonzero(points.notification.to_numpy()))
        stats = metrics_from_alerts(idx, ctx, predicted)
        metric_rows.append({'period': period, 'method': method, **stats})
        for ep in event_frame.itertuples():
            early = points.category.eq('early') & points.next_episode_id_eval.eq(ep.episode_id)
            hits = points.loc[early & points.notification]
            event_rows.append({'period': period, 'method': method, 'episode_id': ep.episode_id, 'start': ep.start, 'early_cycles': int(early.sum()), 'observable': bool(early.any()), 'detected': bool(len(hits)), 'first_alert': hits.cycle_end.min() if len(hits) else pd.NaT, 'lead_hours': hits.lead_eval.iloc[0] if len(hits) else np.nan})
    return {'metrics':pd.DataFrame(metric_rows),'events':pd.DataFrame(event_rows)}

def first_alert_comparisons(p, events):
    lead_rows = []
    for er in events.itertuples():
        q = p.loc[p.period.eq(er.period) & p.method.eq(er.method) & p.notification & p.category.eq('early') & p.next_episode_id_eval.eq(er.episode_id)].sort_values('cycle_end')
        first = q.cycle_end.iloc[0] if len(q) else pd.NaT
        lead = (er.start - first).total_seconds() / 3600 if len(q) else np.nan
        assert bool(len(q)) == er.detected
        if len(q):
            assert first == er.first_alert and np.isclose(lead, er.lead_hours)
        lead_rows.append({'period': er.period, 'method': er.method, 'episode_id': er.episode_id, 'start': er.start, 'early_cycles': er.early_cycles, 'observable': er.observable, 'detected': bool(len(q)), 'first_alert': first, 'lead_hours': lead, 'early_notifications': len(q), 'repeat_early_notifications': max(len(q) - 1, 0)})
    lead = pd.DataFrame(lead_rows)
    pair_rows = []
    summary = []
    for period in ['validation', 'July']:
        for a, b in itertools.combinations(METHODS, 2):
            wide = lead.loc[lead.period.eq(period)].pivot(index='episode_id', columns='method', values='lead_hours')
            common = wide.dropna(subset=[a, b])
            for eid, row in common.iterrows():
                pair_rows.append({'period': period, 'model_a': a, 'model_b': b, 'episode_id': eid, 'lead_a_hours': row[a], 'lead_b_hours': row[b], 'a_minus_b_hours': row[a] - row[b]})
            summary.append({'period': period, 'model_a': a, 'model_b': b, 'common_detected': len(common), 'a_total_detected': int(lead.loc[lead.period.eq(period) & lead.method.eq(a), 'detected'].sum()), 'b_total_detected': int(lead.loc[lead.period.eq(period) & lead.method.eq(b), 'detected'].sum()), 'median_a_minus_b_hours': float((common[a] - common[b]).median()) if len(common) else np.nan, 'a_earlier': int((common[a] > common[b]).sum()), 'b_earlier': int((common[a] < common[b]).sum()), 'same_time': int((common[a] == common[b]).sum())})
    pairs = pd.DataFrame(pair_rows)
    paired_summary = pd.DataFrame(summary)
    return {'lead':lead,'pairs':pairs,'summary':paired_summary}

def notification_burden(p, episodes, metrics, lead):
    all_rows = []
    burden = []
    daily_rows = []
    for (period, method), g in p.groupby(['period', 'method'], sort=False):
        g = g.sort_values('cycle_end').copy()
        last = None
        block = None
        emitted = []
        for r in g.itertuples():
            if r.raw_block != block:
                last = None
                block = r.raw_block
            flag = bool(r.prediction and (last is None or (r.cycle_end - last).total_seconds() >= 3600))
            emitted.append(flag)
            if flag:
                last = r.cycle_end
        assert np.array_equal(emitted, g.notification.to_numpy())
        new_run = g.prediction & (~g.prediction.shift(fill_value=False) | g.segment.ne(g.segment.shift()))
        g['positive_run'] = new_run.cumsum()
        a = g.loc[g.notification].copy()
        a['within_signal_run_order'] = a.groupby('positive_run').cumcount() + 1
        a['repeat_signal'] = a.within_signal_run_order.gt(1)
        a['event_attribution'] = ''
        a.loc[a.category.isin(['early', 'late']), 'event_attribution'] = a.loc[a.category.isin(['early', 'late']), 'next_episode_id_eval']
        for idx, r in a.loc[a.category.isin(['failure', 'recovery'])].iterrows():
            if r.category == 'failure':
                z = episodes.loc[(episodes.start < r.cycle_end) & (episodes.end_exclusive > r.cycle_start)]
            else:
                z = episodes.loc[(episodes.end_exclusive <= r.cycle_end) & (episodes.end_exclusive + pd.Timedelta(hours=2) > r.cycle_end)]
            if len(z):
                a.loc[idx, 'event_attribution'] = z.iloc[0 if r.category == 'failure' else -1].episode_id
        a['alert_id'] = period + '_' + method + '_' + a.cycle_id
        all_rows.append(a)
        counts = a.category.value_counts().reindex(CATS, fill_value=0)
        mr = metrics.loc[metrics.period.eq(period) & metrics.method.eq(method)].iloc[0]
        assert counts.sum() == len(a) == mr.all_alerts
        assert counts['background'] == mr.false_alerts and counts['early'] == mr.early_alerts
        assert counts['late'] == mr.late_alerts and counts[['failure', 'recovery', 'unknown']].sum() == mr.excluded_alerts
        r = {'period': period, 'method': method, 'all_notifications': len(a), **counts.to_dict(), 'first_signal_notifications': int((~a.repeat_signal).sum()), 'repeat_signal_notifications': int(a.repeat_signal.sum()), 'suppressed_positive_cycles': int(g.prediction.sum() - len(a)), 'early_event_repeats': int(lead.loc[lead.period.eq(period) & lead.method.eq(method), 'repeat_early_notifications'].sum())}
        assert r['first_signal_notifications'] + r['repeat_signal_notifications'] == r['all_notifications']
        burden.append(r)
        days = pd.date_range('2020-05-01' if period == 'validation' else '2020-07-01', '2020-06-30' if period == 'validation' else '2020-07-31', freq='D')
        for day in days:
            aq = a.loc[a.cycle_end.dt.normalize().eq(day)]
            gq = g.loc[g.cycle_end.dt.normalize().eq(day)]
            dc = aq.category.value_counts().reindex(CATS, fill_value=0)
            daily_rows.append({'period': period, 'method': method, 'date': day, 'scored_cycles': len(gq), 'all_notifications': len(aq), **dc.to_dict()})
    alerts = pd.concat(all_rows, ignore_index=True)
    burden = pd.DataFrame(burden)
    daily = pd.DataFrame(daily_rows)
    assert alerts.alert_id.is_unique
    cross = alerts.groupby(['period', 'method', 'category', 'repeat_signal']).size().rename('notifications').reset_index()
    assert cross.notifications.sum() == len(alerts)
    attributed = alerts.loc[alerts.event_attribution.ne('')]
    event_counts = attributed.groupby(['period', 'method', 'event_attribution', 'category']).size().unstack(fill_value=0).reindex(columns=['early', 'late', 'failure', 'recovery'], fill_value=0).reset_index()
    event_counts['total_associated'] = event_counts[['early', 'late', 'failure', 'recovery']].sum(axis=1)
    event_counts['additional_associated'] = np.maximum(event_counts.total_associated - 1, 0)
    event_counts['additional_early'] = np.maximum(event_counts.early - 1, 0)
    stats = []
    for (period, method), d in daily.groupby(['period', 'method'], sort=False):
        v = d.all_notifications
        obs = d.loc[d.scored_cycles.gt(0), 'all_notifications']
        assert v.sum() == int(burden.loc[burden.period.eq(period) & burden.method.eq(method), 'all_notifications'].iloc[0])
        stats.append({'period': period, 'method': method, 'calendar_days': len(v), 'observed_score_days': len(obs), 'mean_calendar_day': v.mean(), 'median_calendar_day': v.median(), 'p90_calendar_day': v.quantile(0.9), 'p95_calendar_day': v.quantile(0.95), 'max_calendar_day': v.max(), 'max_dates': '|'.join(d.loc[v.eq(v.max()), 'date'].dt.strftime('%Y-%m-%d')), 'mean_observed_day': obs.mean(), 'zero_notification_days': int(v.eq(0).sum())})
    daily_stats = pd.DataFrame(stats)
    return {'alerts':alerts,'burden':burden,'daily':daily,'daily_stats':daily_stats,'cross':cross,'event_counts':event_counts}

def event_cycle_composition(p):
    event_perf = []
    for (method, ep), d in p.loc[p.period.eq('July') & p.category.eq('early')].groupby(['method', 'next_episode_id_eval']):
        event_perf.append({'method': method, 'episode': ep, 'positive_cycles': len(d), 'TP': int(d.prediction.sum()), 'FN': int((~d.prediction).sum()), 'cycle_recall': d.prediction.mean(), 'early_notifications': int(d.notification.sum()), 'repeat_after_first': max(0, int(d.notification.sum()) - 1)})
    burden = []
    for method, d in p.loc[p.period.eq('July')].groupby('method'):
        alerts = d.loc[d.notification]
        early = alerts.loc[alerts.category.eq('early')]
        fp = int(alerts.category.eq('background').sum())
        repeated = len(early) - early.next_episode_id_eval.nunique()
        burden.append({'method': method, 'all_notifications': len(alerts), 'background_false_notifications': fp, 'false_share_of_all': fp / len(alerts), 'early_notifications': len(early), 'repeat_early_after_first': repeated, 'repeat_share_of_early': repeated / len(early) if len(early) else np.nan})
    return {'event_recall':pd.DataFrame(event_perf),'composition':pd.DataFrame(burden)}

def boundary_sensitivity(f, splits, episodes, p, bundle):
    scaler = bundle['scaler']
    models = bundle['models']
    selected = bundle['selected']
    vf = f.loc[splits.validation].reset_index(drop=True)
    tf = f.loc[splits.july].reset_index(drop=True)
    ve = episodes.loc[episodes.start.ge('2020-05-01') & episodes.start.lt('2020-07-01')]
    te = episodes.loc[episodes.start.ge('2020-07-01') & episodes.start.lt('2020-08-01')]
    vctx = make_context(vf, ve)
    tctx = make_context(tf, te)
    jp = p.loc[p.period.eq('July')]
    boundary_rows = []
    stream = f.loc[f.cycle_end.ge('2020-05-01')].reset_index(drop=True)
    stream_ctx = make_context(stream, episodes.loc[episodes.start.ge('2020-05-01') & episodes.start.lt('2020-08-01')])
    stream_is_july = stream.cycle_end.ge('2020-07-01').to_numpy()
    july_offset = np.flatnonzero(stream_is_july)[0]
    for row in selected.itertuples():
        with threadpool_limits(limits=1):
            ss = score_model(row.method, models[row.method], scaler.transform(stream[A16].to_numpy(float)))
        all_idx = emit_alerts(ss > row.threshold, stream_ctx)
        carried = all_idx[stream_is_july[all_idx]] - july_offset
        fresh = np.flatnonzero(jp.loc[jp.method.eq(row.method), 'notification'].to_numpy())
        carried_stats = metrics_from_alerts(carried, tctx, ss[stream_is_july] > row.threshold)
        boundary_rows.append({'method': row.method, 'different_notification_rows': len(np.setxor1d(carried, fresh)), 'carried_false_alerts': carried_stats['false_alerts'], 'carried_events_detected': carried_stats['events_detected']})
        mid = len(vf) // 2
        p = score_model(row.method, models[row.method], scaler.transform(vf[A16].to_numpy(float))) > row.threshold
        prefix_ctx = make_context(vf.iloc[:mid], ve)
        assert np.array_equal(emit_alerts(p[:mid], prefix_ctx), emit_alerts(p, vctx)[emit_alerts(p, vctx) < mid])
    boundary = pd.DataFrame(boundary_rows)
    return boundary


from paths import repository_root
OUTPUT_FILES = {'figure07': 'figures/그림07_사건별_최초경보_선행시간.png', 'figure08': 'figures/그림08_일별_발송규칙_적용후_경보.png', 'figure09': 'figures/그림09_LOF_오탐과_정상_신호.png', 'figure10': 'figures/그림10_LOF_구간평균과_학습이웃.png', 'figure11': 'figures/그림11_IF_미탐과_정탐_신호.png', 'figure12': 'figures/그림12_IF_미탐정탐_구간평균.png'}

def output_paths():
    return {key:repository_root()/relative for key,relative in OUTPUT_FILES.items()}
