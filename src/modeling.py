"""APU staged analysis: functions have no import-time data processing."""
import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from threadpoolctl import threadpool_limits
from features import A16
from evaluation import make_context, emit_alerts, reference_alerts, metrics_from_alerts, curve_for_scores
from paths import repository_root
METHODS=['ZScore','IF','LOF']
SEED=42

def point_curve(curve,scores,ctx):
    y=ctx['y'][ctx['eligible']];s=np.asarray(scores)[ctx['eligible']]
    order=np.argsort(s,kind='stable');s=s[order];y=y[order]
    k=np.searchsorted(s,curve.threshold.to_numpy(),side='right');cum=np.r_[0,np.cumsum(y)]
    tp=y.sum()-cum[k];fp=len(y)-k-tp;fn=y.sum()-tp;tn=(1-y).sum()-fp
    pr=np.divide(tp,tp+fp,out=np.zeros(len(tp),float),where=tp+fp>0)
    rc=tp/y.sum();f1=np.divide(2*tp,2*tp+fp+fn,out=np.zeros(len(tp),float),where=2*tp+fp+fn>0)
    return curve.assign(tn=tn,fp=fp,fn=fn,tp=tp,precision=pr,recall=rc,f1=f1)

def choose(curve):
    feasible=curve.events_detected.ge(7);c=curve.loc[feasible].copy()
    ok=len(c)>0
    if not ok:c=curve.loc[curve.events_detected.eq(curve.events_detected.max())].copy()
    c['_lead']=c.median_lead_hours.fillna(-np.inf)
    row=c.sort_values(['false_alerts','events_detected','_lead','threshold'],ascending=[True,False,False,False]).iloc[0].drop('_lead').to_dict()
    return {'feasible':ok,**row}

def score_model(method,model,x):
    return np.abs(x).max(axis=1) if method=='ZScore' else -model.score_samples(x)

def verify_metrics(scores,threshold,ctx):
    pred=scores>threshold;idx=emit_alerts(pred,ctx)
    assert np.array_equal(idx,reference_alerts(pred,ctx))
    m=metrics_from_alerts(idx,ctx,pred);eligible=ctx['eligible']
    tn,fp,fn,tp=confusion_matrix(ctx['y'][eligible],pred[eligible],labels=[0,1]).ravel()
    pr,rc,f1,_=precision_recall_fscore_support(ctx['y'][eligible],pred[eligible],average='binary',zero_division=0)
    for key,value in dict(tn=tn,fp=fp,fn=fn,tp=tp,precision=pr,recall=rc,f1=f1).items():assert np.isclose(m[key],value),(key,m[key],value)
    assert (ctx['frame'].iloc[idx].cycle_end>=ctx['frame'].iloc[idx].cycle_end).all()
    return m,pred,idx

def fit_model_grid(train, vf, ve):
    scaler = StandardScaler().fit(train[A16].to_numpy(float))
    assert scaler.n_samples_seen_ == len(train)
    assert np.allclose(scaler.mean_, train[A16].mean().to_numpy())
    Xtrain = scaler.transform(train[A16].to_numpy(float))
    Xval = scaler.transform(vf[A16].to_numpy(float))
    assert np.isfinite(Xtrain).all() and np.isfinite(Xval).all()
    vctx = make_context(vf, ve)
    specs = [{'id': 'ZScore', 'method': 'ZScore', 'k': 0}, {'id': 'IF', 'method': 'IF', 'k': 0}] + [{'id': f'LOF_k{k}', 'method': 'LOF', 'k': k} for k in [10, 20, 35, 50, 100]]
    models = {}
    curves = {}
    val_scores = {}
    rows = []
    for spec in specs:
        with threadpool_limits(limits=1):
            if spec['method'] == 'IF':
                model = IsolationForest(n_estimators=300, max_samples=256, contamination='auto', random_state=SEED, n_jobs=1).fit(Xtrain)
            elif spec['method'] == 'LOF':
                model = LocalOutlierFactor(n_neighbors=spec['k'], novelty=True, contamination='auto', metric='minkowski', p=2, n_jobs=1).fit(Xtrain)
            else:
                model = None
            scores = score_model(spec['method'], model, Xval)
        assert np.isfinite(scores).all()
        curve = point_curve(curve_for_scores(scores, vctx, candidate_scope='all'), scores, vctx)
        chosen = choose(curve)
        measured, _, _ = verify_metrics(scores, chosen['threshold'], vctx)
        for key, value in measured.items():
            assert np.isclose(value, chosen[key], equal_nan=True), (spec['id'], key)
        models[spec['id']] = model
        curves[spec['id']] = curve
        val_scores[spec['id']] = scores
        rows.append({**spec, **chosen})
    candidates = pd.DataFrame(rows)
    selected_rows = []
    for method in METHODS:
        d = candidates.loc[candidates.method.eq(method)].copy()
        good = d.loc[d.feasible]
        d = good if len(good) else d.loc[d.events_detected.eq(d.events_detected.max())]
        d['_lead'] = d.median_lead_hours.fillna(-np.inf)
        selected_rows.append(d.sort_values(['false_alerts', 'events_detected', '_lead', 'k'], ascending=[True, False, False, True]).iloc[0].drop('_lead').to_dict())
    selected = pd.DataFrame(selected_rows)
    return {'scaler':scaler,'models':models,'curves':curves,'val_scores':val_scores,'candidates':candidates,'selected':selected,'Xtrain':Xtrain,'Xval':Xval,'vctx':vctx}

