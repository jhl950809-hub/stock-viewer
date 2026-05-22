"""
정적 OHLCV JSON 익스포트.

viewer_server.py 의 /ohlcv/{code} 동적 응답을 빌드 타임에 ohlcv/{code}.json 파일로 굽는다.
GitHub Pages 같은 정적 호스팅에서 viewer.html 의 fetch('ohlcv/{code}.json') 로 바로 동작.

- 최근 LOOKBACK_DAYS 일치만 (모바일/Pages 용량 절감)
- viewer.html 의 Chart.js 가 실제 쓰는 필드만 (close/ma20/ma60/ma120/rsi14/cci20)
- 가격은 정수, 보조지표는 소수 1자리로 round → 사이즈 30~40% 절감
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
import time

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "data" / "ohlcv"
OUT = ROOT / "ohlcv"
OUT.mkdir(exist_ok=True)

LOOKBACK_DAYS = 1250  # 약 5년치 영업일


def _clean_int(s: pd.Series) -> list:
    return [
        None if (x is None or (isinstance(x, float) and math.isnan(x))) else int(round(float(x)))
        for x in s.tolist()
    ]


def _clean_round(s: pd.Series, ndigits: int = 1) -> list:
    return [
        None if (x is None or (isinstance(x, float) and math.isnan(x))) else round(float(x), ndigits)
        for x in s.tolist()
    ]


def compute_payload(df: pd.DataFrame, ticker: str) -> dict | None:
    df = df.sort_values("date").reset_index(drop=True)
    if len(df) == 0:
        return None
    close = df["close"]
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma120 = close.rolling(120).mean()
    d_close = close.diff()
    up = d_close.clip(lower=0).rolling(14).mean()
    dn = (-d_close.clip(upper=0)).rolling(14).mean()
    rs = up / dn.replace(0, float("nan"))
    rsi14 = 100 - 100 / (1 + rs)
    if "high" in df.columns and "low" in df.columns:
        tp = (df["high"] + df["low"] + close) / 3
    else:
        tp = close
    tp_ma20 = tp.rolling(20).mean()
    tp_md20 = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci20 = (tp - tp_ma20) / (0.015 * tp_md20.replace(0, float("nan")))

    if len(df) > LOOKBACK_DAYS:
        df = df.iloc[-LOOKBACK_DAYS:]
        close = close.iloc[-LOOKBACK_DAYS:]
        ma20 = ma20.iloc[-LOOKBACK_DAYS:]
        ma60 = ma60.iloc[-LOOKBACK_DAYS:]
        ma120 = ma120.iloc[-LOOKBACK_DAYS:]
        rsi14 = rsi14.iloc[-LOOKBACK_DAYS:]
        cci20 = cci20.iloc[-LOOKBACK_DAYS:]

    return {
        "ticker": ticker,
        "date": [str(x)[:10] for x in df["date"].tolist()],
        "close": _clean_int(close),
        "ma20": _clean_int(ma20),
        "ma60": _clean_int(ma60),
        "ma120": _clean_int(ma120),
        "rsi14": _clean_round(rsi14, 1),
        "cci20": _clean_round(cci20, 1),
    }


def main() -> None:
    files = sorted(SRC.glob("*.parquet"))
    print(f"[INFO] OHLCV JSON 익스포트 ({len(files)} 종목, 최근 {LOOKBACK_DAYS}일)")
    t0 = time.time()
    ok = 0
    skipped = 0
    total = 0
    for i, fp in enumerate(files, 1):
        ticker = fp.stem
        if not (ticker.isdigit() and len(ticker) == 6):
            skipped += 1
            continue
        try:
            df = pd.read_parquet(fp)
            payload = compute_payload(df, ticker)
            if payload is None:
                skipped += 1
                continue
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            (OUT / f"{ticker}.json").write_text(body, encoding="utf-8")
            total += len(body.encode("utf-8"))
            ok += 1
        except Exception as e:
            print(f"  {ticker} 실패: {e}")
            skipped += 1
        if i % 500 == 0:
            print(f"  {i}/{len(files)}  ({time.time()-t0:.0f}s)")
    avg = total / ok if ok else 0
    print(f"[OK] {ok}개 저장 / {skipped}개 스킵 → {OUT}")
    print(f"     총 {total/1024/1024:.1f}MB, 평균 {avg/1024:.1f}KB, 소요 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
