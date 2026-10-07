"""APU staged analysis: functions have no import-time data processing."""
import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from plot_style import apply_style, save_figure
from alarm_analysis import output_paths
METHODS=['ZScore','IF','LOF']
NAMES={'ZScore':'Z-score','IF':'IF','LOF':'LOF'}
COLORS={'ZScore':'#B67922','IF':'#315A7D','LOF':'#4F806D'}
COL=COLORS
def plot_first_alerts(lead):
    apply_style(160)
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.4), layout='constrained', gridspec_kw={'height_ratios': [2, 1.4]})
    for ax, period in zip(axes, ['validation', 'July']):
        d = lead.loc[lead.period.eq(period)]
        ids = list(d.episode_id.drop_duplicates())
        mat = d.pivot(index='method', columns='episode_id', values='lead_hours').reindex(index=METHODS, columns=ids)
        ax.imshow(np.ma.masked_invalid(mat.to_numpy()), vmin=2, vmax=24, cmap='Blues', aspect='auto')
        for i, m in enumerate(METHODS):
            for j, e in enumerate(ids):
                row = d.loc[d.method.eq(m) & d.episode_id.eq(e)].iloc[0]
                label = f'{row.lead_hours:.2f}h' if row.detected else '미탐' if row.observable else '관측 없음'
                ax.text(j, i, label, ha='center', va='center', color='white' if row.detected and row.lead_hours > 16 else '#222', fontsize=11)
        ax.set(yticks=range(3), yticklabels=[NAMES[m] for m in METHODS], xticks=range(len(ids)), xticklabels=[x.replace('episode_', 'E') for x in ids], title=('5~6월 검증' if period == 'validation' else '7월 평가') + ' 사건별 최초 조기 경보 선행시간', xlabel='병합 고장 사건')
    save_figure(output_paths()['figure07'], fig)

def plot_daily_alarms(daily):
    apply_style(160)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5), layout='constrained', sharey=True)
    for ax, period in zip(axes, ['validation', 'July']):
        for i, m in enumerate(METHODS):
            v = daily.loc[daily.period.eq(period) & daily.method.eq(m), 'all_notifications'].to_numpy()
            vals, cnt = np.unique(v, return_counts=True)
            ax.scatter(np.full(len(vals), i), vals, s=cnt * 13, alpha=0.5, color=COLORS[m], edgecolor='#444')
            ax.hlines(v.median() if hasattr(v, 'median') else np.median(v), i - 0.22, i + 0.22, color='#222', lw=2)
        ax.set(xticks=range(3), xticklabels=[NAMES[m] for m in METHODS], ylabel='하루 발송 규칙 적용 후 경보 (건)', title=('검증 61일' if period == 'validation' else '7월 31일') + ' · 원 크기는 일수', ylim=(-0.7, 25))
    save_figure(output_paths()['figure08'], fig)