def evaluate_selected(fit, vf, tf, ve, te):
    scaler = fit['scaler']
    models = fit['models']
    val_scores = fit['val_scores']
    selected = fit['selected']
    locked = selected.copy(deep=True)
    vctx = make_context(vf, ve)
    tctx = make_context(tf, te)
    Xtest = scaler.transform(tf[A16].to_numpy(float))
    predictions = []
    metric_rows = []
    event_rows = []
    for period, frame, ctx in [('validation', vf, vctx), ('July', tf, tctx)]:
        for row in selected.itertuples():
            with threadpool_limits(limits=1):
                scores = val_scores[row.id] if period == 'validation' else score_model(row.method, models[row.id], Xtest)
            stats, pred, idx = verify_metrics(scores, row.threshold, ctx)
            metric_rows.append({'period': period, 'method': row.method, 'config': row.id, 'threshold': row.threshold, 'validation_feasible': row.feasible, **stats})
            points = frame[['cycle_id', 'cycle_start', 'cycle_end', 'raw_block', 'segment', 'category', 'eligible', 'y', 'next_episode_id_eval', 'lead_eval', 'cycle_seconds']].copy()
            points['period'] = period
            points['method'] = row.method
            points['score'] = scores
            points['threshold'] = row.threshold
            points['prediction'] = pred
            points['notification'] = False
            points.loc[idx, 'notification'] = True
            points['score_available_at'] = points.cycle_end
            assert np.array_equal(points.loc[points.notification, 'cycle_end'], points.loc[points.notification, 'score_available_at'])
            predictions.append(points)
            for ep in ctx['events'].itertuples():
                early = points.category.eq('early') & points.next_episode_id_eval.eq(ep.episode_id)
                hits = points.loc[early & points.notification]
                event_rows.append({'period': period, 'method': row.method, 'episode_id': ep.episode_id, 'start': ep.start, 'early_cycles': int(early.sum()), 'observable': bool(early.any()), 'detected': bool(len(hits)), 'first_alert': hits.cycle_end.min() if len(hits) else pd.NaT, 'lead_hours': hits.lead_eval.iloc[0] if len(hits) else np.nan})
    predictions = pd.concat(predictions, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)
    event_results = pd.DataFrame(event_rows)
    pd.testing.assert_frame_equal(locked, selected)
    for period, d in predictions.groupby('period'):
        ids = [d.loc[d.method.eq(m), 'cycle_id'].tolist() for m in METHODS]
        assert ids[0] == ids[1] == ids[2]
    return {'predictions':predictions,'metrics':metrics,'events':event_results}

