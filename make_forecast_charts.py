"""
종목별 장기 예측 차트 (charts_forecast/{ticker}.png).

레이아웃:
  좌측 (3 칸): 가격 차트 (전체기간) + MA + RSI
  우측 (1 칸): 60/120/240일 상승확률 막대 + 예상 변동률 + 추천
"""

from __future__ import annotations

import pathlib
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OHLCV = DATA / "ohlcv"
CHARTS = ROOT / "charts_forecast"
CHARTS.mkdir(exist_ok=True)

for f in ("Malgun Gothic", "NanumGothic", "Gulim"):
    if any(f in n.name for n in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break
plt.rcParams["axes.unicode_minus"] = False


def rsi(c: pd.Series, period: int = 14):
    d = c.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = (-d.clip(upper=0)).rolling(period).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def make_chart(row, current_price: int):
    ticker = row["종목코드"]; name = row["종목명"]; market = row["시장"]
    f = OHLCV / f"{ticker}.parquet"
    if not f.exists():
        return False
    df = pd.read_parquet(f).sort_values("date").reset_index(drop=True)
    if len(df) < 60:
        return False
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    df["ma120"] = df["close"].rolling(120).mean()
    df["ma252"] = df["close"].rolling(252).mean()
    df["rsi14"] = rsi(df["close"], 14)

    # forecast 데이터
    horizons = [60, 120, 240]
    probs = [row["60d_상승확률(%)"], row["120d_상승확률(%)"], row["240d_상승확률(%)"]]
    rets = [row["60d_예상변동률(%)"], row["120d_예상변동률(%)"], row["240d_예상변동률(%)"]]

    fig = plt.figure(figsize=(15, 7.5))
    gs = GridSpec(3, 4, height_ratios=[5, 1.2, 1.5], width_ratios=[3, 3, 3, 1.6], hspace=0.1, wspace=0.15)

    axp = fig.add_subplot(gs[0, :3])
    axv = fig.add_subplot(gs[1, :3], sharex=axp)
    axr = fig.add_subplot(gs[2, :3], sharex=axp)
    axfc = fig.add_subplot(gs[:, 3])

    # 가격
    axp.plot(df["date"], df["close"], color="#1f77b4", lw=0.8, label="종가")
    axp.plot(df["date"], df["ma20"], color="#ff7f0e", lw=0.8, label="MA20", alpha=0.85)
    axp.plot(df["date"], df["ma60"], color="#2ca02c", lw=0.8, label="MA60", alpha=0.85)
    axp.plot(df["date"], df["ma120"], color="#9467bd", lw=0.8, label="MA120", alpha=0.85)
    axp.plot(df["date"], df["ma252"], color="#8c564b", lw=0.9, label="MA252", alpha=0.9)

    # 미래 예측 fan-out
    last_date = df["date"].iloc[-1]
    last_close = df["close"].iloc[-1]
    for h, ret in zip(horizons, rets):
        future_date = last_date + pd.Timedelta(days=int(h * 1.4))  # 영업일 → 달력
        future_price = last_close * (1 + ret / 100)
        axp.plot([last_date, future_date], [last_close, future_price],
                 color="#d62728" if ret >= 0 else "#1a7f37", lw=2.0, ls="--", alpha=0.7)
        axp.scatter([future_date], [future_price],
                    color="#d62728" if ret >= 0 else "#1a7f37", s=60, zorder=5)
        axp.annotate(f"{h}d {ret:+.1f}%",
                     xy=(future_date, future_price),
                     xytext=(5, 0), textcoords="offset points",
                     fontsize=9, fontweight="bold",
                     color="#d62728" if ret >= 0 else "#1a7f37")

    axp.set_title(f"{name} ({ticker}, {market})  {df['date'].min().date()} ~ {df['date'].max().date()}  /  현재 {int(last_close):,}원")
    axp.legend(loc="upper left", fontsize=8, ncol=5)
    axp.grid(alpha=0.3)

    # 거래량
    axv.bar(df["date"], df["volume"], color="#888", width=1.0)
    axv.set_ylabel("거래량", fontsize=8); axv.grid(alpha=0.3)
    plt.setp(axv.get_xticklabels(), visible=False); plt.setp(axp.get_xticklabels(), visible=False)

    # RSI
    axr.plot(df["date"], df["rsi14"], color="#9467bd", lw=0.8)
    axr.axhline(70, color="r", lw=0.5, ls="--", alpha=0.6); axr.axhline(30, color="g", lw=0.5, ls="--", alpha=0.6)
    axr.set_ylim(0, 100); axr.set_ylabel("RSI14", fontsize=8); axr.grid(alpha=0.3)

    # ===== 우측 forecast 패널 =====
    axfc.set_xlim(0, 100); axfc.set_ylim(-0.5, 4.5); axfc.invert_yaxis()
    axfc.axis("off")

    # 추천 박스
    rec = row["추천"]
    rec_color = {"★강한매수": "#b71c1c", "매수": "#d62728",
                 "관망": "#888", "매도": "#1a7f37", "★강한매도": "#0d3d1a"}.get(rec, "#888")
    axfc.text(50, 0, f"추천\n{rec}", ha="center", va="center", fontsize=14, fontweight="bold",
              color="white",
              bbox=dict(boxstyle="round,pad=0.6", fc=rec_color, ec="none"))

    # 종합점수 / 백분위
    axfc.text(50, 1.0, f"종합점수: {row['종합점수']:.2f}\n시장 상위 {row['시장내_상위_백분위(%)']:.1f}%",
              ha="center", va="center", fontsize=9.5,
              bbox=dict(boxstyle="round,pad=0.4", fc="#f0f0f0", ec="#999"))

    # 막대그래프: 상승확률
    axfc.text(50, 1.9, "상승확률(%)", ha="center", va="center", fontsize=9, fontweight="bold")
    bar_y = [2.4, 3.0, 3.6]
    bar_h = 0.3
    for y, h, prob, ret in zip(bar_y, horizons, probs, rets):
        prob_clip = max(0, min(100, prob))
        # 배경 막대 (흐림)
        axfc.add_patch(plt.Rectangle((10, y - bar_h/2), 80, bar_h, fc="#e0e0e0", ec="none"))
        # 실제 확률 막대
        col = "#d62728" if prob_clip > 25 else ("#999" if prob_clip > 20 else "#1a7f37")
        axfc.add_patch(plt.Rectangle((10, y - bar_h/2), prob_clip * 0.8, bar_h, fc=col, ec="none"))
        axfc.text(5, y, f"{h}d", ha="right", va="center", fontsize=8.5, fontweight="bold")
        axfc.text(95, y, f"{prob:.1f}%\n{ret:+.1f}%", ha="right", va="center", fontsize=7.5)

    # 20% 기준선 표시
    axfc.axvline(10 + 20 * 0.8, color="black", lw=0.5, ls=":", alpha=0.5)
    axfc.text(10 + 20 * 0.8, 2.05, "20%", ha="center", va="bottom", fontsize=7, color="gray")

    fig.suptitle(f"{name} ({ticker}) 장기 예측", fontsize=12, y=0.99)
    fig.tight_layout()
    fig.savefig(CHARTS / f"{ticker}.png", dpi=85, bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    pred = pd.read_excel(DATA / "predictions_multi.xlsx")
    print(f"[INFO] 차트 생성 ({len(pred)} 종목)")
    t0 = time.time()
    ok = 0
    for i, row in enumerate(pred.itertuples(index=False), 1):
        d = dict(zip(pred.columns, row))
        try:
            if make_chart(d, d["현재가"]):
                ok += 1
        except Exception as e:
            print(f"  {d['종목코드']} 실패: {e}")
        if i % 200 == 0:
            print(f"  {i}/{len(pred)}  ({time.time()-t0:.0f}s)")
    print(f"[OK] {ok}장 저장 → {CHARTS}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
