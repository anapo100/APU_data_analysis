import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from plot_style import apply_style, save_figure
from time_series import output_paths
METHODS=['ZScore','IF','LOF']
NAMES={'ZScore':'Z-score','IF':'IF','LOF':'LOF'}
def plot_daily_patterns(daily, episodes, cycles):
    apply_style(220)
    observed = episodes.loc[episodes.episode_id.isin(cycles.loc[cycles.category.eq('early') & cycles.cycle_end.ge('2020-07-01'), 'next_episode_id_eval'])]
    d = daily
    fig, axes = plt.subplots(3, 1, figsize=(8.4, 4.7), sharex=True, layout='constrained')
    start = pd.Timestamp('2020-03-01')
    end = pd.Timestamp('2020-07-31')
    index = pd.date_range(start, end)
    for ax, col, label in zip(axes, ['pressure_cycle_mean', 'current_cycle_mean', 'cycle_minutes'], ['주기 평균 압력 (bar)', '주기 평균 전류 (A)', '전체 주기 길이 (분)']):
        z = d.loc[d.feature.eq(col)].set_index('date').reindex(index)
        ax.fill_between(z.index, z.q25, z.q75, color='#315A7D', alpha=0.18, label='관측 주기의 25~75%')
        ax.plot(z.index, z['median'], color='#315A7D', lw=1.15, label='일별 중앙값')
        for ep in observed.itertuples():
            ax.axvspan(ep.start - pd.Timedelta(hours=24), ep.start - pd.Timedelta(hours=2), color='#B67922', alpha=0.17)
        ax.set_ylabel(label)
        ax.grid(axis='y', alpha=0.15)
    axes[0].set_title('2020년 3~7월 완전 주기의 일별 수준과 변화 폭', fontsize=12)
    axes[0].legend(loc='upper left', ncols=2, frameon=False, fontsize=9)
    axes[-1].set_xlim(start, end)
    axes[-1].set_xticks([start, pd.Timestamp('2020-04-01'), pd.Timestamp('2020-05-01'), pd.Timestamp('2020-06-01'), pd.Timestamp('2020-07-01'), end])
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    axes[-1].set_xlabel('주기 종료일 (2020년)')
    save_figure(output_paths()['figure03'], fig)
