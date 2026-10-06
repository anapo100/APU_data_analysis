# 입력 데이터

## 원본 센서와 라벨

- 센서 파일 `MetroPT3(AirCompressor).csv`: [UCI MetroPT-3 Dataset](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)의 Download에서 받는다. 라이선스 표기는 CC BY 4.0이다.
- 라벨 파일 `apu_failure_events.csv`: 팀이 보유한 고장 라벨은 [Davari 등(2021)](https://doi.org/10.1109/DSAA53316.2021.9564181) 6쪽 표 II의 전문가 고장 기록을 활용하였다.  해당 기록을 바탕으로 apu_failure_events.csv를 만들었다.

원본 데이터를 바탕으로 `notebooks/01_데이터확인.ipynb`에서 전체 변수 품질, 시간 범위, 관측 공백과 고장 기록을 확인한다. 
각 변수 설명은 [COLUMN.md]를 참고한다.
