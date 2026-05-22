"""
viewer.html 을 로컬 서버로 제공하면서 "데이터 갱신" 버튼이 daily_run.bat 를
한 번에 실행할 수 있도록 하는 작은 HTTP 서버.

표준 라이브러리만 사용 (외부 의존 없음).
사용:
  py viewer_server.py
  → 브라우저에서 http://127.0.0.1:8765/viewer.html 자동 오픈
  → 헤더의 "🔄 데이터 갱신" 버튼 클릭 → /refresh API 호출 → daily_run.bat 백그라운드 실행
  → /refresh-status 폴링으로 진행률(로그 tail) 표시
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent
PORT = 8765
BAT = ROOT / "daily_run.bat"
LOG = ROOT / "viewer_refresh.log"

# 갱신 작업 상태 (메모리)
_state = {
    "running": False,
    "started_at": None,
    "ended_at": None,
    "returncode": None,
    "error": None,
}
_lock = threading.Lock()


def _run_bat():
    """daily_run.bat 를 별도 프로세스로 실행하고 stdout/stderr 를 로그 파일에 기록."""
    with _lock:
        _state["running"] = True
        _state["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _state["ended_at"] = None
        _state["returncode"] = None
        _state["error"] = None

    LOG.write_text(f"=== 갱신 시작: {_state['started_at']} ===\n", encoding="utf-8")

    try:
        with LOG.open("a", encoding="utf-8") as fp:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.Popen(
                ["cmd.exe", "/c", str(BAT)],
                cwd=str(ROOT),
                stdout=fp,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            rc = proc.wait()
        with _lock:
            _state["returncode"] = rc
    except Exception as e:
        with _lock:
            _state["error"] = repr(e)
    finally:
        with _lock:
            _state["running"] = False
            _state["ended_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == "/refresh":
            with _lock:
                if _state["running"]:
                    return self._json(409, {"ok": False, "error": "이미 갱신 실행 중입니다."})
            if not BAT.exists():
                return self._json(500, {"ok": False, "error": f"{BAT.name} 가 없습니다."})
            t = threading.Thread(target=_run_bat, daemon=True)
            t.start()
            return self._json(200, {"ok": True, "message": "갱신을 시작했습니다."})
        self.send_error(404)

    def do_GET(self):
        if self.path.startswith("/refresh-status"):
            with _lock:
                snap = dict(_state)
            tail = ""
            if LOG.exists():
                try:
                    raw = LOG.read_text(encoding="utf-8", errors="replace")
                    tail = raw[-4000:]
                except Exception:
                    tail = ""
            return self._json(200, {**snap, "log_tail": tail})
        if self.path.startswith("/ohlcv/"):
            return self._serve_ohlcv()
        # 기본은 정적 파일 핸들러 (viewer.html, charts_forecast/, charts_math_forecast/)
        return super().do_GET()

    def _serve_ohlcv(self):
        ticker = self.path[len("/ohlcv/"):].split("?")[0].strip()
        if not (ticker.isdigit() and len(ticker) == 6):
            return self._json(400, {"error": "invalid ticker"})
        fp = ROOT / "data" / "ohlcv" / f"{ticker}.parquet"
        if not fp.exists():
            return self._json(404, {"error": "no ohlcv data", "ticker": ticker})
        try:
            import math

            import pandas as pd
            df = pd.read_parquet(fp).sort_values("date").reset_index(drop=True)
            if len(df) == 0:
                return self._json(404, {"error": "empty data", "ticker": ticker})
            import numpy as np
            close = df["close"]
            ma20 = close.rolling(20).mean()
            ma60 = close.rolling(60).mean()
            ma120 = close.rolling(120).mean()
            ma252 = close.rolling(252).mean()
            d_close = close.diff()
            up = d_close.clip(lower=0).rolling(14).mean()
            dn = (-d_close.clip(upper=0)).rolling(14).mean()
            rs = up / dn.replace(0, float("nan"))
            rsi14 = 100 - 100 / (1 + rs)
            # CCI20: Commodity Channel Index (Typical Price 기반)
            if "high" in df.columns and "low" in df.columns:
                tp = (df["high"] + df["low"] + close) / 3
            else:
                tp = close
            tp_ma20 = tp.rolling(20).mean()
            tp_md20 = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            cci20 = (tp - tp_ma20) / (0.015 * tp_md20.replace(0, float("nan")))

            def clean(s):
                return [None if (x is None or (isinstance(x, float) and math.isnan(x))) else float(x) for x in s.tolist()]

            payload = {
                "ticker": ticker,
                "date": [str(x)[:10] for x in df["date"].tolist()],
                "close": clean(close),
                "volume": clean(df["volume"]) if "volume" in df.columns else [],
                "ma20": clean(ma20),
                "ma60": clean(ma60),
                "ma120": clean(ma120),
                "ma252": clean(ma252),
                "rsi14": clean(rsi14),
                "cci20": clean(cci20),
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=300")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            return self._json(500, {"error": repr(e), "ticker": ticker})

    def log_message(self, format, *args):
        # 콘솔 잡음 줄이기
        pass


def main():
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/viewer.html"
    print(f"[OK] 로컬 서버 실행 중 — {url}")
    print("    Ctrl+C 로 종료")
    try:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[종료]")
        httpd.shutdown()


if __name__ == "__main__":
    main()
