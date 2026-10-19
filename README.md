# 철도 공기생산장치(APU) 고장 전조 탐지

포스코 K-뉴딜 아카데미 통합 프로젝트 · 4조

철도 차량에 압축공기를 공급하는 공기생산장치(APU, Air Production Unit)의 압력·전류 기록을 분석했다. 가동·대기 주기를 기준으로 Z-score·Isolation Forest(IF)·Local Outlier Factor(LOF)의 탐지 성능과 경보 횟수를 비교했다.

[APU 고장 전조 탐지 대시보드](https://apu-early-warning-dashboard.anapo123.chatgpt.site) · 과거 데이터 탐색 및 경보 재생

[결과보고서](report/4조_결과보고서_261013.pdf) · [문제정의서](report/문제정의서.pdf) · [발표 자료](report/presentation/index.html) · [센서 변수 설명](data/COLUMN.md)

## 분석 결과

검증 고장 9건 중 최소 7건을 조기에 탐지하는 설정에서 정상 구간의 오탐 경보를 비교했다. A16 특징과 1시간 발송 제한을 공통 적용한 결과, 오탐 경보가 가장 적은 IF를 점검 후보 모델로 선정했다.

### 5~6월 검증: 모델별 설정 선택

| 모델 | 선택 임곗값¹ | 조기 탐지 사건 | 정상 구간 오탐 경보 |
|---|---:|---:|---:|
| Z-score | 1.447497 | 7/9건 | 164건 |
| IF | 0.535155 | 7/9건 | 36건 |
| LOF · 이웃 수 20 | 2.015209 | 7/9건 | 57건 |

¹ 임곗값은 소수점 여섯 자리로 표시했다. 코드에는 반올림 전 값을 적용한다. 탐지한 사건의 구성은 모델마다 다르다.

### 7월 평가: 검증에서 정한 설정을 고정

| 모델 | 주기 Precision | 주기 Recall | 주기 F1 | 조기 탐지 사건 | 정상 구간 오탐 경보 | 전체 경보 |
|---|---:|---:|---:|---:|---:|---:|
| Z-score | 38.50% | 79.12% | 0.5180 | 2/3건 | 134건 | 174건 |
| IF | 69.41% | 64.84% | 0.6705 | 2/3건 | 35건 | 61건 |
| LOF | 0.00% | 0.00% | 0.0000 | 0/3건 | 29건 | 35건 |

주기 지표는 정상 1,663개와 전조 182개, 총 1,845주기를 대상으로 계산했다. Precision은 이상 판정 중 전조의 비율, Recall은 전조 중 이상 판정의 비율, F1은 두 값의 조화평균이다. 경보 수는 1시간 발송 제한 적용 후 집계했다. 전체 경보에는 고장 직전·진행·회복·라벨 미확인 구간도 포함한다.

Z-score와 IF는 E15·E16을 탐지했다. 첫 경보는 Z-score가 각각 2.14시간, 6.95시간 빨랐고, 전체 경보는 IF가 적었다. E14는 전조 주기가 관측되지 않았다. LOF는 관측 가능한 두 사건 모두 미탐이었다.

상세 결과: [04 모델 학습·검증·평가](notebooks/04_모델학습_검증_평가.ipynb), [05 경보·오탐미탐 평가](notebooks/05_경보_오탐미탐_평가.ipynb), [결과보고서](report/4조_결과보고서_261013.pdf).

## 분석 방법

```text
원본 센서 + 전문가 고장 기록
  → 데이터 품질·관측 공백 확인
  → 완전한 가동·대기 주기 추출
  → A16 특징 생성 및 고장 라벨 연결
  → 3~4월 정상 후보로 표준화·학습
  → 5~6월에서 임곗값·LOF 이웃 수 선택
  → 고정 설정으로 7월 평가
  → 사건별 첫 경보·반복 부담·오탐과 미탐 사례 분석
```

### 1. 완전 주기와 A16 특징

`COMP=0`인 가동 시작부터 대기(`COMP=1`)를 거쳐 다음 가동 시작까지가 한 주기다. 센서 기록에 30초 초과 공백이 있으면 관측 구간을 분리한다. 시작·종료가 확인되고 모든 세부 구간에 관측값이 있는 완전 주기만 사용한다. 판정 시점은 주기 종료 시각이다.

가동은 같은 길이의 2구간, 대기는 같은 길이의 5구간으로 나눠 총 7구간으로 구성한다.

| A16 구성 | 개수 | 계산 방법 |
|---|---:|---|
| `TP3_B1`~`TP3_B7` | 7 | 각 구간의 압력 표본 평균 × 전체 주기 길이(초) |
| `MC_B1`~`MC_B7` | 7 | 각 구간의 모터 전류 표본 평균 × 전체 주기 길이(초) |
| `Trun_seconds`, `Tidle_seconds` | 2 | 가동 시간, 대기 시간(초) |

16개 특징은 센서 수준과 주기 길이를 함께 반영한다. 시계열·오류 분석에서는 구간별 센서 평균·주기 길이·가동 비율을 따로 비교한다. 특징 계산: [features.py](src/features.py) · 주기 선택: [preprocess.py](src/preprocess.py).

### 2. 정상 후보와 기간 분할

고장 기록 21구간의 중첩·인접 구간을 병합해 16개 사건으로 정리했다. 주기 종료 이후 가장 가까운 고장 시작까지 2시간 이상 24시간 이하가 남은 주기를 전조로 분류한다.

학습용 정상 후보는 주기 전체가 고장 시작 24시간 전부터 고장 종료 후 2시간까지의 범위 밖에 있는 자료다. 정상 후보에서만 평균과 표준편차를 계산해 표준화(StandardScaler)하고 모델을 학습한다.

| 기간 · 2020년 | 용도 | 사용 규모 |
|---|---|---|
| 3~4월 | 정상 후보로 표준화·모델 학습 | 2,314주기 |
| 5~6월 | 임곗값과 LOF 이웃 수 선택 | 점수 계산 2,754주기 · 주기 지표 2,648주기 · 고장 9건 |
| 7월 | 선택한 설정을 고정해 평가 | 점수 계산 1,948주기 · 주기 지표 1,845주기 · 고장 3건 |

해당 기간 안에서 이후 고장 여부를 확인할 수 있도록 학습·검증의 마지막 24시간을 제외한다. 주기 지표에서는 고장 직전 2시간 미만, 고장 진행·중첩, 종료 후 2시간의 회복, 이후 24시간의 라벨 미확인 구간을 제외한다. 라벨·기간 선택 규칙: [labels.py](src/labels.py).

### 3. 모델 비교와 경보 규칙

| 방법 | 이상을 판단하는 방식 | 코드의 주요 설정 |
|---|---|---|
| Z-score | 정상 후보의 평균에서 얼마나 멀리 벗어났는지 확인 | 표준화한 A16 절댓값 중 최댓값 |
| IF | 무작위로 자료를 나눌 때 쉽게 따로 분리되는 주기 탐지 | 트리 300개 · 트리별 학습 표본 256개 · 난수값 42 |
| LOF | 가까운 학습 주기들과 비교해 주변 자료가 드문 주기 탐지 | 이웃 수 10·20·35·50·100 비교 · 새 자료 판정용 `novelty=True` |

이상점수가 임곗값을 초과하면 경보 후보로 분류한다. 시간순으로 처리하며 마지막 발송 후 1시간 동안 추가 경보를 제한한다. 센서 기록이 끊겨 새 관측 구간이 시작되거나 평가를 시작하면 대기시간을 초기화한다. 발송 여부는 과거 데이터에 이 규칙을 적용해 계산했다.

고장 2~24시간 전에 경보가 한 번 이상 있으면 해당 사건을 탐지한 것으로 집계한다. 검증 9건 중 최소 7건을 탐지하는 후보에서 정상 구간 오탐 경보가 가장 적은 설정을 선택한다. 동률이면 탐지 사건 수와 첫 경보 선행시간의 중앙값을 비교한다. 세부 선택·평가 규칙: [modeling.py](src/modeling.py), [evaluation.py](src/evaluation.py).

## 저장소 구성

```text
APU_data_analysis/
├── README.md
├── data/
│   ├── README.md                     # 입력 데이터 출처
│   └── COLUMN.md                     # 센서 변수 설명
├── notebooks/
│   ├── 01_데이터확인.ipynb
│   ├── 02_주기전처리_특징생성.ipynb
│   ├── 03_시계열분석.ipynb
│   ├── 04_모델학습_검증_평가.ipynb
│   └── 05_경보_오탐미탐_평가.ipynb
├── src/
│   ├── paths.py                      # 저장소 기준 경로
│   ├── data_checks.py                # 입력 자료와 관측 품질 확인
│   ├── preprocess.py                 # 완전 주기 추출·분할 저장
│   ├── features.py                   # A16 계산
│   ├── labels.py                     # 사건 병합·라벨·기간 선택
│   ├── time_series.py                # 주기별 신호 통계
│   ├── modeling.py                   # 모델 학습·설정 선택·결과 저장
│   ├── evaluation.py                 # 발송 규칙과 성능 지표
│   ├── alarm_analysis.py             # 사건별·일별 경보 부담
│   ├── case_analysis.py              # 오탐·미탐 사례 해석
│   ├── plot_preprocessing.py
│   ├── plot_time_series.py
│   ├── plot_models.py
│   ├── plot_alarms.py
│   └── plot_style.py
├── figures/                          # 분석 그림 01~13
└── report/
    ├── 문제정의서.docx
    ├── 문제정의서.pdf
    ├── 4조_결과보고서_261013.docx
    ├── 4조_결과보고서_261013.pdf
    └── presentation/                 # HTML 발표 자료
        ├── index.html
        ├── app.js
        ├── styles.css
        ├── assets/
        └── fonts/
```

입력 CSV와 실행 중 생성되는 파생 CSV·학습 모델은 로컬 `data/`에 저장한다.

## 실행 방법

### 1. Python 환경 준비

Python 3와 Jupyter를 사용한다. 노트북 메타데이터에 기록된 Python 버전은 3.14.6이다. `src/`와 노트북에서 사용하는 패키지를 설치한 뒤 프로젝트 폴더 `APU_data_analysis/`에서 JupyterLab을 실행한다.

```powershell
python -m pip install numpy pandas scipy scikit-learn matplotlib joblib threadpoolctl jupyterlab ipykernel
python -m jupyterlab
```

한글 글꼴은 맑은 고딕, Noto Sans CJK KR, 나눔고딕, AppleGothic 중 하나를 사용한다. 노트북의 작업 위치는 프로젝트 루트 또는 `notebooks/`다.

### 2. 원자료 두 CSV 준비

원자료 두 CSV는 로컬 `data/`에 배치하며 저장소 업로드 대상에서 제외한다.

| 파일 | 준비 방법 |
|---|---|
| `data/MetroPT3(AirCompressor).csv` | [UCI MetroPT-3 Dataset](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)의 Download에서 내려받아 압축 해제 후 배치. 라이선스: CC BY 4.0. |
| `data/apu_failure_events.csv` | 팀에서 정리한 전문가 고장 기록 CSV. [Davari 등(2021)](https://doi.org/10.1109/DSAA53316.2021.9564181) 6쪽 표 II의 21개 구간을 바탕으로 작성. |

센서 파일에는 15개 센서와 시간 정보가 있다. 주기·특징 계산에는 `timestamp`, `TP3`, `Motor_current`, `COMP`를 사용한다. 고장 CSV의 필수 열은 `event_id`, `failure_start`, `failure_end`이며, 저장된 분석 자료에는 `duration_minutes_reported`, `severity`도 포함된다. 날짜·시간은 pandas에서 해석 가능한 형식을 사용한다.

고장 CSV는 센서 자료와 별도로 준비한다. 데이터 출처: [data/README.md](data/README.md) · 변수 설명: [COLUMN.md](data/COLUMN.md).

### 3. 노트북 실행

Jupyter에서 01 → 02 → 03 → 04 → 05 순으로 실행한다. 각 파일의 셀은 위에서 아래로 실행하며, 후속 단계는 앞 단계의 저장 파일을 읽는다.

| 순서 | 노트북 | 작업·산출물 |
|---|---|---|
| 01 | [데이터 확인](notebooks/01_데이터확인.ipynb) | 전체 변수의 결측·시간 범위·관측 공백·고장 기록 확인. 결과 표 표시. |
| 02 | [주기 전처리·특징 생성](notebooks/02_주기전처리_특징생성.ipynb) | 완전 주기·A16·라벨·기간 선택표 생성. CSV 3개, 그림 01~02 저장. |
| 03 | [시계열 분석](notebooks/03_시계열분석.ipynb) | 주기별 신호 통계·일별 분포·최근 24시간 변화 분석. 신호 통계 CSV, 그림 03 저장. |
| 04 | [모델 학습·검증·평가](notebooks/04_모델학습_검증_평가.ipynb) | 모델 학습·검증 설정 선택·7월 평가·탐지 목표 7·8·9건 비교. 예측 CSV·학습 모델, 그림 04~06·13 저장. |
| 05 | [경보·오탐미탐 평가](notebooks/05_경보_오탐미탐_평가.ipynb) | 사건별 첫 경보·일별 발송·반복 부담·LOF 오탐·IF 미탐 사례 분석. 그림 07~12 저장. |

노트북 실행 시 생성되는 후속 단계 입력 파일:

| 생성 단계 | `data/`에 저장하는 파일 |
|---|---|
| 02 | `APU_cycle_features_and_labels.csv`, `APU_cycle_splits.csv`, `APU_failure_episodes.csv` |
| 03 | `APU_cycle_signal_statistics.csv` |
| 04 | `APU_predictions.csv`, `APU_fitted_models.joblib` |

### 4. 결과 확인

수치는 노트북 표, 그림은 [figures/](figures/), 보고서는 [report/](report/)에 정리했다. 주요 그림: [7월 주기 지표](figures/그림05_7월_Precision_Recall_F1.png) · [사건별 최초 경보](figures/그림07_사건별_최초경보_선행시간.png) · [검증 탐지 목표별 오탐](figures/그림13_검증_탐지목표별_최소오탐.png). HTML 발표 자료는 `report/presentation/index.html`을 브라우저에서 연다.

## 팀원과 역할

| 이름 | 역할 |
|---|---|
| 이하일 | 팀장 · 발표 · 프로젝트 총괄 |
| 차승윤 | 전처리 · 시계열 분석 |
| 신승원 | 데이터 관리 |
| 김제환 | 용어 해석 · 문서 정리 |
| 전미소 | 모델링 |

## 참고 문헌과 자료

- [MetroPT-3 Dataset · UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset) — 센서 원자료, 변수 설명, 다운로드와 라이선스. 데이터 DOI: [10.24432/C5VW3R](https://doi.org/10.24432/C5VW3R).
- Davari, N., Veloso, B., Ribeiro, R. P., Pereira, P. M., & Gama, J. (2021). [Predictive maintenance based on anomaly detection using deep learning for air production unit in the railway industry](https://doi.org/10.1109/DSAA53316.2021.9564181). IEEE DSAA. — 전문가 고장 기록의 출처.
- scikit-learn 공식 문서: [IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html), [LocalOutlierFactor](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.LocalOutlierFactor.html), [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) — 이상 점수와 입력 표준화 구현.

## 결과의 해석 범위

- 7월은 개발 중 반복 확인한 과거 자료의 회고적 평가다. 전체 3개 사건 중 전조가 관측된 사건은 2개다. 같은 설정을 새 기간에 적용한 검증이 필요하다.
- IF 선정은 A16·검증 최소 7/9건 탐지 조건에 한정된다. 검증 목표가 8·9건이면 LOF의 오탐이 가장 적다.
- 정상 후보·전조는 보유 고장 기록과 시간 구간으로 분류했다. 미기록 고장·관측 공백·물리적 고장 원인은 추가 센서·정비 기록으로 확인해야 한다.
- 경보와 대시보드는 과거 자료의 탐색·재생 결과다. 현장 점검 횟수와 비용 절감 효과는 새 관측 자료와 실제 점검 기록이 있어야 평가할 수 있다.
