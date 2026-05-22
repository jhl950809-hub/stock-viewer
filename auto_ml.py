"""
자체학습 ML 파이프라인 (최대 1000 boost rounds, early stopping 포함).

- 39개 특성 (단·중·장기 + 돌파/모멘텀가속/오실레이터/거래량/횡단면랭크)
- 두 가지 자체학습 모델:
    M1 분류: 20일 후 상승 확률 (LightGBM binary, ≤1000 rounds + early stop)
    M2 회귀: 20일 후 변동률 % (LightGBM regression, ≤1000 rounds + early stop)
- 종목별 출력 (predictions_pct.xlsx):
    종목코드, 종목명, 시장, 현재가,
    예상상승확률, 예상변동률(%), 예상가격, 추천, 신뢰도
"""

from __future__ import annotations

import pathlib
import sys
import time
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OHLCV = DATA / "ohlcv"
FEATURES_PARQUET = DATA / "features_upside.parquet"

TRAIN_END = "2024-12-31"
TEST_START = "2025-01-01"
FORWARD = 20
NUM_ROUNDS = 1000
EARLY_STOP = 50
STRONG_UP = 0.05

BASE_FEATURES = [
    "ret_1", "ret_5", "ret_20", "ret_60", "ret_120", "ret_252",
    "ma_ratio_5", "ma_ratio_20", "ma_ratio_60", "ma_ratio_120", "ma_ratio_252",
    "ma20_over_ma60", "ma60_over_ma120", "ma120_over_ma252",
    "vol_5", "vol_20", "vol_60",
    "rsi_14", "rsi_28", "vol_z",
    "drawdown_60", "drawdown_252", "dist_from_low_252", "trend_slope_60",
]
UPSIDE_FEATURES = [
    "breakout_60", "breakout_120", "new_highs_20", "dist_from_max_252",
    "accel_short", "accel_mid",
    "bb_pos_20", "stoch_k_14", "williams_r_14", "mfi_14",
    "macd_hist", "macd_signal_pos",
    "obv_slope_20", "volume_breakout", "gap_up_20",
]
CS_FEATURES = ["cs_rank_ret_20", "cs_rank_ret_60", "cs_rank_vol_20"]
ALL_FEATURES = BASE_FEATURES + UPSIDE_FEATURES + CS_FEATURES


# ---------------- 특성화 (upside_train.py와 동일) ----------------

