"""APU staged analysis: functions have no import-time data processing."""
import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from plot_style import apply_style, save_figure
from modeling import output_paths
METHODS=['ZScore','IF','LOF']
NAMES={'ZScore':'Z-score','IF':'IF','LOF':'LOF'}
COLORS={'ZScore':'#315A7D','IF':'#B67922','LOF':'#4F806D'}
COL={'ZScore':'#B67922','IF':'#315A7D','LOF':'#4F806D'}
def plot_model_evaluation(selected, curves, metrics):
    apply_style(160)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), layout='constrained', sharey=True)
    for ax, method in zip(axes, METHODS):
        chosen = selected.loc[selected.method.eq(method)].iloc[0]
        curve = curves[chosen.id]
        ax.scatter(curve.false_alerts, curve.events_detected, s=12, alpha=0.3, color=COLORS[method], rasterized=True)
        ax.scatter([chosen.false_alerts], [chosen.events_detected], s=160, marker='*', color=COLORS[method], edgecolor='#222', zorder=4)
        ax.axhline(7, color='#555', ls='--', lw=1)
        ax.set(xlabel='검증 오탐 발송 수 (건)', title=f'{NAMES[method]} · {chosen.id}\n선정: {chosen.events_detected:.0f}/9건, 오탐 {chosen.false_alerts:.0f}건', ylim=(-0.3, 9.5), yticks=range(10))
        ax.grid(alpha=0.15)
    axes[0].set_ylabel('조기 경보가 발송된 고장 수 (건)')
    save_figure(output_paths()['figure04'], fig)
    july = metrics.loc[metrics.period.eq('July')].set_index('method').loc[METHODS]
    fig, ax = plt.subplots(figsize=(10, 4.8), layout='constrained')
    x = np.arange(3)
    for i, method in enumerate(METHODS):
        vals = july.loc[method, ['precision', 'recall', 'f1']].to_numpy(float)
        bars = ax.bar(x + (i - 1) * 0.24, vals, width=0.23, color=COLORS[method], label=NAMES[method])
        ax.bar_label(bars, labels=[f'{v:.3f}' for v in vals], padding=3, fontsize=10)
    ax.set(xticks=x, xticklabels=['Precision', 'Recall', 'F1'], ylim=(0, 1), ylabel='주기 지표 (0–1)', title=f"동일 M34·A16 조건 · 7월 회고 평가 {int(july.iloc[0][['tn', 'fp', 'fn', 'tp']].sum()):,}주기")
    ax.legend(frameon=False, ncol=3, loc='upper right')
    ax.grid(axis='y', alpha=0.15)
    ax.set_axisbelow(True)
    save_figure(output_paths()['figure05'], fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.4), layout='constrained')
    for ax, method in zip(axes, METHODS):
        r = july.loc[method]
        mat = np.array([[r.tn, r.fp], [r.fn, r.tp]], int)
        ax.imshow(mat, cmap='Blues', vmin=0, vmax=max(1, int(july[['tn', 'fp', 'fn', 'tp']].to_numpy().max())))
        for (i, j), v in np.ndenumerate(mat):
            ax.text(j, i, f'{v:,}', ha='center', va='center', fontsize=15, color='white' if v > july[['tn', 'fp', 'fn', 'tp']].to_numpy().max() / 2 else '#222')
        ax.set(xticks=[0, 1], xticklabels=['비고장', '전조'], yticks=[0, 1], yticklabels=['비고장', '전조'], xlabel='예측', ylabel='실제', title=f'{NAMES[method]}\nF1 {r.f1:.4f}')
    fig.suptitle(f'공통 7월 혼동행렬 · 양성 {int(july.iloc[0].tp + july.iloc[0].fn):,} / 비고장 {int(july.iloc[0].tn + july.iloc[0].fp):,} · FP/FN은 주기 수')
    save_figure(output_paths()['figure06'], fig)

def plot_target_sensitivity(targets):
    apply_style(220)
    t = targets
    fig, ax = plt.subplots(figsize=(8.4, 3.0), layout='constrained')
    for method, marker in [('ZScore', 'o'), ('IF', 's'), ('LOF', '^')]:
        z = t.loc[t.method.eq(method)].sort_values('target')
        ax.plot(z.target, z.false_alerts, marker=marker, color=COL[method], label='Z-score' if method == 'ZScore' else method, lw=1.6)
        for r in z.loc[z.feasible].itertuples():
            ax.annotate(str(int(r.false_alerts)), (r.target, r.false_alerts), xytext=(0, -14 if method == 'IF' and r.target == 7 else 7), textcoords='offset points', ha='center', fontsize=10)
    ax.set_xticks([7, 8, 9])
    ax.set_xlim(6.85, 9.15)
    ax.set_ylim(0, 315)
    ax.set_xlabel('검증 9개 사건 중 요구 탐지 수 (건)')
    ax.set_ylabel('정상 구간 오탐 알림 (건)')
    ax.set_title('5~6월 검증 목표별 최소 오탐 부담', fontsize=12)
    ax.legend(frameon=False, ncols=3, loc='upper left')
    ax.grid(axis='y', alpha=0.15)
    save_figure(output_paths()['figure13'], fig)