def plot_case_signals(cases, pred, raw_windows):
    apply_style(220)
    for method, kind, num in [('LOF', 'FP', '09'), ('IF', 'FN', '11')]:
        selected = cases.loc[cases.method.eq(method)]
        if selected.empty:
            fig, ax = plt.subplots(figsize=(8.4, 3.6))
            ax.axis('off')
            ax.text(0.5, 0.5, '조건을 충족하는 오류·대조 주기 쌍 없음', ha='center', va='center')
            save_figure(output_paths()['figure' + num], fig)
            continue
        if method == 'LOF':
            rr = raw_windows['FP', 'error']
            fig, axes = plt.subplots(3, 1, figsize=(8.4, 3.6), sharex=True, layout='constrained')
            for ax, col, label in zip(axes[:2], ['TP3', 'Motor_current'], ['압력 (bar)', '전류 (A)']):
                ax.plot(rr.timestamp, rr[col], color='#536C7E', lw=0.9)
                ax.set_ylabel(label)
            q = pred.loc[pred.method.eq(method) & pred.cycle_end.between(rr.timestamp.min(), rr.timestamp.max())]
            axes[2].plot(q.cycle_end, q.score, 'o-', color=COL[method], ms=3, lw=0.9)
            axes[2].axhline(selected.threshold.iloc[0], ls='--', color='#444444', lw=1, label='고정 임곗값')
            axes[2].set_ylabel('LOF 이상 점수')
            for _, r in selected.iterrows():
                color = '#B67922' if r.role == 'error' else '#315A7D'
                lab = '오탐 FP' if r.role == 'error' else '정상 판정 TN'
                for ax in axes:
                    ax.axvspan(r.cycle_start, r.cycle_end, color=color, alpha=0.15)
                    ax.axvline(r.cycle_end, color=color, ls=':', lw=1)
                axes[0].plot([], [], color=color, lw=5, alpha=0.6, label=lab)
            axes[0].legend(ncols=2, frameon=False, loc='upper right', fontsize=9)
            error = selected.loc[selected.role.eq('error')].iloc[0]
            control = selected.loc[selected.role.eq('control')].iloc[0]
            gap = (control.cycle_end - error.cycle_end).total_seconds() / 60
            axes[0].set_title(f'{error.cycle_end:%m월 %d일} LOF 오탐과 {gap:+.1f}분 정상 판정', fontsize=12)
            axes[2].legend(frameon=False, fontsize=9)
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            axes[-1].set_xlabel(f'센서 관측 / 완전 주기 종료 시각 ({error.cycle_end:%Y-%m-%d})')
        else:
            fig, axes = plt.subplots(2, 2, figsize=(8.4, 3.4), layout='constrained')
            for j, (_, r) in enumerate(selected.iterrows()):
                rr = raw_windows['FN', r.role]
                color = '#B67922' if r.role == 'error' else '#315A7D'
                for i, (col, label) in enumerate([('TP3', '압력 (bar)'), ('Motor_current', '전류 (A)')]):
                    ax = axes[i, j]
                    ax.plot(rr.timestamp, rr[col], color='#536C7E', lw=0.9)
                    ax.axvspan(r.cycle_start, r.cycle_end, color=color, alpha=0.2)
                    ax.axvline(r.cycle_end, color=color, ls=':', lw=1)
                    ax.set_ylabel(label)
                    ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    ax.set_xlabel(f'{r.cycle_end:%m월 %d일} 센서 시각')
                axes[0, j].set_title(('미탐 FN' if r.role == 'error' else '정탐 TP') + ' · 종료 ' + r.cycle_end.strftime('%H:%M:%S'), fontsize=11)
            error = selected.loc[selected.role.eq('error')].iloc[0]
            control = selected.loc[selected.role.eq('control')].iloc[0]
            gap = abs((control.cycle_end - error.cycle_end).total_seconds()) / 3600
            fig.suptitle(f"{error.next_episode_id_eval.replace('episode_', 'E')}의 유사 조건 비교 · 시점 차이 {gap:.2f}시간", fontsize=12)
        save_figure(output_paths()['figure' + num], fig)

def plot_case_profiles(cases, feat, neighbors):
    apply_style(220)
    trace = []
    for method, num in [('LOF', '10'), ('IF', '12')]:
        fig, axes = plt.subplots(1, 2, figsize=(8.4, 2.65), layout='constrained')
        fig.suptitle('LOF 오탐·정상과 학습 이웃의 구간 평균' if method == 'LOF' else 'IF 미탐·정탐의 구간 평균', fontsize=12)
        for ax, s, label in zip(axes, ['TP3', 'MC'], ['구간 평균 압력 (bar)', '구간 평균 전류 (A)']):
            cols = [f'{s}_mean_B{i}' for i in range(1, 8)]
            if method == 'LOF' and (not neighbors.empty):
                ids = neighbors.loc[neighbors.role.eq('error'), 'train_cycle']
                z = feat.loc[feat.cycle_id.isin(ids), cols]
                assert len(z) == len(set(ids))
                ax.fill_between(range(1, 8), z.quantile(0.25).to_numpy(), z.quantile(0.75).to_numpy(), color='#828B92', alpha=0.2, label='FP 학습 이웃 25~75%')
                ax.plot(range(1, 8), z.median().to_numpy(), color='#4E5961', ls='--', lw=1, label='FP 학습 이웃 중앙값')
            for _, r in cases.loc[cases.method.eq(method)].iterrows():
                labelcase = ('오탐 FP' if method == 'LOF' else '미탐 FN') if r.role == 'error' else '정상 TN' if method == 'LOF' else '정탐 TP'
                ax.plot(range(1, 8), r[cols].to_numpy(float), 'o-', ms=3, lw=1.1, color='#B67922' if r.role == 'error' else '#315A7D', label=labelcase)
                for col, v in zip(cols, r[cols]):
                    trace.append({'method': method, 'role': r.role, 'feature': col, 'value': v})
            ax.set_xticks(range(1, 8), [f'B{i}' for i in range(1, 8)])
            ax.axvline(2.5, color='#AAAAAA', ls=':', lw=1)
            ax.set_ylabel(label)
            ax.set_xlabel('가동 B1~B2 / 대기 B3~B7')
            ax.grid(axis='y', alpha=0.12)
        axes[1].legend(frameon=False, fontsize=8.5, loc='upper right')
        save_figure(output_paths()['figure' + num], fig)
    return pd.DataFrame(trace)
