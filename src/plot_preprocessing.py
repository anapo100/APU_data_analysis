from pathlib import Path
import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch


def style():
    font=Path('C:/Windows/Fonts/malgun.ttf')
    if font.exists():font_manager.fontManager.addfont(str(font));family=font_manager.FontProperties(fname=str(font)).get_name()
    else:
        available={f.name for f in font_manager.fontManager.ttflist}
        family=next((x for x in ['Malgun Gothic','Noto Sans CJK KR','NanumGothic','AppleGothic'] if x in available),None)
        if family is None:raise RuntimeError('A Korean font is required: Malgun Gothic or Noto Sans CJK KR.')
    plt.rcParams.update({'font.family':family,'font.size':10.5,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})

def plot_flow(flow):
    counts=flow.set_index('stage')
    fig,ax=plt.subplots(figsize=(10,5.8));ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis('off')
    ax.text(5,5.83,'원자료에서 학습·검증·평가 주기까지',ha='center',weight='bold',fontsize=13)
    def box(x,y,w,h,text):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.06',facecolor='#F0F4F7',edgecolor='#A7B5BF',linewidth=.8))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=10.5)
    raw=counts.loc['raw_sensor_rows'];valid=counts.loc['source_valid_rows'];runs=counts.loc['COMP_run_segments'];scope=counts.loc['complete_cycles_Feb_July']
    box(.1,4.35,2.2,.95,f"센서 관측\n{int(raw['before']):,}행")
    box(2.7,4.35,2.15,.95,f"가동 시작 후보\n{int(runs['before']):,}구간")
    box(5.25,4.35,2.1,.95,f"완전 주기\n{int(runs['remaining']):,}개")
    box(7.8,4.35,2.05,.95,f"2~7월 완전 주기\n{int(scope['remaining']):,}개")
    for a,b in [(2.3,2.7),(4.85,5.25),(7.35,7.8)]:ax.annotate('',xy=(b,4.82),xytext=(a,4.82),arrowprops={'arrowstyle':'->','color':'#334B5A'})
    ax.text(1.18,4.05,f"중복·무효 제외 {int(raw['excluded']+valid['excluded']):,}행",ha='center',fontsize=9.5)
    ax.text(5.95,4.05,f"불완전 {int(runs['excluded']):,}구간 제외",ha='center',fontsize=9.5)
    ax.text(8.83,4.05,f"범위 밖 {int(scope['excluded']):,}개 제외",ha='center',fontsize=9.5)
    ax.text(5,3.65,'이후 분할은 주기 수 기준 · 각 행의 기간·제외 이유가 다름',ha='center',fontsize=10)
    for y,(key,title) in zip([2.55,1.4,.25],[('training','3~4월 학습'),('validation','5~6월 검증'),('July','7월 평가')]):
        m=counts.loc[key+'_mature'];last=counts.loc[key+('_normal_guard' if key=='training' else '_metric_eligible')]
        ax.text(.15,y+.45,title,va='center',weight='bold',fontsize=11)
        middle='성숙 학습 후보' if key=='training' else '기간·시점 조건'
        end='정상 후보 학습' if key=='training' else '주기 지표 대상'
        for x,value,sub in [(2.1,m['before'],'기간 내 완전 주기'),(4.75,m['remaining'],middle),(7.65,last['remaining'],end)]:box(x,y,2,.76,f'{int(value):,}개\n{sub}')
        for a,b in [(4.1,4.75),(7,7.65)]:ax.annotate('',xy=(b,y+.45),xytext=(a,y+.45),arrowprops={'arrowstyle':'->','color':'#334B5A'})
        note=f"말단 24시간 {int(m['excluded']):,}개 제외" if key!='July' else '기간 내 완전 주기 유지'
        ax.text(5.76,y-.10,note,ha='center',va='top',fontsize=9)
        note=('정상 후보 조건' if key=='training' else '지표 제외')+f" {int(last['excluded']):,}개"+(" 제외" if key=='training' else '')
        ax.text(8.63,y-.10,note,ha='center',va='top',fontsize=9)
    return fig

def plot_example(source,train):
    example=train.assign(distance=(train.cycle_seconds-train.cycle_seconds.median()).abs()).sort_values(['distance','cycle_end']).iloc[0]
    a,m,b=example.cycle_start,example.idle_start,example.cycle_end
    part=source.loc[source.timestamp.ge(a)&source.timestamp.lt(b)]
    boundaries=list(pd.date_range(a,m,periods=3))+list(pd.date_range(m,b,periods=6))[1:]
    bin_rows=[]
    for i,(left,right) in enumerate(zip(boundaries[:-1],boundaries[1:]),1):
        q=part.loc[part.timestamp.ge(left)&part.timestamp.lt(right)]
        for col,prefix in [('TP3','TP3'),('Motor_current','MC')]:
            avg=q[col].mean();weighted=avg*example.cycle_seconds
            assert np.isclose(weighted,example[f'{prefix}_B{i}'])
            bin_rows.append({'bin':f'B{i}','sensor':col,'samples':len(q),'sample_mean':avg,'whole_cycle_seconds':example.cycle_seconds,'A16_value':weighted})
    fig,axes=plt.subplots(3,1,figsize=(13,8),sharex=True,layout='constrained')
    for ax,col,unit,color in zip(axes,['TP3','Motor_current','COMP'],['TP3 압력 (bar)','모터 전류 (A)','COMP 상태'],['#315A7D','#B67922','#555']):
        d=source.loc[source.timestamp.between(a,b)]
        ax.step(d.timestamp,d[col],where='post',color=color,lw=1)
        for i,(left,right) in enumerate(zip(boundaries[:-1],boundaries[1:]),1):
            ax.axvspan(left,right,color='#315A7D' if i<=2 else '#B67922',alpha=.06 if i%2 else .12)
            ax.axvline(left,color='#999',lw=.6)
            if ax is axes[0]:ax.text(left+(right-left)/2,1.01,f'B{i}',transform=ax.get_xaxis_transform(),ha='center',fontsize=10)
        ax.axvline(b,color='#444',ls='--',label='특징 사용 가능: 주기 종료')
        ax.set_ylabel(unit);ax.grid(alpha=.12)
    axes[0].set_title(f'실제 완전 주기 {example.cycle_id} · 가동 2구간 + 휴지 5구간',pad=24)
    axes[2].set(yticks=[0,1],yticklabels=['0: 가동','1: 휴지'],xlabel='원시 관측 시각');loc=mdates.AutoDateLocator(minticks=3,maxticks=7);axes[2].xaxis.set_major_locator(loc);axes[2].xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    axes[0].legend(loc='lower left',frameon=False)
    fig.suptitle(f'A16 = 구간 평균 14개 × 전체 주기 {example.cycle_seconds:.0f}초 + 가동/휴지 시간 2개',fontsize=13)
    return fig, pd.DataFrame(bin_rows)

def create_figures(source,train,flow,paths):
    style()
    example_fig,example_values = plot_example(source,train)
    figures = [('figure01',plot_flow(flow)),('figure02',example_fig)]
    for key,fig in figures:
        fig.savefig(paths[key],bbox_inches='tight',facecolor='white')
        plt.close(fig)
    return example_values
