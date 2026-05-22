"""
일별 증분 데이터 업데이트.

동작:
  1. data/ohlcv/{ticker}.parquet 마다 last_date 확인
  2. 같은 시작일끼리 그룹화하여 yfinance 배치 다운로드
  3. 기존 데이터에 신규 행 append, date 중복 제거 후 저장
  4. 신규 상장 종목 (FDR 리스트 vs 현재 보유) 비교, 새 종목은 2010-01-01부터 다운로드
  5. features 캐시(features_upside.parquet, features_rank.parquet) 삭제 → 다음 학습 시 재계산

전 종목 모두 동일 시점에 갱신된 상황이라면 보통 한 번의 배치 다운로드로 끝남.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OHLCV = DATA / "ohlcv"
TICKERS_XLSX = DATA / "tickers.xlsx"
LOG_JSON = DATA / "update_log.json"

CACHE_TO_INVALIDATE = [
    DATA / "features_upside.parquet",
    DATA / "features_rank.parquet",
]

BATCH = 50
MIN_DATE = pd.Timestamp("2010-01-01")


def yf_symbol(ticker: str, market: str) -> str:
    return f"{ticker}.{'KS' if market == 'KOSPI' else 'KQ'}"


def refresh_ticker_list() -> pd.DataFrame:
    """FDR로 최신 KOSPI/KOSDAQ 종목리스트를 받아 tickers.xlsx 갱신."""
    import FinanceDataReader as fdr

    cols = ["Code", "Name", "Marcap"]
    rows = []
    for mkt, suf in (("KOSPI", "KS"), ("KOSDAQ", "KQ")):
        df = fdr.StockListing(mkt)[cols].copy()
        df["market"] = mkt
        df["yf_symbol"] = df["Code"] + "." + suf
        rows.append(df)
    df = pd.concat(rows, ignore_index=True)
    df = df.rename(columns={"Code": "ticker", "Name": "name", "Marcap": "marcap"})
    df = df.dropna(subset=["ticker"]).drop_duplicates("ticker")
    df = df.sort_values(["market", "ticker"]).reset_index(drop=True)
    df.to_excel(TICKERS_XLSX, index=False)
    return df


def load_existing_last_date(ticker: str) -> pd.Timestamp | None:
    f = OHLCV / f"{ticker}.parquet"
    if not f.exists():
        return None
    try:
        df = pd.read_parquet(f, columns=["date"])
        if df.empty:
            return None
        return pd.to_datetime(df["date"]).max()
    except Exception:
        return None


def download_batch(symbols: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    try:
        raw = yf.download(
            tickers=symbols, start=start, end=end,
            progress=False, auto_adjust=False, group_by="column", threads=True,
        )
    except Exception:
        raw = pd.DataFrame()

    if raw is None or raw.empty:
        for s in symbols:
            try:
                d = yf.download(s, start=start, end=end, progress=False, auto_adjust=False)
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
        out[symbols[0]] = _flatten(raw, symbols[0])
    return out


def _flatten(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        if symbol in df.columns.get_level_values(-1):
            df = df.xs(symbol, axis=1, level=-1)
        else:
            df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close",
        "Adj Close": "adj_close", "Volume": "volume",
    })
    df.index.name = "date"
    df = df.reset_index()
    return df


def append_save(ticker: str, new_df: pd.DataFrame) -> int:
    """기존 parquet에 새 데이터 합치기. 추가된 행 수 반환."""
    if new_df is None or new_df.empty:
        return 0
    new_df = new_df.copy()
    new_df["ticker"] = ticker
    new_df["date"] = pd.to_datetime(new_df["date"])

    f = OHLCV / f"{ticker}.parquet"
    if f.exists():
        old = pd.read_parquet(f)
        old["date"] = pd.to_datetime(old["date"])
        merged = pd.concat([old, new_df], ignore_index=True)
        merged = merged.drop_duplicates(subset="date", keep="last").sort_values("date").reset_index(drop=True)
        added = len(merged) - len(old)
    else:
        merged = new_df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
        added = len(merged)
    merged.to_parquet(f, index=False)
    return added


def main():
    print(f"[INFO] 일별 업데이트 시작 ({datetime.now():%Y-%m-%d %H:%M})")
    today = pd.Timestamp.today().normalize()
    end_str = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")  # yfinance end는 exclusive

    # 1. 종목리스트 갱신
    print("[INFO] 종목리스트 갱신 (FDR)")
    tickers = refresh_ticker_list()
    print(f"  현재 KOSPI {sum(tickers.market=='KOSPI')} / KOSDAQ {sum(tickers.market=='KOSDAQ')}")

    # 2. 종목별 시작일 결정
    plan: dict[str, str] = {}  # ticker → start_date
    new_listings = 0
    for _, row in tickers.iterrows():
        last = load_existing_last_date(row["ticker"])
        if last is None:
            plan[row["ticker"]] = MIN_DATE.strftime("%Y-%m-%d")
            new_listings += 1
        else:
            need_from = last + pd.Timedelta(days=1)
            if need_from > today:
                continue  # 이미 최신
            plan[row["ticker"]] = need_from.strftime("%Y-%m-%d")
    print(f"[INFO] 갱신 대상 {len(plan)} 종목 (그 중 신규 상장 {new_listings})")
    if not plan:
        print("[OK] 모든 종목이 이미 최신.")
        return

    # 3. 시작일별로 그룹화 후 배치 다운로드
    by_start = defaultdict(list)
    for tic, start in plan.items():
        by_start[start].append(tic)

    sym_to_tic = {}
    log: dict = {"run_at": datetime.now().isoformat(), "groups": []}
    total_added = 0
    failed = []

    for start, ticks in sorted(by_start.items()):
        print(f"\n[그룹] start={start}, 종목수 {len(ticks)}")
        # ticker → yf_symbol
        merged_map = tickers.set_index("ticker")
        symbols = []
        for t in ticks:
            try:
                row = merged_map.loc[t]
                sym = yf_symbol(t, row["market"])
                symbols.append(sym)
                sym_to_tic[sym] = t
            except KeyError:
                failed.append(t)

        added_in_group = 0
        for i in range(0, len(symbols), BATCH):
            chunk = symbols[i:i+BATCH]
            res = download_batch(chunk, start=start, end=end_str)
            for s in chunk:
                tic = sym_to_tic[s]
                df = res.get(s, pd.DataFrame())
                if df.empty:
                    failed.append(tic)
                    continue
                added = append_save(tic, df)
                added_in_group += added
                total_added += added
            time.sleep(0.4)

        log["groups"].append({"start": start, "n_tickers": len(ticks), "rows_added": added_in_group})
        print(f"  -> {added_in_group} 행 추가")

    log["total_rows_added"] = total_added
    log["failed_tickers"] = failed
    LOG_JSON.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 50)
    print(f"[완료] 총 {total_added} 행 추가, 실패 {len(failed)} 종목")
    print(f"  로그: {LOG_JSON}")

    # 4. features 캐시 무효화 → 다음 학습 시 재계산
    invalidated = []
    for cache in CACHE_TO_INVALIDATE:
        if cache.exists():
            cache.unlink()
            invalidated.append(cache.name)
    if invalidated:
        print(f"[INFO] 캐시 삭제 (다음 학습 시 재계산): {', '.join(invalidated)}")

    if failed:
        print(f"\n[WARN] 실패 종목 {len(failed)} (상장폐지/거래정지 가능): {failed[:10]}{'...' if len(failed)>10 else ''}")


if __name__ == "__main__":
    main()
