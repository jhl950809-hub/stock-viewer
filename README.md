# KRX 주식 데이터

KOSPI + KOSDAQ 전 종목 일봉 OHLCV (2010-01-01 ~ 오늘) 수집 도구.

## 실행

```powershell
py download_krx.py
```

## 저장 구조

```
data/
  tickers.xlsx              # 전체 종목 리스트 (코드/이름/시장)
  ohlcv/{ticker}.parquet    # 종목별 일봉 (date, open, high, low, close, volume, value, change_pct, ticker)
  ohlcv_sample.xlsx         # 시총 상위 20개 샘플 (엑셀로 미리보기용)
  progress.json             # 이어받기 상태 - 중단 후 재실행하면 done 종목은 건너뜀
```

## 왜 Parquet + 샘플 엑셀?

- 종목 수가 약 2,500개라 시트별 엑셀 한 파일은 비현실적 (시트 한도/속도/파일 크기).
- Parquet는 종목별 수십 KB로 작고 pandas로 빠르게 로드됨.
- 분석 시 `pd.read_parquet("data/ohlcv/005930.parquet")` 형태로 사용.
- 전체를 하나로 합치고 싶을 때:
  ```python
  import pandas as pd, pathlib
  files = list(pathlib.Path("data/ohlcv").glob("*.parquet"))
  all_df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
  ```
