"""
다기간(20일 / 60일 / 120일 / 240일) 상위 20% 분류기 + 예상 변동률 회귀.

산출물:
  data/predictions_multi.xlsx  -- 종목별 4-horizon 예측 통합 테이블
  data/model_multi_{h}d_cls.txt / _reg.txt
  data/multi_summary.csv
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
FEATURES_IN = DATA / "features_upside.parquet"

HORIZONS = [20, 60, 120, 240]
SCORE_HORIZONS = [60, 120, 240]  # 종합점수/추천은 장기 horizon만 사용
NUM_ROUNDS = 1000
EARLY_STOP = 50

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


def cb_progress(every=100):
    last = [0]
    def cb(env):
        i = env.iteration + 1
        if i - last[0] >= every or i == 1:
            msg = " ".join(f"{n}_{m}={v:.4f}" for (n, m, v, _) in env.evaluation_result_list)
            print(f"  round {i:4d}: {msg}")
            last[0] = i
    return cb


def make_horizon(full: pd.DataFrame, h: int) -> pd.DataFrame:
    print(f"\n[INFO] {h}일 forward / 상위20% 라벨 계산")
    full = full.sort_values(["ticker", "date"]).reset_index(drop=True)
    full[f"fwd_{h}"] = full.groupby("ticker")["close"].shift(-h) / full["close"] - 1
    full[f"label_topq_{h}"] = (
        full.groupby("date")[f"fwd_{h}"].rank(method="first", pct=True) > 0.8
    ).astype("Int8")
    full.loc[full[f"fwd_{h}"].isna(), f"label_topq_{h}"] = pd.NA
    return full


def split_for_horizon(full: pd.DataFrame, h: int):
    """h일 forward라 train_end는 today - h일 - 60일 여유."""
    today = full["date"].max()
    train_end = today - pd.Timedelta(days=int(h * 1.5))  # 영업일 약 70% → 여유
    test_start = pd.Timestamp("2025-01-01")
    base = full.dropna(subset=ALL_FEATURES)
    tr = base[(base["date"] <= train_end) & base[f"label_topq_{h}"].notna()]
    te = base[(base["date"] >= test_start) & base[f"label_topq_{h}"].notna()]
    return tr, te, train_end


def train_h(full: pd.DataFrame, h: int):
    full = make_horizon(full, h)
    tr, te, te_end = split_for_horizon(full, h)
    print(f"[INFO] h={h}d : train≤{te_end.date()} {len(tr):,} / test {len(te):,}")
    if len(te) < 1000:
        print(f"[WARN] {h}일 테스트셋 너무 작음 ({len(te)}) — 학습은 진행")

    # 분류기
    p = {
        "objective": "binary", "metric": ["auc", "binary_logloss"],
        "learning_rate": 0.03, "num_leaves": 63, "min_data_in_leaf": 200,
        "feature_fraction": 0.85, "bagging_fraction": 0.85, "bagging_freq": 5,
        "is_unbalance": True, "verbose": -1, "seed": 42,
    }
    dtr = lgb.Dataset(tr[ALL_FEATURES].astype("float32"), label=tr[f"label_topq_{h}"].astype("int8"))
    valid_sets = [dtr]; valid_names = ["train"]
    if len(te) > 0:
        dte = lgb.Dataset(te[ALL_FEATURES].astype("float32"), label=te[f"label_topq_{h}"].astype("int8"), reference=dtr)
        valid_sets.append(dte); valid_names.append("valid")
    print(f"[CLS_{h}d] 학습")
    t0 = time.time()
    m_cls = lgb.train(
        p, dtr, num_boost_round=NUM_ROUNDS,
        valid_sets=valid_sets, valid_names=valid_names,
        callbacks=[lgb.early_stopping(EARLY_STOP, verbose=True), cb_progress(100)],
    )
    auc = np.nan
    if len(te) > 0:
        pp = m_cls.predict(te[ALL_FEATURES].astype("float32"))
        auc = roc_auc_score(te[f"label_topq_{h}"].astype(int), pp)
    print(f"[CLS_{h}d] best_iter={m_cls.best_iteration}, valid_auc={auc:.4f}, {time.time()-t0:.0f}s")

    # 회귀기 (예상 변동률용)
    pr = {
        "objective": "regression", "metric": "rmse",
        "learning_rate": 0.03, "num_leaves": 63, "min_data_in_leaf": 200,
        "feature_fraction": 0.85, "bagging_fraction": 0.85, "bagging_freq": 5,
        "verbose": -1, "seed": 42,
    }
    tr_r = full[(full["date"] <= te_end) & full[f"fwd_{h}"].notna()].dropna(subset=ALL_FEATURES)
    te_r = full[(full["date"] >= pd.Timestamp("2025-01-01")) & full[f"fwd_{h}"].notna()].dropna(subset=ALL_FEATURES)
    dtr_r = lgb.Dataset(tr_r[ALL_FEATURES].astype("float32"), label=tr_r[f"fwd_{h}"].astype("float32"))
    valid_sets_r = [dtr_r]; valid_names_r = ["train"]
    if len(te_r) > 0:
        dte_r = lgb.Dataset(te_r[ALL_FEATURES].astype("float32"), label=te_r[f"fwd_{h}"].astype("float32"), reference=dtr_r)
        valid_sets_r.append(dte_r); valid_names_r.append("valid")
    print(f"[REG_{h}d] 학습")
    t0 = time.time()
    m_reg = lgb.train(
        pr, dtr_r, num_boost_round=NUM_ROUNDS,
        valid_sets=valid_sets_r, valid_names=valid_names_r,
        callbacks=[lgb.early_stopping(EARLY_STOP, verbose=True), cb_progress(100)],
    )
    rho = np.nan; rmse = np.nan
    if len(te_r) > 0:
        ppr = m_reg.predict(te_r[ALL_FEATURES].astype("float32"))
        rho, _ = spearmanr(ppr, te_r[f"fwd_{h}"].astype(float))
        rmse = float(np.sqrt(((ppr - te_r[f"fwd_{h}"].astype(float).values) ** 2).mean()))
    print(f"[REG_{h}d] best_iter={m_reg.best_iteration}, spearman={rho:.4f}, rmse={rmse:.4f}, {time.time()-t0:.0f}s")

    (DATA / f"model_multi_{h}d_cls.txt").write_text(m_cls.model_to_string(), encoding="utf-8")
    (DATA / f"model_multi_{h}d_reg.txt").write_text(m_reg.model_to_string(), encoding="utf-8")
    return m_cls, m_reg, auc, rho, rmse


def predict_all(full: pd.DataFrame, models: dict, tickers: pd.DataFrame) -> pd.DataFrame:
    base = full.dropna(subset=ALL_FEATURES)
    latest = base.sort_values("date").groupby("ticker", as_index=False).tail(1).copy()
    X = latest[ALL_FEATURES].astype("float32")

    out = pd.DataFrame({
        "ticker": latest["ticker"].values,
        "기준일": latest["date"].dt.strftime("%Y-%m-%d").values,
        "현재가": latest["close"].values.astype(float).round(0).astype(int),
    })

    z_scores = []
    for h in HORIZONS:
        m_cls, m_reg = models[h]
        p_cls = m_cls.predict(X)
        p_reg = m_reg.predict(X)
        out[f"{h}d_상승확률(%)"] = (p_cls * 100).round(2)
        out[f"{h}d_예상변동률(%)"] = (p_reg * 100).round(2)
        # z-score for 종합점수 — 장기 horizon만 반영
        if h in SCORE_HORIZONS:
            s = np.std(p_cls)
            z_scores.append((p_cls - np.mean(p_cls)) / (s if s > 0 else 1))

    out["종합점수"] = np.mean(z_scores, axis=0).round(3)
    out["시장내_상위_백분위(%)"] = ((1 - out["종합점수"].rank(pct=True)) * 100).round(1)

    def rec(score, p60, p120, p240):
        # 3개 horizon 모두 상위 20% 확률이 평균이상이면 강한매수
        avg_prob = (p60 + p120 + p240) / 3
        if score > 1.0 and avg_prob > 25:
            return "★강한매수"
        if score > 0.5:
            return "매수"
        if score < -1.0:
            return "★강한매도"
        if score < -0.5:
            return "매도"
        return "관망"

    out["추천"] = [
        rec(s, r[0], r[1], r[2])
        for s, r in zip(out["종합점수"],
                        zip(out["60d_상승확률(%)"], out["120d_상승확률(%)"], out["240d_상승확률(%)"]))
    ]

    out = out.merge(tickers[["ticker", "name", "market"]], on="ticker", how="left").rename(
        columns={"ticker": "종목코드", "name": "종목명", "market": "시장"}
    )
    cols = ["종목코드", "종목명", "시장", "기준일", "현재가",
            "20d_상승확률(%)", "20d_예상변동률(%)",
            "60d_상승확률(%)", "60d_예상변동률(%)",
            "120d_상승확률(%)", "120d_예상변동률(%)",
            "240d_상승확률(%)", "240d_예상변동률(%)",
            "종합점수", "시장내_상위_백분위(%)", "추천"]
    out = out[cols].sort_values("종합점수", ascending=False).reset_index(drop=True)
    out.to_excel(DATA / "predictions_multi.xlsx", index=False)
    print(f"\n[OK] predictions_multi.xlsx ({len(out)} 종목)")
    return out


def main():
    if not FEATURES_IN.exists():
        print(f"[ERROR] {FEATURES_IN} 없음. auto_ml.py 먼저 실행.")
        sys.exit(1)
    print(f"[INFO] 특성 로드: {FEATURES_IN}")
    full = pd.read_parquet(FEATURES_IN)
    print(f"[INFO] 전체 {len(full):,} 행")

    models = {}
    summary = []
    for h in HORIZONS:
        m_cls, m_reg, auc, rho, rmse = train_h(full, h)
        models[h] = (m_cls, m_reg)
        summary.append({"horizon_d": h, "valid_auc": auc, "spearman": rho, "rmse": rmse,
                        "best_iter_cls": m_cls.best_iteration,
                        "best_iter_reg": m_reg.best_iteration})

    pd.DataFrame(summary).to_csv(DATA / "multi_summary.csv", index=False)
    print("\n[다기간 모델 성능]")
    print(pd.DataFrame(summary).to_string(index=False))

    tickers = pd.read_excel(DATA / "tickers.xlsx")
    pred = predict_all(full, models, tickers)

    print("\n[Top 20 종목 - 종합점수 기준]")
    print(pred.head(20).to_string(index=False))
    print("\n[추천 분포]\n" + pred["추천"].value_counts().to_string())


if __name__ == "__main__":
    main()