def target_sensitivity(fit):
    curves = fit['curves']
    models = fit['models']
    saved_choice = fit['selected']
    Xval = fit['Xval']
    vctx = fit['vctx']
    targets = []
    fixed = []
    candidate_rows = []
    for target in [7, 8, 9]:
        for spec, curve in curves.items():
            q = curve.loc[curve.events_detected.ge(target)].copy()
            method = 'LOF' if spec.startswith('LOF') else spec
            k = int(spec.split('k')[1]) if method == 'LOF' else 0
            if len(q):
                q['_lead'] = q.median_lead_hours.fillna(-np.inf)
                best = q.sort_values(['false_alerts', 'events_detected', '_lead', 'threshold'], ascending=[True, False, False, False]).iloc[0].drop('_lead').to_dict()
                candidate_rows.append({'target': target, 'method': method, 'spec': spec, 'k': k, 'feasible': True, **best})
            else:
                candidate_rows.append({'target': target, 'method': method, 'spec': spec, 'k': k, 'feasible': False, 'max_detected': curve.events_detected.max()})
        cc = pd.DataFrame([x for x in candidate_rows if x['target'] == target])
        for method in ['ZScore', 'IF', 'LOF']:
            d = cc.loc[cc.method.eq(method) & cc.feasible].copy()
            if len(d):
                d['_lead'] = d.median_lead_hours.fillna(-np.inf)
                targets.append(d.sort_values(['false_alerts', 'events_detected', '_lead', 'k'], ascending=[True, False, False, True]).iloc[0].drop('_lead').to_dict())
            else:
                targets.append({'target': target, 'method': method, 'feasible': False})
        fixed.append(next((x for x in candidate_rows if x['target'] == target and x['spec'] == 'LOF_k20')))
    target_df = pd.DataFrame(targets)
    for r in target_df.loc[target_df.target.eq(7)].itertuples():
        s = saved_choice.loc[saved_choice.method.eq(r.method)].iloc[0]
        assert r.threshold == s.threshold and r.false_alerts == s.false_alerts and (r.spec == s.id)
    replays = []
    for r in target_df.itertuples():
        if not r.feasible:
            continue
        with threadpool_limits(limits=1):
            model = models[r.spec]
            scores = np.abs(Xval).max(axis=1) if r.method == 'ZScore' else -model.score_samples(Xval)
        flags = scores > r.threshold
        indices = reference_alerts(flags, vctx)
        m = metrics_from_alerts(indices, vctx, flags)
        for key in ['events_detected', 'false_alerts', 'all_alerts', 'median_lead_hours']:
            assert np.isclose(m[key], getattr(r, key), rtol=0, atol=1e-10), (r.method, r.target, key, m[key], getattr(r, key))
        replays.append({'target': r.target, 'method': r.method, 'independent_replay_matches': True, **m})
    return {'targets':target_df,'candidates':pd.DataFrame(candidate_rows),'fixed_lof20':pd.DataFrame(fixed),'replays':pd.DataFrame(replays)}


def persist_model_outputs(fit, evaluation):
    # Stage 05 needs the fitted trees and LOF neighborhoods, so keep one bundle.
    selected=fit['selected'].copy(deep=True)
    bundle={'scaler':fit['scaler'],'features':list(A16),'selected':selected,
            'models':{r.method:fit['models'][r.id] for r in selected.itertuples()},'seed':SEED}
    evaluation['predictions'][PREDICTION_COLUMNS].to_csv(output_paths()['predictions'],index=False,encoding='utf-8-sig')
    joblib.dump(bundle,output_paths()['model_bundle'],compress=3)
    return bundle

def load_model_bundle():
    bundle=joblib.load(output_paths()['model_bundle'])
    assert bundle['features']==A16 and bundle['seed']==SEED
    return bundle


OUTPUT_FILES = {
    'predictions':'data/APU_predictions.csv',
    'model_bundle':'data/APU_fitted_models.joblib',
    'figure04':'figures/그림04_검증_임곗값과_탐지오탐.png',
    'figure05':'figures/그림05_7월_Precision_Recall_F1.png',
    'figure06':'figures/그림06_7월_혼동행렬.png',
    'figure13':'figures/그림13_검증_탐지목표별_최소오탐.png',
}
PREDICTION_COLUMNS = ['cycle_id','period','method','score','threshold','prediction','notification']

def output_paths():
    return {key:repository_root()/relative for key,relative in OUTPUT_FILES.items()}

def load_predictions(frame):
    predictions=pd.read_csv(output_paths()['predictions'],float_precision='round_trip')
    assert set(predictions.columns)==set(PREDICTION_COLUMNS)
    columns=['cycle_id','cycle_start','cycle_end','raw_block','segment','category','eligible','y','next_episode_id_eval','lead_eval','cycle_seconds']
    joined=predictions.merge(frame[columns],on='cycle_id',how='left',validate='many_to_one')
    assert joined.cycle_end.notna().all()
    joined['score_available_at']=joined.cycle_end
    assert not joined.duplicated(['period','method','cycle_id']).any()
    return joined
