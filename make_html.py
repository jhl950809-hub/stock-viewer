"""
HTML 대시보드 (모바일 반응형).
- predictions_multi.xlsx 데이터를 JSON으로 임베드
- 데스크탑: 좌-테이블 / 우-차트
- 모바일: 상-테이블 / 하-차트, 필터 sticky, 가로 스크롤
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

pred = pd.read_excel(DATA / "predictions_multi.xlsx")

records = []
for r in pred.itertuples(index=False):
    d = dict(zip(pred.columns, r))
    records.append({
        "code": str(d["종목코드"]).zfill(6),
        "name": str(d["종목명"]),
        "market": str(d["시장"]),
        "date": str(d["기준일"]),
        "price": int(d["현재가"]),
        "p20": float(d["20d_상승확률(%)"]),
        "r20": float(d["20d_예상변동률(%)"]),
        "p60": float(d["60d_상승확률(%)"]),
        "r60": float(d["60d_예상변동률(%)"]),
        "p120": float(d["120d_상승확률(%)"]),
        "r120": float(d["120d_예상변동률(%)"]),
        "p240": float(d["240d_상승확률(%)"]),
        "r240": float(d["240d_예상변동률(%)"]),
        "score": float(d["종합점수"]),
        "pct": float(d["시장내_상위_백분위(%)"]),
        "rec": str(d["추천"]),
    })

data_json = json.dumps(records, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=2">
<meta name="theme-color" content="#1f2937">
<title>한국주식 장기 예측</title>
<style>
  *, *::before, *::after { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; background: #f0f2f5; color: #1e293b; font-size: 14px; line-height: 1.5; }
  header { background: linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%); color: white; padding: 0 20px; height: 58px; position: sticky; top: 0; z-index: 10; display: flex; justify-content: space-between; align-items: center; gap: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.25); border-bottom: 1px solid rgba(255,255,255,0.08); }
  .header-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .header-logo { font-size: 22px; flex-shrink: 0; }
  h1 { margin: 0; font-size: 16px; font-weight: 700; letter-spacing: -0.3px; white-space: nowrap; }
  .sub { color: #93c5fd; font-size: 10.5px; margin-top: 1px; }
  .head-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; flex-shrink: 0; }
  .data-badge { background: rgba(255,255,255,0.1); color: #bfdbfe; padding: 5px 11px; border-radius: 20px; font-size: 11px; font-weight: 600; border: 1px solid rgba(255,255,255,0.15); line-height: 1.4; }
  .data-badge b { color: #fde68a; font-size: 12px; }
  .data-badge.stale { background: rgba(239,68,68,0.2); border-color: rgba(239,68,68,0.4); color: #fecaca; }
  .data-badge.stale b { color: #fca5a5; }
  .btn { background: rgba(255,255,255,0.12); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.2); padding: 7px 13px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; transition: background 0.15s, transform 0.1s; white-space: nowrap; }
  .btn:hover { background: rgba(255,255,255,0.22); transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }
  .btn-accent { background: #3b82f6; border-color: #2563eb; color: #fff; }
  .btn-accent:hover { background: #2563eb; }
  .btn-warn { background: #f59e0b; border-color: #d97706; color: #fff; }
  .btn-warn:hover { background: #d97706; }
  .btn[disabled] { opacity: 0.45; cursor: not-allowed; transform: none !important; }
  .container { max-width: 1540px; margin: 0 auto; padding: 16px; display: grid; grid-template-columns: minmax(0,1.05fr) minmax(0,0.95fr); gap: 16px; }
  @media (max-width: 1100px) { .container { grid-template-columns: 1fr; } }
  .panel { background: #ffffff; border-radius: 14px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06),0 4px 16px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.04); }
  .controls { display: flex; gap: 7px; margin-bottom: 10px; flex-wrap: wrap; position: sticky; top: 0; background: #fff; z-index: 2; padding: 10px 0 8px; border-bottom: 1px solid #f1f5f9; }
  .controls input, .controls select { padding: 8px 11px; border: 1.5px solid #e2e8f0; border-radius: 8px; font-size: 13px; min-height: 38px; color: #1e293b; background: #f8fafc; transition: border-color 0.15s,box-shadow 0.15s; outline: none; }
  .controls input:focus, .controls select:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.12); background: #fff; }
  .controls input { flex: 1; min-width: 130px; }
  .controls input.price { flex: 0 0 105px; min-width: 85px; text-align: right; }
  .controls .price-sep { display: flex; align-items: center; color: #94a3b8; font-size: 12px; padding: 0 1px; }
  .stats { font-size: 11px; color: #94a3b8; margin-bottom: 8px; font-weight: 500; }
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; max-height: 65vh; overflow-y: auto; border-radius: 8px; border: 1px solid #f1f5f9; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 720px; }
  th, td { padding: 9px 7px; text-align: right; white-space: nowrap; }
  th { background: #f8fafc; font-weight: 700; cursor: pointer; user-select: none; position: sticky; top: 0; z-index: 1; font-size: 10.5px; color: #64748b; letter-spacing: 0.3px; border-bottom: 2px solid #e2e8f0; text-transform: uppercase; }
  th:hover { background: #f1f5f9; color: #1e293b; }
  th.asc::after { content: " ▲"; color: #3b82f6; }
  th.desc::after { content: " ▼"; color: #3b82f6; }
  td { border-bottom: 1px solid #f8fafc; }
  tbody tr:nth-child(even) td { background: #fafafa; }
  td.code, td.name, td.market, th.code, th.name, th.market { text-align: left; }
  td.code { font-family: "SF Mono",Menlo,monospace; font-size: 10.5px; color: #94a3b8; }
  td.name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; font-weight: 500; color: #1e293b; }
  td.market { font-size: 10px; color: #64748b; }
  tbody tr { cursor: pointer; transition: background 0.1s; }
  tbody tr:hover td { background: #eff6ff !important; }
  tbody tr.selected td { background: #dbeafe !important; }
  tbody tr.selected td.name { color: #1d4ed8; font-weight: 700; }
  tbody tr:active td { background: #bfdbfe !important; }
  .pos { color: #dc2626; font-weight: 700; }
  .neg { color: #16a34a; font-weight: 700; }
  .rec { padding: 3px 9px; border-radius: 20px; font-size: 10px; font-weight: 700; color: white; display: inline-block; white-space: nowrap; letter-spacing: 0.3px; }
  .rec-strong-buy { background: linear-gradient(135deg,#b91c1c,#991b1b); box-shadow: 0 1px 4px rgba(185,28,28,0.4); }
  .rec-buy { background: linear-gradient(135deg,#dc2626,#b91c1c); }
  .rec-hold { background: #94a3b8; }
  .rec-sell { background: linear-gradient(135deg,#16a34a,#15803d); }
  .rec-strong-sell { background: linear-gradient(135deg,#15803d,#166534); box-shadow: 0 1px 4px rgba(22,101,52,0.4); }
  .preview { text-align: center; min-height: 200px; }
  .preview img { max-width: 100%; height: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
  .preview-title { font-size: 17px; font-weight: 800; margin-bottom: 8px; color: #0f172a; letter-spacing: -0.4px; }
  .preview-meta { font-size: 12px; color: #475569; margin-bottom: 12px; line-height: 1.8; }
  .preview-meta .stat { display: inline-block; padding: 3px 9px; background: #f1f5f9; border-radius: 20px; margin: 2px; font-size: 11px; font-weight: 500; color: #475569; border: 1px solid #e2e8f0; }
  .empty { text-align: center; color: #94a3b8; padding: 60px 16px; font-size: 13px; }
  .empty-icon { font-size: 36px; margin-bottom: 10px; opacity: 0.5; }
  .legend { font-size: 10px; color: #94a3b8; margin-top: 6px; line-height: 1.9; }
  .pill { display: inline-block; padding: 2px 6px; border-radius: 4px; margin-right: 3px; font-size: 9.5px; }
  .modal-mask { display: none; position: fixed; inset: 0; background: rgba(15,23,42,0.6); backdrop-filter: blur(3px); z-index: 100; align-items: flex-start; justify-content: center; padding: 28px 16px; overflow-y: auto; }
  .modal-mask.open { display: flex; }
  .modal { background: #fff; border-radius: 16px; max-width: 840px; width: 100%; padding: 22px 26px; box-shadow: 0 20px 60px rgba(0,0,0,0.25),0 4px 16px rgba(0,0,0,0.1); animation: modalIn 0.2s ease; }
  @keyframes modalIn { from{opacity:0;transform:translateY(-12px);}to{opacity:1;transform:translateY(0);} }
  .modal h2 { margin: 0 0 5px 0; font-size: 19px; font-weight: 800; color: #0f172a; }
  .modal .lead { color: #64748b; font-size: 12.5px; margin-bottom: 16px; }
  .modal h3 { margin: 20px 0 9px 0; font-size: 13px; color: #1e293b; border-left: 4px solid #3b82f6; padding-left: 10px; font-weight: 700; }
  .modal p, .modal li { font-size: 12.5px; line-height: 1.7; color: #334155; }
  .modal .close { float: right; background: #f1f5f9; border: none; font-size: 18px; cursor: pointer; color: #64748b; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
  .modal .close:hover { background: #e2e8f0; color: #1e293b; }
  .modal code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 11.5px; color: #1d4ed8; }
  .modal .formula { background: linear-gradient(135deg,#eff6ff,#dbeafe); border-left: 3px solid #3b82f6; padding: 13px 16px; margin: 10px 0; font-family: "SF Mono",Menlo,monospace; font-size: 12.5px; border-radius: 8px; line-height: 1.9; color: #1e3a8a; }
  .modal .note { background: #fff7ed; border-left: 3px solid #f97316; padding: 11px 14px; font-size: 12px; border-radius: 8px; color: #7c2d12; }
  .rec-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(148px,1fr)); gap: 10px; margin: 10px 0; }
  .rec-card { border-radius: 12px; padding: 13px 14px 15px; color: #fff; box-shadow: 0 3px 10px rgba(0,0,0,0.15); }
  .rec-card .rec-tag { display: inline-block; background: rgba(255,255,255,0.2); padding: 3px 9px; border-radius: 12px; font-size: 10.5px; font-weight: 700; margin-bottom: 8px; }
  .rec-card .rec-cond { font-size: 13px; font-weight: 700; margin-bottom: 5px; line-height: 1.4; }
  .rec-card .rec-desc { font-size: 11px; opacity: 0.9; line-height: 1.5; }
  .rec-card .rec-share { font-size: 10px; opacity: 0.8; margin-top: 7px; }
  .zbar-wrap { background: #f8fafc; border-radius: 10px; padding: 14px 16px 12px; margin: 8px 0 12px; border: 1px solid #e2e8f0; }
  .zbar { position: relative; height: 26px; background: linear-gradient(to right,#166534 0%,#166534 8%,#16a34a 8%,#16a34a 25%,#94a3b8 25%,#94a3b8 75%,#dc2626 75%,#dc2626 92%,#991b1b 92%,#991b1b 100%); border-radius: 8px; }
  .zbar-labels { position: relative; height: 18px; font-size: 10px; color: #64748b; margin-top: 5px; }
  .zbar-labels span { position: absolute; transform: translateX(-50%); }
  .zbar-ticks { position: relative; height: 14px; font-size: 10.5px; color: #334155; margin-top: 2px; }
  .zbar-ticks span { position: absolute; transform: translateX(-50%); font-weight: 700; }
  .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .info-card { background: #f8fafc; border-radius: 8px; padding: 11px 13px; border: 1px solid #e2e8f0; }
  .info-card b { display: block; font-size: 11.5px; color: #1d4ed8; margin-bottom: 4px; font-weight: 700; }
  .info-card span { font-size: 11px; color: #475569; line-height: 1.55; }
  .check-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; margin: 6px 0; }
  .check-row { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; padding: 7px 9px; border-radius: 7px; transition: background 0.15s; }
  .check-row:hover { background: #f1f5f9; }
  .check-row input { margin-top: 2px; flex-shrink: 0; accent-color: #3b82f6; }
  .check-row .icon { font-size: 14px; flex-shrink: 0; }
  .refresh-hero { background: linear-gradient(135deg,#1e3a8a 0%,#1d4ed8 60%,#2563eb 100%); color: #fff; border-radius: 12px; padding: 20px 22px; margin: 6px 0 16px; box-shadow: 0 4px 20px rgba(37,99,235,0.35); }
  .refresh-hero .last { font-size: 12px; opacity: 0.85; margin-bottom: 5px; }
  .refresh-hero .last b { color: #fde68a; }
  .big-refresh-btn { display: block; width: 100%; background: #fff; color: #1d4ed8; border: 0; padding: 15px; border-radius: 10px; font-size: 15px; font-weight: 800; cursor: pointer; margin-top: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.18); transition: transform 0.12s,box-shadow 0.12s; letter-spacing: -0.2px; }
  .big-refresh-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.22); }
  .big-refresh-btn:active { transform: translateY(0); }
  .big-refresh-btn:disabled { opacity: 0.65; cursor: progress; transform: none; }
  .refresh-status { background: #0f172a; color: #94a3b8; border-radius: 8px; padding: 12px 14px; font-family: "SF Mono",Menlo,"Consolas",monospace; font-size: 11px; max-height: 280px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; margin-top: 12px; display: none; border: 1px solid #1e293b; line-height: 1.6; }
  .refresh-status.visible { display: block; }
  .pulse { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 0 rgba(34,197,94,0.7); animation: pulse 1.4s infinite; vertical-align: middle; margin-right: 6px; }
  @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(34,197,94,0.6);}70%{box-shadow:0 0 0 10px rgba(34,197,94,0);}100%{box-shadow:0 0 0 0 rgba(34,197,94,0);} }
  .step-list { display: grid; grid-template-columns: 1fr; gap: 7px; }
  .step-list .step { display: flex; align-items: center; gap: 11px; background: #f8fafc; border-radius: 8px; padding: 9px 13px; font-size: 12.5px; border: 1px solid #e2e8f0; }
  .step-list .step .num { background: linear-gradient(135deg,#2563eb,#1d4ed8); color: #fff; width: 24px; height: 24px; border-radius: 50%; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 6px rgba(37,99,235,0.4); }
  .chart-wrap { position: relative; width: 100%; height: 320px; margin-top: 10px; border-radius: 8px; overflow: hidden; }
  .chart-wrap.rsi { height: 88px; margin-top: 5px; }
  .chart-wrap.cci { height: 88px; margin-top: 5px; }
  .chart-loading { color: #94a3b8; padding: 30px; font-size: 12px; text-align: center; }
  .chart-error { color: #dc2626; padding: 16px; font-size: 12px; background: #fef2f2; border-radius: 8px; margin-top: 8px; border: 1px solid #fecaca; }
  .table-wrap::-webkit-scrollbar,.refresh-status::-webkit-scrollbar { height: 6px; width: 6px; }
  .table-wrap::-webkit-scrollbar-track { background: #f8fafc; }
  .table-wrap::-webkit-scrollbar-thumb,.refresh-status::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
  .table-wrap::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
  @media (max-width: 1100px) { header { height: auto; padding: 10px 14px; } .sub { display: none; } }
  @media (max-width: 600px) {
    header { padding: 9px 12px; flex-wrap: wrap; height: auto; }
    h1 { font-size: 14px; }
    .head-actions .btn { padding: 6px 9px; font-size: 11px; }
    .container { padding: 10px; gap: 10px; }
    .panel { padding: 10px; border-radius: 10px; }
    .controls input, .controls select { font-size: 16px; }
    .table-wrap { max-height: 55vh; border-radius: 6px; }
    table { font-size: 11px; min-width: 680px; }
    th { font-size: 10px; }
    th, td { padding: 7px 5px; }
    .preview { padding: 2px; }
    .preview-title { font-size: 15px; }
    .modal-mask { padding: 10px; }
    .modal { padding: 16px 14px; border-radius: 12px; }
    .chart-wrap { height: 240px; }
    .chart-wrap.rsi { height: 70px; }
    .chart-wrap.cci { height: 70px; }
  }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
<header>
  <div class="header-left">
    <span class="header-logo">📈</span>
    <div>
      <h1>한국주식 장기 예측 대시보드</h1>
      <div class="sub">KOSPI · KOSDAQ 전 종목 &nbsp;|&nbsp; 20 / 60 / 120 / 240일 · LightGBM</div>
    </div>
  </div>
  <div class="head-actions">
    <div class="data-badge" id="dataBadge" title="마지막 데이터 기준일">
      📅 <b id="dataDate">—</b> <span id="dataAge" style="font-weight:500;opacity:0.8;"></span>
    </div>
    <button class="btn btn-accent" onclick="document.getElementById('mdScore').classList.add('open')">📊 기준표</button>
    <button class="btn btn-warn" onclick="document.getElementById('mdRefresh').classList.add('open')">🔄 데이터 갱신</button>
  </div>
</header>

<!-- ============== 점수 기준표 모달 ============== -->
<div class="modal-mask" id="mdScore" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal">
    <button class="close" onclick="document.getElementById('mdScore').classList.remove('open')">×</button>
    <h2>📊 점수 기준표</h2>
    <p class="lead">종합점수와 추천이 어떻게 계산되는지 한눈에 보기 — 그리고 매매 전 사람이 추가로 확인해야 할 요소들.</p>

    <h3>① 종합점수 = 상승확률을 시장 분포로 표준화한 z-score 평균</h3>
    <div class="formula">
      z<sub>h</sub> = ( P<sub>h</sub> − μ<sub>h</sub> ) / σ<sub>h</sub> &nbsp; ← 60·120·240일 각각<br>
      <b>종합점수 = ( z<sub>60</sub> + z<sub>120</sub> + z<sub>240</sub> ) / 3</b>
    </div>

    <div class="zbar-wrap">
      <div style="font-size:11.5px;color:#6b7280;margin-bottom:6px;">📏 종합점수 위치 → 추천 등급 (시각 분포)</div>
      <div class="zbar"></div>
      <div class="zbar-ticks">
        <span style="left:0%;">−2</span>
        <span style="left:25%;">−1</span>
        <span style="left:50%;">0</span>
        <span style="left:75%;">+1</span>
        <span style="left:100%;">+2</span>
      </div>
      <div class="zbar-labels">
        <span style="left:4%;color:#fff;background:#0d3d1a;padding:1px 4px;border-radius:3px;">★강매도</span>
        <span style="left:16%;color:#fff;background:#1a7f37;padding:1px 4px;border-radius:3px;">매도</span>
        <span style="left:50%;color:#fff;background:#6b7280;padding:1px 4px;border-radius:3px;">관망</span>
        <span style="left:84%;color:#fff;background:#d62728;padding:1px 4px;border-radius:3px;">매수</span>
        <span style="left:96%;color:#fff;background:#b71c1c;padding:1px 4px;border-radius:3px;">★강매수</span>
      </div>
    </div>

    <h3>② 추천 5등급 — 임계값 한 장 카드</h3>
    <div class="rec-grid">
      <div class="rec-card" style="background:#b71c1c;">
        <div class="rec-tag">★ 강한매수</div>
        <div class="rec-cond">점수 &gt; +1.0<br>&amp; 평균확률 &gt; 25%</div>
        <div class="rec-desc">3 기간 모두 일관 상위 — 두 조건 동시 충족</div>
        <div class="rec-share">≈ 시장 상위 5%</div>
      </div>
      <div class="rec-card" style="background:#d62728;">
        <div class="rec-tag">매수</div>
        <div class="rec-cond">점수 &gt; +0.5</div>
        <div class="rec-desc">시장 대비 양호한 상승확률</div>
        <div class="rec-share">≈ 시장 상위 30%</div>
      </div>
      <div class="rec-card" style="background:#6b7280;">
        <div class="rec-tag">관망</div>
        <div class="rec-cond">−0.5 ≤ 점수 ≤ +0.5</div>
        <div class="rec-desc">시장 평균 수준 — 신규 진입 보류 권장</div>
        <div class="rec-share">≈ 중간 40%</div>
      </div>
      <div class="rec-card" style="background:#1a7f37;">
        <div class="rec-tag">매도</div>
        <div class="rec-cond">점수 &lt; −0.5</div>
        <div class="rec-desc">시장 대비 약세 — 보유 시 비중 점검</div>
        <div class="rec-share">≈ 시장 하위 30%</div>
      </div>
      <div class="rec-card" style="background:#0d3d1a;">
        <div class="rec-tag">★ 강한매도</div>
        <div class="rec-cond">점수 &lt; −1.0</div>
        <div class="rec-desc">3 기간 모두 일관 하위</div>
        <div class="rec-share">≈ 시장 하위 16%</div>
      </div>
    </div>

    <h3>③ 표 컬럼이 의미하는 것</h3>
    <div class="info-grid">
      <div class="info-card"><b>60d / 120d / 240d ▲%</b><span>해당 기간 후 상위 20% 수익 그룹에 들 모델 추정 확률</span></div>
      <div class="info-card"><b>60d / 120d / 240d 예상</b><span>회귀 모델이 추정한 변동률(%) — 방향 참고용</span></div>
      <div class="info-card"><b>종합</b><span>위 z-score 평균. ±1 = 상위·하위 16%, ±2 = 2.3%</span></div>
      <div class="info-card"><b>시장 상위 %</b><span>전체 종목 중 분위 (1% = 최상위)</span></div>
    </div>

    <h3>④ 매매 전 ✅ 재확인 체크리스트 — 모델이 보지 못하는 요소</h3>
    <p style="color:#6b7280;font-size:11.5px;">모델은 가격·거래량 패턴만 학습합니다. 사람이 추가로 확인해야 합니다.</p>
    <div class="check-grid">
      <div class="check-row"><span class="icon">📑</span><input type="checkbox" id="ck1"><label for="ck1"><b>공시</b><br><span style="color:#6b7280;font-size:11px;">유상증자·CB/BW·주주 변동 (DART)</span></label></div>
      <div class="check-row"><span class="icon">📊</span><input type="checkbox" id="ck2"><label for="ck2"><b>실적 시즌</b><br><span style="color:#6b7280;font-size:11px;">발표일·컨센서스 상하향</span></label></div>
      <div class="check-row"><span class="icon">⚠️</span><input type="checkbox" id="ck3"><label for="ck3"><b>관리·정지·상폐</b><br><span style="color:#6b7280;font-size:11px;">한국거래소 공시 확인</span></label></div>
      <div class="check-row"><span class="icon">🏭</span><input type="checkbox" id="ck4"><label for="ck4"><b>업종 모멘텀</b><br><span style="color:#6b7280;font-size:11px;">업종 전체 vs 단일 종목 이슈</span></label></div>
      <div class="check-row"><span class="icon">🌐</span><input type="checkbox" id="ck5"><label for="ck5"><b>거시 변수</b><br><span style="color:#6b7280;font-size:11px;">환율·금리·FOMC·금통위</span></label></div>
      <div class="check-row"><span class="icon">📉</span><input type="checkbox" id="ck6"><label for="ck6"><b>수학 예측 일치도</b><br><span style="color:#6b7280;font-size:11px;">5가족·16변형 방향이 같은가</span></label></div>
      <div class="check-row"><span class="icon">💧</span><input type="checkbox" id="ck7"><label for="ck7"><b>유동성</b><br><span style="color:#6b7280;font-size:11px;">최근 20일 평균 거래대금</span></label></div>
      <div class="check-row"><span class="icon">🕐</span><input type="checkbox" id="ck8"><label for="ck8"><b>데이터 신선도</b><br><span style="color:#6b7280;font-size:11px;">기준일이 오래됐다면 🔄 갱신</span></label></div>
    </div>

    <div class="note" style="margin-top:14px;">
      <b>⚠ 주의 ─</b> 종합점수는 <b>시장 내 상대 순위</b>입니다. 시장 전체가 약세장이면 상위 종목조차 음(−) 수익을 낼 수 있습니다. 절대 수익률 보장이 아니라 <b>방향성·확률의 참고 자료</b>로 다루세요.
    </div>
  </div>
</div>

<!-- ============== 데이터 갱신 모달 (한 번 클릭 실행) ============== -->
<div class="modal-mask" id="mdRefresh" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal">
    <button class="close" onclick="document.getElementById('mdRefresh').classList.remove('open')">×</button>
    <h2>🔄 데이터 갱신</h2>
    <p class="lead">시세 다운로드 → 특성·모델 재학습 → HTML 재생성까지 한 번에 실행합니다 (차트는 viewer에서 인터랙티브로 렌더).</p>

    <div class="refresh-hero">
      <div class="last">📅 마지막 데이터 기준일 &nbsp; <b id="dataDate2">—</b> &nbsp; <span id="dataDate2Age" style="opacity:0.85;"></span></div>
      <div style="font-size:13px;margin-top:6px;">임베드 종목 수: <b id="dataCount">—</b></div>
      <button class="big-refresh-btn" id="btnGoRefresh" onclick="startRefresh()">🚀 지금 갱신 시작 (daily_run.bat)</button>
      <div style="font-size:11px;opacity:0.85;margin-top:8px;text-align:center;" id="modeHint">
        ※ 한 번 클릭 실행은 <code style="background:rgba(255,255,255,0.2);color:#fde68a;">viewer_open.bat</code> 으로 띄웠을 때만 동작합니다.
      </div>
    </div>

    <div class="refresh-status" id="refreshStatus"></div>

    <h3>실행되는 4단계</h3>
    <div class="step-list">
      <div class="step"><div class="num">1</div>증분 시세 다운로드 — <code>update_daily.py</code></div>
      <div class="step"><div class="num">2</div>특성 캐시 재계산 + 20d 자체학습 — <code>auto_ml.py</code></div>
      <div class="step"><div class="num">3</div>다기간 모델 재학습 + 예측 — <code>multi_horizon.py</code></div>
      <div class="step"><div class="num">4</div>HTML 대시보드 재생성 — <code>make_html.py</code></div>
    </div>

    <div class="note" style="margin-top:14px;">
      <b>한 번 클릭 실행 사용법</b><br>
      ① <code>viewer_open.bat</code> 더블클릭 → 로컬 서버 시작 + 브라우저 자동 오픈<br>
      ② 헤더의 <b>🔄 데이터 갱신</b> → <b>🚀 지금 갱신 시작</b> → 진행 로그 실시간 표시<br>
      ③ 완료되면 <b>새로고침(Ctrl+F5)</b> 으로 새 데이터 반영
    </div>
  </div>
</div>

<div class="container">
  <div class="panel">
    <div class="controls">
      <input id="search" placeholder="🔍 종목코드 또는 이름...">
      <select id="market">
        <option value="">전체</option>
        <option value="KOSPI">KOSPI</option>
        <option value="KOSDAQ">KOSDAQ</option>
      </select>
      <select id="rec">
        <option value="">전체 추천</option>
        <option value="★강한매수">★강한매수</option>
        <option value="매수">매수</option>
        <option value="관망">관망</option>
        <option value="매도">매도</option>
        <option value="★강한매도">★강한매도</option>
      </select>
      <input id="priceMin" class="price" type="number" inputmode="numeric" min="0" step="100" placeholder="최소가 ₩">
      <span class="price-sep">~</span>
      <input id="priceMax" class="price" type="number" inputmode="numeric" min="0" step="100" placeholder="최대가 ₩">
    </div>
    <div class="stats" id="stats"></div>
    <div class="table-wrap">
      <table id="tbl">
        <thead>
          <tr>
            <th class="code" data-key="code">코드</th>
            <th class="name" data-key="name">종목명</th>
            <th class="market" data-key="market">시장</th>
            <th data-key="price">현재가</th>
            <th data-key="p60">60d▲%</th>
            <th data-key="r60">60d예상</th>
            <th data-key="p120">120d▲%</th>
            <th data-key="r120">120d예상</th>
            <th data-key="p240">240d▲%</th>
            <th data-key="r240">240d예상</th>
            <th data-key="score" class="desc">종합</th>
            <th data-key="rec">추천</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <div class="legend">
      <span class="pill" style="background:#b71c1c;color:white;">★강한매수</span>
      <span class="pill" style="background:#d62728;color:white;">매수</span>
      <span class="pill" style="background:#6b7280;color:white;">관망</span>
      <span class="pill" style="background:#1a7f37;color:white;">매도</span>
      <span class="pill" style="background:#0d3d1a;color:white;">★강한매도</span>
      <br>📌 행 터치/클릭 → 차트 보기 · 컬럼 헤더 → 정렬
    </div>
  </div>

  <div class="panel preview" id="preview">
    <div class="empty">왼쪽(또는 위)에서 종목을 선택하세요.</div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;
let sortKey = "score";
let sortDir = "desc";

function fmtNum(n, digits=0) {
  if (n === null || n === undefined || isNaN(n)) return "";
  return Number(n).toLocaleString(undefined, {minimumFractionDigits: digits, maximumFractionDigits: digits});
}
function recClass(r) {
  return {"★강한매수":"rec-strong-buy","매수":"rec-buy","관망":"rec-hold",
          "매도":"rec-sell","★강한매도":"rec-strong-sell"}[r] || "rec-hold";
}

function render() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const mk = document.getElementById("market").value;
  const rk = document.getElementById("rec").value;
  const pMinRaw = document.getElementById("priceMin").value;
  const pMaxRaw = document.getElementById("priceMax").value;
  const pMin = pMinRaw === "" ? null : Number(pMinRaw);
  const pMax = pMaxRaw === "" ? null : Number(pMaxRaw);

  let rows = DATA.filter(d => {
    if (q && !(d.code.includes(q) || d.name.toLowerCase().includes(q))) return false;
    if (mk && d.market !== mk) return false;
    if (rk && d.rec !== rk) return false;
    if (pMin !== null && !Number.isNaN(pMin) && (d.price == null || d.price < pMin)) return false;
    if (pMax !== null && !Number.isNaN(pMax) && (d.price == null || d.price > pMax)) return false;
    return true;
  });

  rows.sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey];
    if (typeof av === "string") { av = av.toLowerCase(); bv = bv.toLowerCase(); }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";
  const max = Math.min(rows.length, 500);
  for (let i = 0; i < max; i++) {
    const d = rows[i];
    const tr = document.createElement("tr");
    tr.dataset.code = d.code;
    tr.innerHTML = `
      <td class="code">${d.code}</td>
      <td class="name">${d.name}</td>
      <td class="market">${d.market}</td>
      <td>${fmtNum(d.price)}</td>
      <td>${fmtNum(d.p60, 1)}</td>
      <td class="${d.r60 >= 0 ? 'pos' : 'neg'}">${d.r60 >= 0 ? '+' : ''}${fmtNum(d.r60, 1)}</td>
      <td>${fmtNum(d.p120, 1)}</td>
      <td class="${d.r120 >= 0 ? 'pos' : 'neg'}">${d.r120 >= 0 ? '+' : ''}${fmtNum(d.r120, 1)}</td>
      <td>${fmtNum(d.p240, 1)}</td>
      <td class="${d.r240 >= 0 ? 'pos' : 'neg'}">${d.r240 >= 0 ? '+' : ''}${fmtNum(d.r240, 1)}</td>
      <td>${fmtNum(d.score, 2)}</td>
      <td><span class="rec ${recClass(d.rec)}">${d.rec}</span></td>
    `;
    tr.addEventListener("click", () => showPreview(d));
    tbody.appendChild(tr);
  }
  document.getElementById("stats").textContent =
    `${rows.length.toLocaleString()}종목 · 표시 ${max} · ${sortKey} ${sortDir}`;

  document.querySelectorAll("th").forEach(th => {
    th.classList.remove("asc", "desc");
    if (th.dataset.key === sortKey) th.classList.add(sortDir);
  });
}

// z-점수 → 상승확률 (로지스틱 근사)
function normCDF(x) { return 1 / (1 + Math.exp(-1.7 * x)); }

function showPreview(d) {
  document.querySelectorAll("tbody tr").forEach(r => r.classList.remove("selected"));
  const target = document.querySelector(`tr[data-code="${d.code}"]`);
  if (target) target.classList.add("selected");

  const upProb = Math.round(normCDF(d.score) * 100);
  const probColor = upProb >= 65 ? "#b91c1c" : upProb >= 50 ? "#d97706" : upProb >= 35 ? "#4b5563" : "#166534";
  const probBg    = upProb >= 65 ? "#fef2f2" : upProb >= 50 ? "#fffbeb" : upProb >= 35 ? "#f9fafb" : "#f0fdf4";

  function horizonCard(label, ret) {
    const up = ret >= 0;
    const col = up ? "#b91c1c" : "#166534";
    const bg  = up ? "#fef2f2" : "#f0fdf4";
    return `<div style="flex:1;background:${bg};border-radius:8px;padding:8px 4px;text-align:center;min-width:0;">
      <div style="font-size:10px;color:#6b7280;margin-bottom:2px;">${label}</div>
      <div style="font-size:20px;color:${col};">${up ? "▲" : "▼"}</div>
      <div style="font-size:12px;font-weight:700;color:${col};">${ret >= 0 ? "+" : ""}${ret.toFixed(1)}%</div>
      <div style="font-size:10px;color:#9ca3af;">${up ? "상승" : "하락"} 예측</div>
    </div>`;
  }

  const html = `
    <div class="preview-title">${d.name} (${d.code}) · ${d.market}</div>
    <div class="preview-meta">
      <span class="stat">현재가 ${fmtNum(d.price)}원</span>
      <span class="stat">기준일 ${d.date}</span>
      <span class="stat">시장 상위 ${fmtNum(d.pct, 1)}%</span>
      <br>
      <span class="rec ${recClass(d.rec)}" style="font-size:13px;padding:5px 12px;">${d.rec}</span>
      <span class="stat">종합점수 ${fmtNum(d.score, 2)}</span>
    </div>
    <div style="background:${probBg};border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;margin-bottom:10px;">
      <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:8px;">🔮 AI 방향 예측 (시장대비 상승확률)</div>
      <div style="display:flex;gap:6px;margin-bottom:10px;">
        ${d.r20 != null ? horizonCard("20일", d.r20) : ""}
        ${horizonCard("60일", d.r60)}
        ${horizonCard("120일", d.r120)}
        ${horizonCard("240일", d.r240)}
      </div>
      <div style="font-size:11px;color:#6b7280;margin-bottom:4px;">종합 상승확률 (z-score → 정규분포)</div>
      <div style="display:flex;align-items:center;gap:8px;">
        <div style="flex:1;background:#e5e7eb;border-radius:6px;height:12px;overflow:hidden;">
          <div style="background:${probColor};height:12px;border-radius:6px;width:${upProb}%;"></div>
        </div>
        <div style="font-size:18px;font-weight:800;color:${probColor};min-width:44px;text-align:right;">${upProb}%</div>
      </div>
      <div style="font-size:10px;color:#9ca3af;margin-top:4px;">※ 시장 평균 대비 상대 확률. 50% = 시장평균, 65%+ = 매수신호 수준</div>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-bottom:4px;">
      <button id="btn240Toggle" style="font-size:11px;padding:3px 10px;border-radius:6px;border:1px solid #d1d5db;background:#f9fafb;color:#374151;cursor:pointer;">240일 예측 보기</button>
    </div>
    <div class="chart-wrap"><canvas id="chartPrice"></canvas></div>
    <div class="chart-wrap rsi"><canvas id="chartRsi"></canvas></div>
    <div class="chart-wrap cci"><canvas id="chartCci"></canvas></div>
    <div id="crossInfo"></div>
    <div id="priceGuide"></div>
    <div id="signalPanel"></div>
    <div id="chartStatus" class="chart-loading">차트 데이터 불러오는 중…</div>
  `;
  document.getElementById("preview").innerHTML = html;
  loadOhlcvChart(d);

  if (window.innerWidth < 1100) {
    setTimeout(() => {
      document.getElementById("preview").scrollIntoView({behavior: "smooth", block: "start"});
    }, 100);
  }
}

let _chartPrice = null, _chartRsi = null, _chartCci = null;
async function loadOhlcvChart(d) {
  if (_chartPrice) { _chartPrice.destroy(); _chartPrice = null; }
  if (_chartRsi)   { _chartRsi.destroy();   _chartRsi = null;   }
  if (_chartCci)   { _chartCci.destroy();   _chartCci = null;   }
  const status = document.getElementById("chartStatus");
  try {
    const r = await fetch(`/ohlcv/${d.code}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    if (j.error) throw new Error(j.error);

    status.style.display = "none";

    const cal60  = Math.round(60  * 1.4);
    const cal120 = Math.round(120 * 1.4);
    const cal240 = Math.round(240 * 1.4);
    const lastIdx = j.close.length - 1;
    const lastClose = j.close[lastIdx];
    const lastDate = new Date(j.date[lastIdx]);
    function addDays(n) { const x = new Date(lastDate); x.setDate(x.getDate() + n); return x.toISOString().slice(0,10); }

    const labels = j.date.slice();
    for (let i = 1; i <= cal240; i++) labels.push(addDays(i));
    const pad = arr => arr.concat(Array(cal240).fill(null));

    const fc = (calDays, ret) => {
      const a = Array(labels.length).fill(null);
      a[lastIdx] = lastClose;
      a[lastIdx + calDays] = lastClose * (1 + (ret || 0) / 100);
      return a;
    };
    const fcColor = ret => (ret >= 0 ? "#d62728" : "#1a7f37");

    // MA20 선형 추세 투영
    let ma20LastIdx = -1, ma20PrevIdx = -1;
    for (let i = j.ma20.length - 1; i >= 0; i--) {
      if (j.ma20[i] !== null) {
        if (ma20LastIdx === -1) ma20LastIdx = i;
        else if (i <= ma20LastIdx - 5) { ma20PrevIdx = i; break; }
      }
    }
    const ma20Slope = (ma20LastIdx >= 0 && ma20PrevIdx >= 0)
      ? (j.ma20[ma20LastIdx] - j.ma20[ma20PrevIdx]) / (ma20LastIdx - ma20PrevIdx) : 0;
    const ma20Fc = Array(labels.length).fill(null);
    if (ma20LastIdx >= 0) { for (let i = 0; i <= cal240; i++) ma20Fc[ma20LastIdx + i] = j.ma20[ma20LastIdx] + ma20Slope * i; }

    // 골든/데드크로스 감지
    const crossEvents = [];
    for (let i = 1; i < j.ma20.length; i++) {
      const m20c = j.ma20[i], m60c = j.ma60[i], m20p = j.ma20[i-1], m60p = j.ma60[i-1];
      if (m20c===null||m60c===null||m20p===null||m60p===null) continue;
      if (m20p < m60p && m20c >= m60c) crossEvents.push({ i, date: j.date[i], type: "golden", price: j.close[i] });
      else if (m20p > m60p && m20c <= m60c) crossEvents.push({ i, date: j.date[i], type: "dead", price: j.close[i] });
    }
    let upcomingCross = null;
    if (ma20LastIdx >= 0 && j.ma60[ma20LastIdx] !== null) {
      const lastDiff = j.ma20[ma20LastIdx] - j.ma60[ma20LastIdx];
      for (let i = 1; i <= cal240; i++) {
        const projDiff = ma20Fc[ma20LastIdx + i] - j.ma60[ma20LastIdx];
        if (lastDiff < 0 && projDiff >= 0) { upcomingCross = { days: i, type: "golden" }; break; }
        if (lastDiff > 0 && projDiff <= 0) { upcomingCross = { days: i, type: "dead"   }; break; }
      }
    }
    const gcData = Array(labels.length).fill(null);
    const dcData = Array(labels.length).fill(null);
    crossEvents.slice(-10).forEach(ev => { if (ev.type==="golden") gcData[ev.i]=ev.price; else dcData[ev.i]=ev.price; });

    const ctxP = document.getElementById("chartPrice").getContext("2d");
    _chartPrice = new Chart(ctxP, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "종가",     data: pad(j.close), borderColor: "#1f77b4", borderWidth: 1.2, pointRadius: 0, tension: 0.1 },
          { label: "MA20",    data: pad(j.ma20),  borderColor: "#ff7f0e", borderWidth: 1,   pointRadius: 0, tension: 0.1 },
          { label: "MA20예상", data: ma20Fc,       borderColor: "#ff7f0e", borderDash: [4,3], borderWidth: 1.5, pointRadius: 0, tension: 0.1, spanGaps: false },
          { label: "MA60",    data: pad(j.ma60),  borderColor: "#2ca02c", borderWidth: 1,   pointRadius: 0, tension: 0.1 },
          { label: "MA120",   data: pad(j.ma120), borderColor: "#9467bd", borderWidth: 1,   pointRadius: 0, tension: 0.1 },
          { label: `60d ${(d.r60>=0?"+":"")}${d.r60.toFixed(1)}%`,   data: fc(cal60,  d.r60),  borderColor: fcColor(d.r60),  borderDash: [5,3], borderWidth: 2, pointRadius: 4, pointBackgroundColor: fcColor(d.r60),  spanGaps: true },
          { label: `120d ${(d.r120>=0?"+":"")}${d.r120.toFixed(1)}%`, data: fc(cal120, d.r120), borderColor: fcColor(d.r120), borderDash: [5,3], borderWidth: 2, pointRadius: 4, pointBackgroundColor: fcColor(d.r120), spanGaps: true },
          { label: `240d ${(d.r240>=0?"+":"")}${d.r240.toFixed(1)}%`, data: fc(cal240, d.r240), borderColor: fcColor(d.r240), borderDash: [5,3], borderWidth: 2, pointRadius: 4, pointBackgroundColor: fcColor(d.r240), spanGaps: true },
          { label: "골든크로스", data: pad(gcData), borderColor: "#DAA520", backgroundColor: "#DAA520", borderWidth: 0, pointRadius: 7, pointStyle: "triangle", showLine: false },
          { label: "데드크로스", data: pad(dcData), borderColor: "#374151", backgroundColor: "#374151", borderWidth: 0, pointRadius: 7, pointStyle: "triangle", rotation: 180, showLine: false },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { position: "top", labels: { boxWidth: 10, font: { size: 10 }, padding: 6 } },
          tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y == null ? "—" : Math.round(c.parsed.y).toLocaleString()}원` } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8, font: { size: 10 }, autoSkip: true } },
          y: { ticks: { callback: v => v.toLocaleString(), font: { size: 10 } } }
        }
      }
    });

    // 240d 예측선 기본 숨김 + 토글 버튼
    _chartPrice.setDatasetVisibility(7, false);
    _chartPrice.update('none');
    const btn240 = document.getElementById("btn240Toggle");
    if (btn240) {
      btn240.onclick = () => {
        const vis = !_chartPrice.isDatasetVisible(7);
        _chartPrice.setDatasetVisibility(7, vis);
        _chartPrice.update('none');
        btn240.textContent = vis ? "240일 예측 숨기기" : "240일 예측 보기";
        btn240.style.background = vis ? "#eff6ff" : "#f9fafb";
        btn240.style.borderColor = vis ? "#93c5fd" : "#d1d5db";
        btn240.style.color = vis ? "#1d4ed8" : "#374151";
      };
    }

    const refLine = (val) => Array(j.date.length).fill(val);
    const ctxR = document.getElementById("chartRsi").getContext("2d");
    _chartRsi = new Chart(ctxR, {
      type: "line",
      data: {
        labels: j.date,
        datasets: [
          { label: "RSI14", data: j.rsi14, borderColor: "#9467bd", borderWidth: 1, pointRadius: 0, tension: 0.1 },
          { label: "70",    data: refLine(70), borderColor: "#dc2626", borderWidth: 0.6, borderDash: [3,3], pointRadius: 0 },
          { label: "30",    data: refLine(30), borderColor: "#16a34a", borderWidth: 0.6, borderDash: [3,3], pointRadius: 0 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false }, tooltip: { filter: c => c.datasetIndex === 0 } },
        scales: { x: { display: false }, y: { min: 0, max: 100, ticks: { stepSize: 50, font: { size: 9 } } } }
      }
    });

    const ctxC = document.getElementById("chartCci").getContext("2d");
    _chartCci = new Chart(ctxC, {
      type: "line",
      data: {
        labels: j.date,
        datasets: [
          { label: "CCI20", data: j.cci20, borderColor: "#0ea5e9", borderWidth: 1, pointRadius: 0, tension: 0.1, fill: false },
          { label: "+100", data: refLine(100),  borderColor: "#dc2626", borderWidth: 0.7, borderDash: [3,3], pointRadius: 0 },
          { label: "-100", data: refLine(-100), borderColor: "#16a34a", borderWidth: 0.7, borderDash: [3,3], pointRadius: 0 },
          { label: "+200", data: refLine(200),  borderColor: "#991b1b", borderWidth: 0.5, borderDash: [2,4], pointRadius: 0 },
          { label: "-200", data: refLine(-200), borderColor: "#14532d", borderWidth: 0.5, borderDash: [2,4], pointRadius: 0 },
          { label: "0",    data: refLine(0),    borderColor: "#9ca3af", borderWidth: 0.5, pointRadius: 0 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false }, tooltip: { filter: c => c.datasetIndex === 0,
          callbacks: { label: c => `CCI20: ${c.parsed.y == null ? "—" : c.parsed.y.toFixed(1)}` } } },
        scales: { x: { display: false }, y: { ticks: { font: { size: 9 }, maxTicksLimit: 5 } } }
      }
    });

    // RSI + CCI 신호 판정
    const lastRsi = [...j.rsi14].reverse().find(v => v !== null) ?? null;
    const lastCci = j.cci20 ? ([...j.cci20].reverse().find(v => v !== null) ?? null) : null;
    function recentCross(arr, threshold, direction, lookback=5) {
      if (!arr) return false;
      for (let i = arr.length-1; i >= Math.max(1, arr.length-lookback); i--) {
        if (arr[i]==null||arr[i-1]==null) continue;
        if (direction==="up"   && arr[i-1]<threshold && arr[i]>=threshold) return true;
        if (direction==="down" && arr[i-1]>threshold && arr[i]<=threshold) return true;
      } return false;
    }
    function sigCard(title, value, signal, color, bg, detail, timing) {
      return `<div style="flex:1;min-width:0;background:${bg};border:1px solid ${color}33;border-radius:8px;padding:10px 12px;">
        <div style="font-size:10px;color:#6b7280;font-weight:600;letter-spacing:0.5px;margin-bottom:4px;">${title}</div>
        <div style="font-size:20px;font-weight:800;color:${color};margin-bottom:4px;">${value!=null?value.toFixed(1):"—"}</div>
        <div style="display:inline-block;padding:2px 8px;border-radius:12px;background:${color};color:#fff;font-size:11px;font-weight:700;margin-bottom:5px;">${signal}</div>
        ${timing?`<div style="font-size:11px;font-weight:700;color:${color};margin-bottom:3px;">⚡ ${timing}</div>`:""}
        <div style="font-size:10.5px;color:#4b5563;line-height:1.5;">${detail}</div>
      </div>`;
    }
    let rsiSig,rsiColor,rsiBg,rsiDetail,rsiTiming=null;
    if(lastRsi==null){rsiSig="데이터 없음";rsiColor="#9ca3af";rsiBg="#f9fafb";rsiDetail="";}
    else if(lastRsi<20){rsiSig="극단 과매도";rsiColor="#b91c1c";rsiBg="#fef2f2";rsiDetail="RSI 20 이하 — 강한 반등 가능성. 20 상향 돌파 시 매수 고려";if(recentCross(j.rsi14,20,"up"))rsiTiming="매수 시점 (RSI 20 상향 돌파)";}
    else if(lastRsi<30){rsiSig="과매도 — 매수 신호";rsiColor="#d62728";rsiBg="#fff1f1";rsiDetail="과매도 구간. RSI 30 상향 돌파 시 매수 진입 타이밍";if(recentCross(j.rsi14,30,"up"))rsiTiming="매수 시점 (RSI 30 상향 돌파)";}
    else if(lastRsi<50){rsiSig="하락 추세";rsiColor="#d97706";rsiBg="#fffbeb";rsiDetail="50선 아래 — 하락 우세. RSI 50 상향 돌파 확인 후 진입 고려";if(recentCross(j.rsi14,50,"up"))rsiTiming="상승 전환 (RSI 50 돌파)";}
    else if(lastRsi<=70){rsiSig="상승 추세";rsiColor="#2563eb";rsiBg="#eff6ff";rsiDetail="50~70 구간 — 상승 추세 유지. 70 접근 시 비중 축소 준비";if(recentCross(j.rsi14,50,"down"))rsiTiming="하락 전환 주의 (RSI 50 이탈)";}
    else if(lastRsi<=80){rsiSig="과매수 — 매도 신호";rsiColor="#166534";rsiBg="#f0fdf4";rsiDetail="과매수 구간. RSI 70 하향 이탈 시 매도·익절 타이밍";if(recentCross(j.rsi14,70,"down"))rsiTiming="매도 시점 (RSI 70 하향 이탈)";}
    else{rsiSig="극단 과매수";rsiColor="#14532d";rsiBg="#dcfce7";rsiDetail="RSI 80 초과 — 단기 급등 과열. 분할 매도 권장";if(recentCross(j.rsi14,80,"down"))rsiTiming="매도 시점 (RSI 80 이탈)";}

    let cciSig,cciColor,cciBg,cciDetail,cciTiming=null;
    if(lastCci==null){cciSig="데이터 없음";cciColor="#9ca3af";cciBg="#f9fafb";cciDetail="";}
    else if(lastCci<-200){cciSig="극단 과매도";cciColor="#b91c1c";cciBg="#fef2f2";cciDetail="CCI -200 이하 — 극단적 매도 과잉. -100 회복 시 강한 반등";if(recentCross(j.cci20,-100,"up"))cciTiming="매수 시점 (CCI -100 상향 돌파)";}
    else if(lastCci<-100){cciSig="과매도 — 매수 신호";cciColor="#d62728";cciBg="#fff1f1";cciDetail="과매도 구간(-100 이하). CCI -100 상향 돌파 시 매수 타이밍";if(recentCross(j.cci20,-100,"up"))cciTiming="매수 시점 (CCI -100 상향 돌파)";}
    else if(lastCci<0){cciSig="하락 추세";cciColor="#d97706";cciBg="#fffbeb";cciDetail="0선 아래 — 단기 하락 우세. CCI 0선 돌파 확인 후 매수 고려";if(recentCross(j.cci20,0,"up"))cciTiming="상승 전환 (CCI 0 돌파)";}
    else if(lastCci<=100){cciSig="상승 추세";cciColor="#2563eb";cciBg="#eff6ff";cciDetail="0~+100 구간 — 상승 추세. +100 접근 시 익절 준비";if(recentCross(j.cci20,0,"down"))cciTiming="하락 전환 주의 (CCI 0 이탈)";}
    else if(lastCci<=200){cciSig="과매수 — 매도 신호";cciColor="#166534";cciBg="#f0fdf4";cciDetail="과매수(+100 초과). CCI +100 하향 이탈 시 매도 타이밍";if(recentCross(j.cci20,100,"down"))cciTiming="매도 시점 (CCI +100 하향 이탈)";}
    else{cciSig="극단 과매수";cciColor="#14532d";cciBg="#dcfce7";cciDetail="CCI +200 초과 — 극단적 과매수. 단기 조정 임박";if(recentCross(j.cci20,200,"down"))cciTiming="매도 시점 (CCI +200 이탈)";}

    // ===== 매수·매도 타이밍 종합 점수 =====
    const ma20Last=ma20LastIdx>=0?j.ma20[ma20LastIdx]:null;
    const priceNow=j.close[lastIdx];
    let buyScore=0, sellScore=0;
    const buySigs=[], sellSigs=[];
    // RSI
    if (lastRsi!==null) {
      if (recentCross(j.rsi14,20,"up",  5)){buyScore +=3;buySigs.push({s:"RSI 20 상향 돌파 (강한 과매도 회복)",w:3});}
      if (recentCross(j.rsi14,30,"up",  5)){buyScore +=3;buySigs.push({s:"RSI 30 상향 돌파 (과매도 탈출)",w:3});}
      if (recentCross(j.rsi14,70,"down",5)){sellScore+=3;sellSigs.push({s:"RSI 70 하향 이탈 (과매수 해소)",w:3});}
      if (recentCross(j.rsi14,80,"down",5)){sellScore+=3;sellSigs.push({s:"RSI 80 하향 이탈 (강한 과매수 해소)",w:3});}
      if      (lastRsi<20){buyScore +=2;buySigs.push({s:`RSI 극단 과매도 (현재 ${lastRsi.toFixed(1)})`,w:2});}
      else if (lastRsi<30){buyScore +=1;buySigs.push({s:`RSI 과매도 구간 (현재 ${lastRsi.toFixed(1)})`,w:1});}
      else if (lastRsi>80){sellScore+=2;sellSigs.push({s:`RSI 극단 과매수 (현재 ${lastRsi.toFixed(1)})`,w:2});}
      else if (lastRsi>70){sellScore+=1;sellSigs.push({s:`RSI 과매수 구간 (현재 ${lastRsi.toFixed(1)})`,w:1});}
    }
    // CCI
    if (lastCci!==null) {
      if (recentCross(j.cci20,-200,"up",  5)){buyScore +=2;buySigs.push({s:"CCI -200 상향 돌파 (극단 과매도 회복)",w:2});}
      if (recentCross(j.cci20,-100,"up",  5)){buyScore +=3;buySigs.push({s:"CCI -100 상향 돌파 (과매도 탈출)",w:3});}
      if (recentCross(j.cci20, 100,"down",5)){sellScore+=3;sellSigs.push({s:"CCI +100 하향 이탈 (과매수 해소)",w:3});}
      if (recentCross(j.cci20, 200,"down",5)){sellScore+=2;sellSigs.push({s:"CCI +200 하향 이탈 (극단 과매수 해소)",w:2});}
      if      (lastCci<-200){buyScore +=2;buySigs.push({s:`CCI 극단 과매도 (현재 ${lastCci.toFixed(0)})`,w:2});}
      else if (lastCci<-100){buyScore +=1;buySigs.push({s:`CCI 과매도 구간 (현재 ${lastCci.toFixed(0)})`,w:1});}
      else if (lastCci> 200){sellScore+=2;sellSigs.push({s:`CCI 극단 과매수 (현재 ${lastCci.toFixed(0)})`,w:2});}
      else if (lastCci> 100){sellScore+=1;sellSigs.push({s:`CCI 과매수 구간 (현재 ${lastCci.toFixed(0)})`,w:1});}
    }
    // 골든·데드크로스 (최근 20봉)
    const lastCrossEvt=crossEvents[crossEvents.length-1];
    if (lastCrossEvt&&j.ma20.length-lastCrossEvt.i<=20) {
      if (lastCrossEvt.type==="golden"){buyScore +=2;buySigs.push({s:`골든크로스 발생 ${lastCrossEvt.date}`,w:2});}
      else                             {sellScore+=2;sellSigs.push({s:`데드크로스 발생 ${lastCrossEvt.date}`,w:2});}
    }
    // 가격 MA20 돌파 (최근 5봉)
    let priceCrossed=false;
    for (let i=j.close.length-1;i>=Math.max(1,j.close.length-5);i--) {
      const [c,cp,m,mp]=[j.close[i],j.close[i-1],j.ma20[i],j.ma20[i-1]];
      if (c&&cp&&m&&mp) {
        if (cp<mp&&c>=m){buyScore +=2;buySigs.push({s:"가격 MA20 상향 돌파",w:2});priceCrossed=true;break;}
        if (cp>mp&&c<=m){sellScore+=2;sellSigs.push({s:"가격 MA20 하향 이탈",w:2});priceCrossed=true;break;}
      }
    }
    if (!priceCrossed&&ma20Last!==null&&priceNow!==null) {
      if (ma20Slope>0&&priceNow>ma20Last)      {buyScore +=1;buySigs.push({s:"MA20 상승 + 가격 MA20 위",w:1});}
      else if (ma20Slope<0&&priceNow<ma20Last) {sellScore+=1;sellSigs.push({s:"MA20 하락 + 가격 MA20 아래",w:1});}
    }
    const netScore=buyScore-sellScore;
    let verdict,vColor,vBg,vBorder;
    if      (netScore>=6) {verdict="★ 강한 매수 타이밍";vColor="#b91c1c";vBg="#fef2f2";vBorder="#fca5a5";}
    else if (netScore>=3) {verdict="매수 신호";         vColor="#d62728";vBg="#fff5f5";vBorder="#fca5a5";}
    else if (netScore>=1) {verdict="매수 대기";         vColor="#d97706";vBg="#fffbeb";vBorder="#fde68a";}
    else if (netScore<=-6){verdict="★ 강한 매도 타이밍";vColor="#14532d";vBg="#f0fdf4";vBorder="#86efac";}
    else if (netScore<=-3){verdict="매도 신호";         vColor="#166534";vBg="#f0fdf4";vBorder="#86efac";}
    else if (netScore<=-1){verdict="매도 대기";         vColor="#374151";vBg="#f9fafb";vBorder="#d1d5db";}
    else                  {verdict="관망";              vColor="#6b7280";vBg="#f9fafb";vBorder="#e5e7eb";}
    const maxS=12;
    const gaugeW=Math.min(Math.abs(netScore)/maxS*50,50);
    const gaugeL=netScore>=0?50:50-gaugeW;
    const gaugeC=netScore>0?"#d62728":netScore<0?"#166534":"#9ca3af";
    const sigRow=(s,isBuy)=>
      `<div style="display:flex;align-items:center;gap:5px;padding:5px 8px;background:${isBuy?"#fff1f1":"#f0fdf4"};border-radius:6px;font-size:11px;color:${isBuy?"#b91c1c":"#166534"};font-weight:${s.w>=3?"700":"400"};">
        ${s.w>=3?"🔥":isBuy?"📈":"📉"} ${s.s}
      </div>`;
    const timingHtml=`
    <div style="background:${vBg};border:2px solid ${vBorder};border-radius:12px;padding:14px 16px;margin-top:8px;">
      <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:10px;">⚡ 매수·매도 타이밍 종합</div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
        <div style="background:${vColor};color:#fff;padding:9px 16px;border-radius:8px;font-size:15px;font-weight:800;white-space:nowrap;box-shadow:0 2px 8px ${vColor}44;">${verdict}</div>
        <div style="flex:1;min-width:120px;">
          <div style="font-size:9.5px;color:#6b7280;margin-bottom:3px;display:flex;justify-content:space-between;"><span>매도</span><span>관망</span><span>매수</span></div>
          <div style="background:#e5e7eb;border-radius:6px;height:12px;position:relative;overflow:hidden;">
            <div style="position:absolute;left:50%;top:0;bottom:0;width:2px;background:#9ca3af;z-index:1;margin-left:-1px;"></div>
            <div style="position:absolute;top:0;bottom:0;left:${gaugeL}%;width:${gaugeW}%;background:${gaugeC};border-radius:6px;transition:width 0.5s;"></div>
          </div>
        </div>
        <div style="font-size:20px;font-weight:800;color:${vColor};min-width:36px;text-align:center;">${netScore>0?"+":""}${netScore}</div>
      </div>
      ${buySigs.length===0&&sellSigs.length===0
        ?`<div style="text-align:center;color:#9ca3af;font-size:11px;padding:8px 0;">현재 뚜렷한 매수·매도 타이밍 신호 없음 — 관망 유지</div>`
        :`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:4px;">
            ${buySigs.map(s=>sigRow(s,true)).join("")}
            ${sellSigs.map(s=>sigRow(s,false)).join("")}
          </div>`
      }
      <div style="font-size:10px;color:#9ca3af;margin-top:8px;line-height:1.6;">🔥 = 최근 5봉 내 기준선 돌파 (핵심 타이밍) &nbsp;|&nbsp; 점수: 매수 +${buyScore} / 매도 -${sellScore} / 합산 ${netScore>0?"+":""}${netScore}</div>
    </div>`;
    const spEl=document.getElementById("signalPanel");
    if(spEl) spEl.innerHTML=timingHtml+`
      <div style="margin-top:8px;">
        <div style="font-size:11px;font-weight:700;color:#9ca3af;letter-spacing:0.5px;margin-bottom:5px;">📡 지표별 현재 상태</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          ${sigCard("RSI 14",lastRsi,rsiSig,rsiColor,rsiBg,rsiDetail,rsiTiming)}
          ${sigCard("CCI 20",lastCci,cciSig,cciColor,cciBg,cciDetail,cciTiming)}
        </div>
        <div style="font-size:10px;color:#9ca3af;margin-top:5px;line-height:1.5;">RSI: 30 이하 과매도·매수 / 70 이상 과매수·매도 &nbsp;|&nbsp; CCI: −100 이하 매수 / +100 이상 매도</div>
      </div>`;

    // ===== 골든·데드크로스 전용 패널 =====
    const ma60Now = [...j.ma60].reverse().find(v => v !== null) ?? null;

    // 현재 MA20 vs MA60 관계
    let crossStatus = null;
    if (ma20Last !== null && ma60Now !== null) {
      const isGolden = ma20Last > ma60Now;
      const gapPct   = ((ma20Last - ma60Now) / ma60Now * 100).toFixed(2);
      const lastEv   = crossEvents[crossEvents.length - 1];
      const daysSince = lastEv ? (() => {
        const d1 = new Date(lastEv.date), d2 = new Date(j.date[j.date.length-1]);
        return Math.round((d2 - d1) / 86400000);
      })() : null;
      crossStatus = { isGolden, gapPct, lastEv, daysSince };
    }

    // 크로스 이력 행 생성
    const crossHistoryRows = crossEvents.slice(-6).reverse().map((ev, idx) => {
      const isG = ev.type === 'golden';
      const isLatest = idx === 0;
      return `<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;
          background:${isLatest ? (isG?'#fef9f0':'#f0fdf4') : '#fafafa'};
          border-radius:8px;border:1px solid ${isLatest ? (isG?'#fde68a':'#bbf7d0') : '#f1f5f9'};">
        <div style="width:28px;height:28px;border-radius:50%;background:${isG?'#f59e0b':'#374151'};
            display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:13px;">
          ${isG ? '▲' : '▼'}
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:12.5px;font-weight:${isLatest?'800':'600'};color:${isG?'#92400e':'#1f2937'};">
            ${isG ? '골든크로스' : '데드크로스'}
            ${isLatest ? '<span style="font-size:10px;background:#3b82f6;color:#fff;padding:1px 6px;border-radius:10px;margin-left:5px;">최근</span>' : ''}
          </div>
          <div style="font-size:11px;color:#64748b;margin-top:1px;">${ev.date} &nbsp;·&nbsp; ${fmtNum(Math.round(ev.price))}원</div>
        </div>
        <div style="font-size:11px;color:${isG?'#d97706':'#475569'};font-weight:600;text-align:right;">
          MA20<br>${isG?'↑위':'↓아래'}
        </div>
      </div>`;
    }).join("");

    // 현재 상태 뱃지
    const statusHtml = crossStatus ? (() => {
      const { isGolden, gapPct, lastEv, daysSince } = crossStatus;
      const stBg     = isGolden ? '#fffbeb' : '#f0fdf4';
      const stBorder = isGolden ? '#fde68a' : '#bbf7d0';
      const stColor  = isGolden ? '#92400e' : '#166534';
      const stIcon   = isGolden ? '🟡' : '🔵';
      return `
      <div style="background:${stBg};border:2px solid ${stBorder};border-radius:10px;padding:12px 14px;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <div>
            <div style="font-size:11px;color:#64748b;margin-bottom:2px;">현재 상태</div>
            <div style="font-size:16px;font-weight:800;color:${stColor};">
              ${stIcon} ${isGolden ? '골든크로스 구간' : '데드크로스 구간'}
            </div>
            ${daysSince !== null ? `<div style="font-size:10.5px;color:#94a3b8;margin-top:2px;">마지막 크로스 ${daysSince}일 전</div>` : ''}
          </div>
          <div style="flex:1;min-width:0;text-align:right;">
            <div style="font-size:10px;color:#94a3b8;margin-bottom:3px;">MA20 vs MA60 괴리율</div>
            <div style="font-size:18px;font-weight:800;color:${stColor};">${gapPct > 0 ? '+' : ''}${gapPct}%</div>
            <div style="font-size:10.5px;color:#64748b;">
              MA20 ${fmtNum(Math.round(ma20Last))}원 &nbsp;|&nbsp; MA60 ${fmtNum(Math.round(ma60Now))}원
            </div>
          </div>
        </div>
      </div>`;
    })() : '';

    // 예상 크로스
    const upcomingHtml = upcomingCross ? `
      <div style="background:${upcomingCross.type==='golden'?'#eff6ff':'#fff1f2'};border:1px dashed ${upcomingCross.type==='golden'?'#93c5fd':'#fca5a5'};border-radius:8px;padding:10px 12px;margin-top:8px;display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">🔮</span>
        <div>
          <div style="font-size:12px;font-weight:700;color:${upcomingCross.type==='golden'?'#1d4ed8':'#dc2626'};">
            ${upcomingCross.type==='golden'?'골든':'데드'}크로스 예상
          </div>
          <div style="font-size:11px;color:#64748b;">MA20 추세 유지 시 약 <b>${upcomingCross.days}일 후</b> 발생 예상</div>
        </div>
      </div>` : '';

    const crossInfoEl = document.getElementById("crossInfo");
    if (crossInfoEl) crossInfoEl.innerHTML = `
    <div style="background:#fff;border:2px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-top:10px;">
      <div style="font-size:12px;font-weight:700;color:#1e293b;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
        <span style="font-size:16px;">🔀</span> MA20 × MA60 골든·데드크로스 분석
      </div>

      ${statusHtml}

      <div style="font-size:11px;font-weight:700;color:#64748b;margin-bottom:6px;letter-spacing:0.3px;">📋 크로스 이력 (최근 6회)</div>
      ${crossHistoryRows || `<div style="text-align:center;color:#94a3b8;font-size:12px;padding:16px 0;">데이터 기간 내 골든·데드크로스 없음</div>`}

      ${upcomingHtml}

      <div style="font-size:10px;color:#94a3b8;margin-top:8px;line-height:1.6;">
        ※ 골든크로스: MA20이 MA60을 상향 돌파 (단기 상승 신호) &nbsp;|&nbsp; 데드크로스: MA20이 MA60을 하향 이탈 (단기 하락 신호)
      </div>
    </div>`;

    // ===== 매수·매도 가격 가이드 =====
    const lastMa60v =([...j.ma60].reverse().find(v=>v!==null)??null);
    const lastMa120v=([...j.ma120].reverse().find(v=>v!==null)??null);
    const lastMa252v=([...j.ma252].reverse().find(v=>v!==null)??null);
    const dirScore=(netScore/12)*0.5+Math.max(-1,Math.min(1,d.score/2))*0.5;
    const isUpDir=dirScore>0.05, isDownDir=dirScore<-0.05;
    const confPct=Math.min(Math.round(Math.abs(dirScore)*100),95);
    const dirLabel=isUpDir?"▲ 상승":isDownDir?"▼ 하락":"→ 횡보";
    const dirColor=isUpDir?"#d62728":isDownDir?"#166534":"#6b7280";
    const dirBg   =isUpDir?"#fff5f5":isDownDir?"#f0fdf4":"#f9fafb";
    const maLevels=[
      {v:ma20Last,   label:"MA20"},
      {v:lastMa60v,  label:"MA60"},
      {v:lastMa120v, label:"MA120"},
      {v:lastMa252v, label:"MA252"},
    ].filter(m=>m.v!==null);
    const supBelow=maLevels.filter(m=>m.v<priceNow).sort((a,b)=>b.v-a.v);
    const resAbove=maLevels.filter(m=>m.v>priceNow).sort((a,b)=>a.v-b.v);
    let buyLow,buyHigh,buyBasis;
    const strongBuyNow=netScore>=3||(lastRsi!==null&&lastRsi<30)||(lastCci!==null&&lastCci<-100);
    if(strongBuyNow){
      buyLow=Math.round(priceNow*0.99); buyHigh=Math.round(priceNow*1.005);
      buyBasis="현재가 기준 즉시 매수";
    } else if(netScore>=1&&supBelow.length>0){
      const s=supBelow[0];
      buyLow=Math.round(s.v*0.99); buyHigh=Math.round(s.v*1.01);
      buyBasis=`${s.label} 지지선 (${fmtNum(Math.round(s.v))}원) 눌림 매수`;
    } else if(supBelow.length>=2){
      const s=supBelow[1];
      buyLow=Math.round(s.v*0.98); buyHigh=Math.round(s.v*1.005);
      buyBasis=`${s.label} 지지선 (${fmtNum(Math.round(s.v))}원) 대기 후 매수`;
    } else if(supBelow.length===1){
      const s=supBelow[0];
      buyLow=Math.round(s.v*0.97); buyHigh=Math.round(s.v*1.00);
      buyBasis=`${s.label} 지지선 (${fmtNum(Math.round(s.v))}원) 대기 후 매수`;
    } else {
      buyLow=Math.round(priceNow*0.93); buyHigh=Math.round(priceNow*0.97);
      buyBasis="추가 하락 후 매수 대기";
    }
    const midEntry=Math.round((buyLow+buyHigh)/2);
    const sell20v =d.r20!=null?Math.round(midEntry*(1+d.r20/100)):null;
    const sell60v =Math.round(midEntry*(1+d.r60/100));
    const sell120v=Math.round(midEntry*(1+d.r120/100));
    const nearRes=resAbove.length>0?resAbove[0]:null;
    const stopSup=maLevels.filter(m=>m.v<buyLow).sort((a,b)=>b.v-a.v)[0]??null;
    const stopLoss=stopSup?Math.round(stopSup.v*0.97):Math.round(buyLow*0.93);
    const stopPct=((stopLoss-midEntry)/midEntry*100).toFixed(1);
    const stopBasis=stopSup?`${stopSup.label} 하방 3%`:"매수가 기준 −7%";
    const sellRow=(label,price)=>{
      if(price==null) return "";
      const pDiff=((price-midEntry)/midEntry*100).toFixed(1);
      const col=price>=midEntry?"#15803d":"#b91c1c";
      const resNote=nearRes&&price>nearRes.v
        ?`<span style="font-size:9px;color:#d97706;"> ⚠ ${nearRes.label} 저항(${fmtNum(Math.round(nearRes.v))}원) 확인</span>`:"";
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #f0fdf4;">
        <span style="font-size:11px;color:#4b5563;">${label}</span>
        <span style="font-weight:700;color:${col};font-size:13px;">${fmtNum(price)}원 <span style="font-size:10px;font-weight:400;">(${pDiff>=0?"+":""}${pDiff}%)</span>${resNote}</span>
      </div>`;
    };
    const pgEl=document.getElementById("priceGuide");
    if(pgEl) pgEl.innerHTML=`
    <div style="background:#fff;border:2px solid #dbeafe;border-radius:12px;padding:14px 16px;margin-top:8px;">
      <div style="font-size:12px;font-weight:700;color:#1e40af;margin-bottom:10px;">📌 매수·매도 가격 가이드</div>
      <div style="background:${dirBg};border-radius:8px;padding:9px 12px;margin-bottom:10px;display:flex;align-items:center;gap:10px;">
        <div style="font-size:17px;font-weight:800;color:${dirColor};white-space:nowrap;">${dirLabel}</div>
        <div style="flex:1;">
          <div style="font-size:9px;color:#6b7280;margin-bottom:3px;">예측 신뢰도 (모델 + 기술지표 종합)</div>
          <div style="background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;">
            <div style="background:${dirColor};height:8px;width:${confPct}%;border-radius:4px;"></div>
          </div>
        </div>
        <div style="font-size:17px;font-weight:800;color:${dirColor};">${confPct}%</div>
      </div>
      <div style="display:grid;gap:8px;">
        <div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:10px 12px;">
          <div style="font-size:10.5px;font-weight:700;color:#be123c;margin-bottom:5px;">💚 매수 진입 구간</div>
          <div style="font-size:19px;font-weight:800;color:#be123c;letter-spacing:-0.5px;">${fmtNum(buyLow)}원 ~ ${fmtNum(buyHigh)}원</div>
          <div style="font-size:10px;color:#9ca3af;margin-top:3px;">📍 ${buyBasis}</div>
        </div>
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 12px;">
          <div style="font-size:10.5px;font-weight:700;color:#15803d;margin-bottom:5px;">🎯 매도 목표가 <span style="font-weight:400;color:#9ca3af;">(매수 기준가 ${fmtNum(midEntry)}원 → 모델 예상 수익률 적용)</span></div>
          ${sellRow("단기 20일",sell20v)}
          ${sellRow("중기 60일",sell60v)}
          ${sellRow("장기 120일",sell120v)}
        </div>
        <div style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:10px 12px;">
          <div style="font-size:10.5px;font-weight:700;color:#475569;margin-bottom:5px;">🛑 손절 기준가</div>
          <div style="font-size:19px;font-weight:800;color:#475569;">${fmtNum(stopLoss)}원 <span style="font-size:12px;font-weight:400;color:#94a3b8;">(${stopPct}%)</span></div>
          <div style="font-size:10px;color:#94a3b8;margin-top:3px;">📍 ${stopBasis}</div>
        </div>
      </div>
      <div style="font-size:9.5px;color:#9ca3af;margin-top:8px;line-height:1.6;">※ 이 가격은 모델 예측·기술지표 기반 참고용입니다. 실제 투자는 본인 판단 하에 진행하세요.</div>
    </div>`;

  } catch (e) {
    // /ohlcv 실패 → 정적 배포(GitHub Pages 등)일 가능성 → PNG 폴백
    document.querySelectorAll("#preview .chart-wrap").forEach(el => el.remove());
    status.className = "";
    status.innerHTML = `<img src="charts_forecast/${d.code}.png" alt="${d.name}"
         style="max-width:100%;height:auto;border:1px solid #d1d5db;border-radius:4px;display:block;"
         onerror="this.outerHTML='<div class=\\'chart-error\\'>차트 데이터 없음 — 로컬 서버 미실행 또는 charts_forecast PNG 캐시 없음<br><span style=\\'color:#6b7280;font-size:11px;\\'>viewer_open.bat 실행 또는 make_forecast_charts.py 수동 실행 필요</span></div>';">`;
  }
}

document.querySelectorAll("th").forEach(th => {
  th.addEventListener("click", () => {
    const k = th.dataset.key;
    if (sortKey === k) sortDir = sortDir === "asc" ? "desc" : "asc";
    else { sortKey = k; sortDir = "desc"; }
    render();
  });
});
document.getElementById("search").addEventListener("input", render);
document.getElementById("market").addEventListener("change", render);
document.getElementById("rec").addEventListener("change", render);
document.getElementById("priceMin").addEventListener("input", render);
document.getElementById("priceMax").addEventListener("input", render);

// 모달 데이터 메타 + 마지막 기준일 표시
(function fillMeta(){
  if (!DATA.length) return;
  const dates = DATA.map(d => d.date).filter(Boolean).sort();
  const latest = dates[dates.length-1] || "—";

  // 마지막 데이터 경과일
  const today = new Date();
  const ld = new Date(latest);
  const days = isNaN(ld) ? null : Math.floor((today - ld) / (1000*60*60*24));
  let ageText = "";
  let stale = false;
  if (days !== null) {
    if (days <= 1) ageText = "(오늘 기준)";
    else if (days <= 3) ageText = "(" + days + "일 전)";
    else if (days <= 10) { ageText = "(" + days + "일 전)"; }
    else { ageText = "(" + days + "일 전 · 갱신 권장)"; stale = true; }
  }

  const dt1 = document.getElementById("dataDate");
  const dt2 = document.getElementById("dataDate2");
  const age1 = document.getElementById("dataAge");
  const age2 = document.getElementById("dataDate2Age");
  const cnt = document.getElementById("dataCount");
  const badge = document.getElementById("dataBadge");
  if (dt1) dt1.textContent = latest;
  if (dt2) dt2.textContent = latest;
  if (age1) age1.textContent = " " + ageText;
  if (age2) age2.textContent = ageText;
  if (cnt) cnt.textContent = DATA.length.toLocaleString() + " 종목";
  if (badge && stale) badge.classList.add("stale");
})();

// ===== 데이터 갱신 (로컬 서버에서 실행 시 1-클릭) =====
let _refreshTimer = null;

async function startRefresh(){
  const btn = document.getElementById("btnGoRefresh");
  const out = document.getElementById("refreshStatus");
  const hint = document.getElementById("modeHint");
  btn.disabled = true;
  btn.innerHTML = '<span class="pulse"></span> 갱신 중…';
  out.classList.add("visible");
  out.textContent = "[요청] /refresh ...\\n";
  try {
    const r = await fetch("/refresh", { method: "POST" });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || ("HTTP "+r.status));
    out.textContent += "[OK] 갱신 시작됨 — daily_run.bat 백그라운드 실행 중\\n진행 로그를 폴링합니다…\\n\\n";
    if (hint) hint.style.display = "none";
    pollStatus();
  } catch (e) {
    out.textContent += "[실패] " + e.message + "\\n\\n" +
      "이 페이지가 file:// 로 열렸거나 viewer_open.bat 가 실행 중이지 않습니다.\\n" +
      "→ 프로젝트 폴더의 viewer_open.bat 를 더블클릭한 뒤 다시 시도하세요.\\n";
    btn.disabled = false;
    btn.innerHTML = "🚀 지금 갱신 시작 (daily_run.bat)";
  }
}

async function pollStatus(){
  const out = document.getElementById("refreshStatus");
  const btn = document.getElementById("btnGoRefresh");
  try {
    const r = await fetch("/refresh-status");
    const s = await r.json();
    const head = `[상태] running=${s.running}  시작=${s.started_at||"-"}  종료=${s.ended_at||"-"}  rc=${s.returncode==null?"-":s.returncode}\\n`;
    out.textContent = head + "\\n" + (s.log_tail || "(로그 없음)");
    out.scrollTop = out.scrollHeight;
    if (s.running) {
      _refreshTimer = setTimeout(pollStatus, 2000);
    } else {
      btn.disabled = false;
      if (s.returncode === 0) {
        out.textContent += "\\n\\n✅ 갱신 완료! 10초 후 자동으로 페이지를 새로고침합니다...";
        let cnt = 10;
        btn.innerHTML = `✅ 완료 — ${cnt}초 후 자동 새로고침`;
        const cntTimer = setInterval(() => {
          cnt--;
          btn.innerHTML = cnt > 0 ? `✅ 완료 — ${cnt}초 후 자동 새로고침` : "✅ 새로고침 중...";
          if (cnt <= 0) { clearInterval(cntTimer); location.reload(true); }
        }, 1000);
      } else {
        btn.innerHTML = "❗ 종료 (rc=" + s.returncode + ") — 다시 시도";
      }
    }
  } catch (e) {
    out.textContent += "\\n[폴링 오류] " + e.message + "\\n";
    btn.disabled = false;
    btn.innerHTML = "🚀 다시 시도";
  }
}

// 페이지 로드시 서버 모드 감지
(async function detectServer(){
  try {
    const r = await fetch("/refresh-status", { method: "GET" });
    if (r.ok) {
      const hint = document.getElementById("modeHint");
      if (hint) hint.innerHTML = "✅ 로컬 서버 감지됨 — 한 번 클릭으로 실행 가능합니다.";
      // 진행 중이면 바로 폴링
      const s = await r.json();
      if (s.running) {
        document.getElementById("refreshStatus").classList.add("visible");
        const btn = document.getElementById("btnGoRefresh");
        btn.disabled = true;
        btn.innerHTML = '<span class="pulse"></span> 갱신 중…';
        pollStatus();
      }
    }
  } catch(e) {
    // file:// 모드 — 안내 그대로 둠
  }
})();

// ESC로 모달 닫기
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-mask.open").forEach(m => m.classList.remove("open"));
  }
});

render();
</script>
</body>
</html>
"""

html = html.replace("__DATA_JSON__", data_json)
out = ROOT / "viewer.html"
out.write_text(html, encoding="utf-8")
print(f"[OK] HTML (모바일 반응형): {out}")
print(f"     {len(records)}종목 임베드 / {out.stat().st_size/1024:.0f} KB")
