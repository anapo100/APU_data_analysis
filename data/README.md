# 데이터

분석에 사용하는 입력 CSV와 노트북 실행 중 생성하는 파생 파일을 보관한다.

## 입력 자료

아래 두 CSV를 로컬 `data/`에 배치한다. 원자료 두 파일은 저장소 업로드 대상에서 제외한다.

| 파일 | 출처·준비 방법 |
|---|---|
| `MetroPT3(AirCompressor).csv` | [UCI MetroPT-3 Dataset](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)의 Download에서 내려받아 압축을 푼다. 라이선스는 CC BY 4.0이다. |
| `apu_failure_events.csv` | 팀이 정리한 고장 기록 CSV를 별도로 준비한다. [Davari 등(2021)](https://doi.org/10.1109/DSAA53316.2021.9564181) 6쪽 표 II의 전문가 고장 기록 21구간을 CSV로 정리한 자료다. |

센서 파일의 전체 변수를 확인한 뒤 주기·특징 계산에 `timestamp`, `TP3`, `Motor_current`, `COMP`를 사용한다. 센서별 의미와 단위는 [COLUMN.md](COLUMN.md)에 정리했다.

고장 기록의 필수 열은 `event_id`, `failure_start`, `failure_end`다. 날짜·시간은 pandas에서 해석 가능한 형식을 사용한다. 노트북은 센서 CSV와 고장 CSV를 각각 입력으로 읽으므로, 실행 전에 두 파일을 모두 준비한다.

## 파생 자료

아래 파일은 노트북 실행 시 `data/`에 생성된다. 입력 자료와 구분하며, 후속 단계에서 다시 읽어 사용한다.

| 생성 단계 | 파일 | 내용 |
|---|---|---|
| 02 | `APU_cycle_features_and_labels.csv` | 완전 주기의 A16 특징과 고장 라벨 |
| 02 | `APU_cycle_splits.csv` | 주기별 학습·검증·7월 평가 구분 |
| 02 | `APU_failure_episodes.csv` | 겹치거나 맞닿은 고장 기록을 병합한 사건 목록 |
| 03 | `APU_cycle_signal_statistics.csv` | 주기별 압력·전류와 운전 시간 통계 |
| 04 | `APU_predictions.csv` | 모델별 이상 점수·임곗값·판정·경보 발송 여부 |
| 04 | `APU_fitted_models.joblib` | 표준화 도구, 선택한 모델·임곗값, 특징 목록 |

## 실행 순서

Jupyter에서 01 → 02 → 03 → 04 → 05 순으로 실행한다. 각 노트북의 셀은 위에서 아래로 실행한다.

| 순서 | 노트북 | 데이터 처리 |
|---|---|---|
| 01 | [데이터 확인](../notebooks/01_데이터확인.ipynb) | 원본 센서·고장 기록의 변수 품질, 시간 범위와 관측 공백 확인 |
| 02 | [주기 전처리·특징 생성](../notebooks/02_주기전처리_특징생성.ipynb) | 원본에서 완전 주기를 추출하고 특징·라벨·기간 구분 저장 |
| 03 | [시계열 분석](../notebooks/03_시계열분석.ipynb) | 원본 센서와 02의 결과로 주기별 신호 통계 생성 |
| 04 | [모델 학습·검증·평가](../notebooks/04_모델학습_검증_평가.ipynb) | 02의 결과로 모델을 학습·평가하고 예측과 학습 모델 저장 |
| 05 | [경보·오탐미탐 평가](../notebooks/05_경보_오탐미탐_평가.ipynb) | 앞 단계의 결과와 원본 센서로 경보·오탐·미탐 분석 |

수치 표는 노트북에 표시하고, 분석 그림은 [figures/](../figures/)에 저장한다. 설치 명령과 전체 분석 구성은 [프로젝트 README](../README.md)에 정리했다.
