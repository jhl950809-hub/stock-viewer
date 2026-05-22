"""
KOSPI + KOSDAQ 전 종목 일봉 OHLCV 다운로드 (2010-01-01 ~ 오늘).

소스:
  - 종목 리스트: FinanceDataReader (KRX 상장 전 종목)
  - 가격 데이터: yfinance ({code}.KS / .KQ) — 2010년부터 데이터 보유

저장 구조:
  data/
    tickers.xlsx              # 전체 종목 리스트
    ohlcv/{ticker}.parquet    # 종목별 일봉
    ohlcv_sample.xlsx         # 시총 상위 20개 샘플 (시트별)
    progress.json             # 이어받기 상태
    failed.txt                # 실패 종목 로그
"""

from __future__ import annotations

import json
import time
import warnings
from datetime import datetime
from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd
import yfinance as yf
from tqdm import tqdm

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OHLCV_DIR = DATA / "ohlcv"
PROGRESS = DATA / "progress.json"
TICKERS_XLSX = DATA / "tickers.xlsx"
SAMPLE_XLSX = DATA / "ohlcv_sample.xlsx"
FAILED_LOG = DATA / "failed.txt"

START = "2010-01-01"
END = datetime.today().strftime("%Y-%m-%d")
BATCH = 40  # yfinance 배치 크기


def ensure_dirs() -> None:
    OHLCV_DIR.mkdir(parents=True, exist_ok=True)


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"done": [], "failed": []}


def save_progress(state: dict) -> None:
    PROGRESS.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_ticker_list() -> pd.DataFrame:
    """KOSPI + KOSDAQ 전 종목 (현재 상장)."""
    cols = ["Code", "Name", "Marcap"]
    kospi = fdr.StockListing("KOSPI")[cols].copy()
    kospi["market"] = "KOSPI"
    kospi["yf_symbol"] = kospi["Code"] + ".KS"

    kosdaq = fdr.StockListing("KOSDAQ")[cols].copy()
    kosdaq["market"] = "KOSDAQ"
    kosdaq["yf_symbol"] = kosdaq["Code"] + ".KQ"

    df = pd.concat([kospi, kosdaq], ignore_index=True)
    df = df.rename(columns={"Code": "ticker", "Name": "name", "Marcap": "marcap"})
    df = df.dropna(subset=["ticker"]).drop_duplicates("ticker")
    df = df.sort_values(["market", "ticker"]).reset_index(drop=True)
    df.to_excel(TICKERS_XLSX, index=False)
    return df


def _flatten(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """yfinance 다운로드 결과 정리: 단일 종목 DataFrame으로."""
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        # 멀티 종목 다운로드 시: (Field, Ticker)
        if symbol in df.columns.get_level_values(-1):
            df = df.xs(symbol, axis=1, level=-1)
        else:
            df.columns = df.columns.get_level_values(0)
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    df.index.name = "date"
    df = df.reset_index()
    return df


def download_batch(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """심볼 리스트를 한 번에 다운로드. 실패 시 건별 재시도."""
    out: dict[str, pd.DataFrame] = {}
    try:
        raw = yf.download(
            tickers=symbols,
            start=START,
            end=END,
            progress=False,
            auto_adjust=False,
            group_by="column",
            threads=True,
        )
    except Exception:
        raw = pd.DataFrame()

    if raw is None or raw.empty:
        # 건별 재시도
        for s in symbols:
            try:
                d = yf.download(s, start=START, end=END, progress=False, auto_adjust=False)
                out[s] = _flatten(d, s)
            except Exception:
                out[s] = pd.DataFrame()
        return out

    if isinstance(raw.columns, pd.MultiIndex):
        for s in symbols:
            try:
                sub = raw.xs(s, axis=1, level=-1).dropna(how="all")
                out[s] = _flatten(sub, s)
            except Exception:
                out[s] = pd.DataFrame()
    else:
        # 단일 종목 결과
        out[symbols[0]] = _flatten(raw, symbols[0])
    return out


def write_sample(tickers: pd.DataFrame) -> None:
    # 시총 상위 20: 마지막 영업일 종가 × 발행주식수 정보가 없으니 거래대금 기반 → 그냥 KOSPI 상위 20
    candidates = tickers.sort_values("marcap", ascending=False).head(20)
    with pd.ExcelWriter(SAMPLE_XLSX, engine="openpyxl") as xw:
        for _, row in candidates.iterrows():
            f = OHLCV_DIR / f"{row['ticker']}.parquet"
            if not f.exists():
                continue
            sheet = (str(row["name"]) or row["ticker"])[:28]
            pd.read_parquet(f).to_excel(xw, sheet_name=sheet, index=False)
    print(f"[OK] 샘플 엑셀 저장: {SAMPLE_XLSX}")


def main() -> None:
    ensure_dirs()
    print(f"[INFO] 종목 리스트 수집 (기준일 {END})...")
    tickers = fetch_ticker_list()
    print(
        f"[INFO] 종목 수 {len(tickers)} "
        f"(KOSPI {sum(tickers.market=='KOSPI')}, KOSDAQ {sum(tickers.market=='KOSDAQ')})"
    )

    state = load_progress()
    done = set(state["done"])
    todo = tickers[~tickers["ticker"].isin(done)].copy()
    print(f"[INFO] 다운로드 대상 {len(todo)} (이미 완료 {len(done)})")

    failed_now: list[str] = []

    sym2tic = dict(zip(todo["yf_symbol"], todo["ticker"]))
    symbols = list(todo["yf_symbol"])

    for i in tqdm(range(0, len(symbols), BATCH), desc="Batches"):
        chunk = symbols[i : i + BATCH]
        result = download_batch(chunk)
        for s in chunk:
            tic = sym2tic[s]
            df = result.get(s, pd.DataFrame())
            if df is None or df.empty:
                failed_now.append(tic)
                continue
            df["ticker"] = tic
            df.to_parquet(OHLCV_DIR / f"{tic}.parquet", index=False)
            done.add(tic)
        if i % (BATCH * 5) == 0:
            state["done"] = sorted(done)
            state["failed"] = sorted(set(failed_now))
            save_progress(state)
        time.sleep(0.5)  # yahoo 레이트 리밋 완화

    state["done"] = sorted(done)
    state["failed"] = sorted(set(failed_now))
    save_progress(state)
    FAILED_LOG.write_text("\n".join(state["failed"]), encoding="utf-8")
    print(f"[INFO] 다운로드 완료. 성공 {len(state['done'])} / 실패 {len(state['failed'])}")
    if state["failed"]:
        print(f"[INFO] 실패 종목 목록: {FAILED_LOG}")

    write_sample(tickers)


if __name__ == "__main__":
    main()