def rsi(c: pd.Series, period: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = (-d.clip(upper=0)).rolling(period).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def featurize_one(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    c = df["close"].astype(float)
    h = df.get("high", c).astype(float)
    l = df.get("low", c).astype(float)
    v = df["volume"].astype(float)
    r = c.pct_change(1)

    df["ret_1"] = r
    for w in (5, 20, 60, 120, 252):
        df[f"ret_{w}"] = c.pct_change(w)
    for w in (5, 20, 60, 120, 252):
        df[f"ma_ratio_{w}"] = c / c.rolling(w).mean() - 1

    ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
    ma120 = c.rolling(120).mean(); ma252 = c.rolling(252).mean()
    df["ma20_over_ma60"] = ma20 / ma60 - 1
    df["ma60_over_ma120"] = ma60 / ma120 - 1
    df["ma120_over_ma252"] = ma120 / ma252 - 1

    df["vol_5"] = r.rolling(5).std()
    df["vol_20"] = r.rolling(20).std()
    df["vol_60"] = r.rolling(60).std()
    df["rsi_14"] = rsi(c, 14)
    df["rsi_28"] = rsi(c, 28)

    vm = v.rolling(20).mean(); vs = v.rolling(20).std().replace(0, np.nan)
    df["vol_z"] = (v - vm) / vs

    high60 = c.rolling(60).max(); high252 = c.rolling(252).max(); low252 = c.rolling(252).min()
    df["drawdown_60"] = c / high60 - 1
    df["drawdown_252"] = c / high252 - 1
    df["dist_from_low_252"] = (c - low252) / low252.replace(0, np.nan)

    x60 = np.arange(60)
    def slope(arr):
        if np.isnan(arr).any():
            return np.nan
        m = np.polyfit(x60, arr, 1)[0]
        return m / arr.mean() if arr.mean() != 0 else np.nan
    df["trend_slope_60"] = c.rolling(60).apply(slope, raw=True)

    df["breakout_60"] = (c >= high60 * 0.999).astype("int8")
    df["breakout_120"] = (c >= c.rolling(120).max() * 0.999).astype("int8")
    df["new_highs_20"] = df["breakout_60"].rolling(20).sum()
    df["dist_from_max_252"] = c / high252 - 1
    df["accel_short"] = df["ret_20"] - df["ret_60"]
    df["accel_mid"] = df["ret_60"] - df["ret_120"]

    bb_std = c.rolling(20).std()
    bb_up = ma20 + 2 * bb_std
    bb_lo = ma20 - 2 * bb_std
    df["bb_pos_20"] = (c - bb_lo) / (bb_up - bb_lo).replace(0, np.nan)

    h14 = h.rolling(14).max(); l14 = l.rolling(14).min()
    df["stoch_k_14"] = (c - l14) / (h14 - l14).replace(0, np.nan) * 100
    df["williams_r_14"] = (h14 - c) / (h14 - l14).replace(0, np.nan) * -100

    tp = (h + l + c) / 3
    mf = tp * v
    pos_mf = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_mf = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
    mfr = pos_mf / neg_mf.replace(0, np.nan)
    df["mfi_14"] = 100 - 100 / (1 + mfr)

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    df["macd_hist"] = (macd - sig) / c
    df["macd_signal_pos"] = (macd > sig).astype("int8")

    direction = np.sign(c.diff()).fillna(0)
    obv = (direction * v).cumsum()
    obv_ma = obv.rolling(20).mean().replace(0, np.nan)
    obv_diff = obv - obv.shift(20)
    df["obv_slope_20"] = obv_diff / obv_ma.abs()

    df["volume_breakout"] = (df["vol_z"] > 2).astype("int8")
    df["gap_up_20"] = (r > 0.03).rolling(20).sum()

    fwd = c.shift(-FORWARD) / c - 1
    df["fwd_ret"] = fwd
    df["label_up_20"] = (fwd > 0).astype("Int8")
    return df


def build_dataset() -> pd.DataFrame:
    if FEATURES_PARQUET.exists():
        print(f"[INFO] 캐시 로드: {FEATURES_PARQUET}")
        return pd.read_parquet(FEATURES_PARQUET)

    print(f"[INFO] 특성화 시작 (특성 {len(ALL_FEATURES)}개)")
    files = list(OHLCV.glob("*.parquet"))
    keep_cols = (
        ["date", "ticker"] + BASE_FEATURES + UPSIDE_FEATURES
        + ["fwd_ret", "label_up_20", "close"]
    )
    rows = []
    t0 = time.time()
    for i, f in enumerate(files, 1):
        df = pd.read_parquet(f)
        if len(df) < 280:
            continue
        df = featurize_one(df)
        rows.append(df[keep_cols])
        if i % 500 == 0:
            print(f"  {i}/{len(files)}  ({time.time()-t0:.0f}s)")
    full = pd.concat(rows, ignore_index=True)
    full["date"] = pd.to_datetime(full["date"])

    print("[INFO] 횡단면 랭크 계산")
    for src, dst in [("ret_20", "cs_rank_ret_20"), ("ret_60", "cs_rank_ret_60"), ("vol_20", "cs_rank_vol_20")]:
        full[dst] = full.groupby("date")[src].rank(method="first", pct=True)

    full.to_parquet(FEATURES_PARQUET, index=False)
    print(f"[INFO] 특성 저장: {len(full):,} 행 ({time.time()-t0:.0f}s)")
    return full


# ---------------- 학습 ----------------

def split_for(full, label_col):
    base = full.dropna(subset=ALL_FEATURES)
    tr = base[(base["date"] <= TRAIN_END) & base[label_col].notna()]
    te = base[(base["date"] >= TEST_START) & base[label_col].notna()]
    return tr, te


def cb_progress(every=50):
    last_iter = [0]
    def cb(env):
        i = env.iteration + 1
        if i - last_iter[0] >= every or i == 1:
            msg = " ".join(f"{n}_{m}={v:.4f}"
                           for (n, m, v, _) in env.evaluation_result_list)
            print(f"  round {i:4d}: {msg}")
            last_iter[0] = i
    return cb


def train_classifier(tr, te):
    print(f"\n[M1 분류] train {len(tr):,} / test {len(te):,}, 최대 {NUM_ROUNDS} rounds (early stop {EARLY_STOP})")
    p = {
        "objective": "binary", "metric": ["auc", "binary_logloss"],
        "learning_rate": 0.03, "num_leaves": 63, "min_data_in_leaf": 200,
        "feature_fraction": 0.85, "bagging_fraction": 0.85, "bagging_freq": 5,
        "verbose": -1, "seed": 42,
    }
    dtr = lgb.Dataset(tr[ALL_FEATURES].astype("float32"), label=tr["label_up_20"].astype("int8"))
    dte = lgb.Dataset(te[ALL_FEATURES].astype("float32"), label=te["label_up_20"].astype("int8"), reference=dtr)
    t0 = time.time()
    m = lgb.train(
        p, dtr, num_boost_round=NUM_ROUNDS,
        valid_sets=[dtr, dte], valid_names=["train", "valid"],
        callbacks=[
            lgb.early_stopping(EARLY_STOP, verbose=True),
            cb_progress(50),
        ],
    )
    pp = m.predict(te[ALL_FEATURES].astype("float32"))
    auc = roc_auc_score(te["label_up_20"].astype(int), pp)
    print(f"[M1 분류] best_iteration={m.best_iteration}, valid_auc={auc:.4f}, {time.time()-t0:.0f}s")
    return m, auc


def train_regressor(tr, te):
    print(f"\n[M2 회귀] train {len(tr):,} / test {len(te):,}, 최대 {NUM_ROUNDS} rounds (early stop {EARLY_STOP})")
    p = {
        "objective": "regression", "metric": "rmse",
        "learning_rate": 0.03, "num_leaves": 63, "min_data_in_leaf": 200,
        "feature_fraction": 0.85, "bagging_fraction": 0.85, "bagging_freq": 5,
        "verbose": -1, "seed": 42,
    }
    dtr = lgb.Dataset(tr[ALL_FEATURES].astype("float32"), label=tr["fwd_ret"].astype("float32"))
    dte = lgb.Dataset(te[ALL_FEATURES].astype("float32"), label=te["fwd_ret"].astype("float32"), reference=dtr)
    t0 = time.time()
    m = lgb.train(
        p, dtr, num_boost_round=NUM_ROUNDS,
        valid_sets=[dtr, dte], valid_names=["train", "valid"],
        callbacks=[
            lgb.early_stopping(EARLY_STOP, verbose=True),
            cb_progress(50),
        ],
    )
    pp = m.predict(te[ALL_FEATURES].astype("float32"))
    rho, _ = spearmanr(pp, te["fwd_ret"].astype(float))
    rmse = float(np.sqrt(((pp - te["fwd_ret"].astype(float).values) ** 2).mean()))
    print(f"[M2 회귀] best_iteration={m.best_iteration}, spearman={rho:.4f}, rmse={rmse:.4f}, {time.time()-t0:.0f}s")
    return m, rho, rmse


# ---------------- 종목별 예측 출력 ----------------

def recommend(prob_up: float, pred_pct: float) -> str:
    """확률과 예상 변동률 결합 추천."""
    if prob_up >= 0.55 and pred_pct >= 3:
        return "★강한매수"
    if prob_up >= 0.50 and pred_pct >= 1:
        return "매수"
    if prob_up <= 0.40 and pred_pct <= -3:
        return "★강한매도"
    if prob_up <= 0.45 and pred_pct <= -1:
        return "매도"
    return "관망"


def confidence(prob_up: float, pred_pct: float) -> str:
    """방향 일치도 기반 신뢰도."""
    cls_dir = 1 if prob_up >= 0.5 else -1
    reg_dir = 1 if pred_pct >= 0 else -1
    if cls_dir != reg_dir:
        return "낮음(모델 불일치)"
    # 두 모델 일치 → 강도로 등급
    strength = abs(prob_up - 0.5) * 2 + min(abs(pred_pct) / 10, 1)
    if strength > 0.5:
        return "높음"
    if strength > 0.25:
        return "중간"
    return "낮음"


def predict_all(full: pd.DataFrame, m_cls, m_reg, tickers: pd.DataFrame) -> pd.DataFrame:
    """종목별 마지막 영업일 기준 예측."""
    base = full.dropna(subset=ALL_FEATURES)
    latest = base.sort_values("date").groupby("ticker", as_index=False).tail(1).copy()
    X = latest[ALL_FEATURES].astype("float32")

    p_up = m_cls.predict(X)
    pred_ret = m_reg.predict(X)

    out = pd.DataFrame({
        "ticker": latest["ticker"].values,
        "기준일": latest["date"].dt.strftime("%Y-%m-%d").values,
        "현재가": latest["close"].values.astype(float).round(0).astype(int),
        "예상상승확률(%)": (p_up * 100).round(2),
        "예상변동률(%)": (pred_ret * 100).round(2),
    })
    out["예상가격"] = (out["현재가"] * (1 + out["예상변동률(%)"] / 100)).round(0).astype(int)
    out["추천"] = [recommend(p, r) for p, r in zip(p_up, pred_ret * 100)]
    out["신뢰도"] = [confidence(p, r) for p, r in zip(p_up, pred_ret * 100)]

    out = out.merge(tickers[["ticker", "name", "market"]], on="ticker", how="left")
    out = out.rename(columns={"ticker": "종목코드", "name": "종목명", "market": "시장"})
    out = out[
        ["종목코드", "종목명", "시장", "기준일", "현재가",
         "예상상승확률(%)", "예상변동률(%)", "예상가격", "추천", "신뢰도"]
    ].sort_values("예상변동률(%)", ascending=False).reset_index(drop=True)

    out.to_excel(DATA / "predictions_pct.xlsx", index=False)
    print(f"\n[OK] 종목별 % 예측 저장: predictions_pct.xlsx ({len(out)} 종목)")
    return out


def feature_importance_save(model, name):
    imp = pd.DataFrame({
        "feature": ALL_FEATURES,
        "gain": model.feature_importance("gain"),
        "split": model.feature_importance("split"),
    }).sort_values("gain", ascending=False)
    imp.to_csv(DATA / f"feature_importance_{name}.csv", index=False)
    return imp


def main():
    full = build_dataset()
    print(f"[INFO] 전체 {len(full):,} 행, 특성 {len(ALL_FEATURES)}개")

    # M1: 분류
    tr, te = split_for(full, "label_up_20")
    m_cls, auc = train_classifier(tr, te)
    feature_importance_save(m_cls, "auto_cls")
    (DATA / "model_auto_cls.txt").write_text(m_cls.model_to_string(), encoding="utf-8")

    # M2: 회귀
    tr2 = full[(full["date"] <= TRAIN_END) & full["fwd_ret"].notna()].dropna(subset=ALL_FEATURES)
    te2 = full[(full["date"] >= TEST_START) & full["fwd_ret"].notna()].dropna(subset=ALL_FEATURES)
    m_reg, rho, rmse = train_regressor(tr2, te2)
    imp_reg = feature_importance_save(m_reg, "auto_reg")
    (DATA / "model_auto_reg.txt").write_text(m_reg.model_to_string(), encoding="utf-8")

    # 종목별 예측
    tickers = pd.read_excel(DATA / "tickers.xlsx")
    pred = predict_all(full, m_cls, m_reg, tickers)

    # 추천 분포
    rec_counts = pred["추천"].value_counts()
    print("\n[추천 분포]\n" + rec_counts.to_string())

    # Top 20 by 예상변동률
    print("\n[예상 상승률 Top 20]")
    print(pred.head(20).to_string(index=False))

    print("\n[예상 하락률 Top 20]")
    print(pred.tail(20).to_string(index=False))

    print("\n[Feature importance Top 10 - 회귀모델]")
    print(imp_reg.head(10).to_string(index=False))

    # 요약 메타
    meta = {
        "model": ["M1_분류", "M2_회귀"],
        "metric": [f"valid_auc={auc:.4f}", f"spearman={rho:.4f} rmse={rmse:.4f}"],
        "best_iteration": [m_cls.best_iteration, m_reg.best_iteration],
        "max_rounds": [NUM_ROUNDS, NUM_ROUNDS],
    }
    pd.DataFrame(meta).to_csv(DATA / "auto_ml_summary.csv", index=False)
    print(f"\n[OK] 요약 저장: auto_ml_summary.csv")


if __name__ == "__main__":
    main()
