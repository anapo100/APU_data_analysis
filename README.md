# APU_data_analysis
프로젝트의 목적: 압축기의 공기 생산 장치(APU) 이상탐지 

개인별 역할:

**팀장: 이하일, 발표 / 프로젝트 총괄 디렉팅**

**시계열: 차승윤 / 시계열**

**데이터: 신승원 / 데이터 관리**

**해석/문서: 김제환 / 용어 해석 및 문서 정리**

**모델링: 전미소 / 모델링**

데이터 준비방법: # 입력 데이터

## 원본 센서와 라벨

- 센서 파일 `MetroPT3(AirCompressor).csv`: [UCI MetroPT-3 Dataset](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)의 Download에서 받는다. 라이선스 표기는 CC BY 4.0이다.
- 라벨 파일 `apu_failure_events.csv`: 팀이 보유한 고장 라벨은 [Davari 등(2021)](https://doi.org/10.1109/DSAA53316.2021.9564181) 6쪽 표 II의 전문가 고장 기록을 활용하였다.
