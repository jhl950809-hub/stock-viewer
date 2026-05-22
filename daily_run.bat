@echo off
REM 매일 오후 7시(장 마감 후) 실행 추천
REM 데이터 → 학습 → 차트 → HTML 순서로 자동 갱신
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo [%date% %time%] === 일별 갱신 시작 ===

echo.
echo [1/5] 시세 데이터 증분 업데이트
py update_daily.py
if errorlevel 1 (echo [FAIL] update_daily.py & exit /b 1)

echo.
echo [2/5] 특성 캐시 재계산 + 20d 자체학습 모델 (features_upside.parquet 생성)
py auto_ml.py
if errorlevel 1 (echo [FAIL] auto_ml.py & exit /b 1)

echo.
echo [3/5] 다기간 모델 재학습 + 예측 (60/120/240d)
py multi_horizon.py
if errorlevel 1 (echo [FAIL] multi_horizon.py & exit /b 1)

echo.
echo [4/5] 정적 OHLCV JSON 익스포트 (ohlcv/*.json — GitHub Pages 배포용)
py export_ohlcv_json.py
if errorlevel 1 (echo [FAIL] export_ohlcv_json.py & exit /b 1)

echo.
echo [5/5] HTML 대시보드 갱신
py make_html.py
if errorlevel 1 (echo [FAIL] make_html.py & exit /b 1)

echo.
echo [%date% %time%] === 일별 갱신 완료 ===
