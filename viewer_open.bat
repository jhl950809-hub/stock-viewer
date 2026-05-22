@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

REM 포트 8765가 이미 LISTENING 상태인지 확인
netstat -ano | find "8765" | find "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] 서버 이미 실행 중 — 브라우저를 엽니다
    start "" "http://127.0.0.1:8765/viewer.html"
    timeout /t 2 /nobreak >nul
    exit /b 0
)

REM 서버 미실행 → 최소화 창으로 백그라운드 실행
echo [INFO] 서버 시작 중...
start /min "주식뷰어 서버 (닫지 마세요)" cmd /c "chcp 65001 >nul && set PYTHONIOENCODING=utf-8 && py viewer_server.py"

REM 서버 기동 대기 (최대 8초)
set /a cnt=0
:wait
timeout /t 1 /nobreak >nul
netstat -ano | find "8765" | find "LISTENING" >nul 2>&1
if %errorlevel% == 0 goto ready
set /a cnt+=1
if %cnt% lss 8 goto wait

echo [WARN] 서버 응답 없음 — Python 설치 또는 viewer_server.py 확인 필요
pause
exit /b 1

:ready
echo [OK] 서버 준비 완료 — 브라우저를 엽니다
start "" "http://127.0.0.1:8765/viewer.html"
echo.
echo 이 창은 닫으셔도 됩니다. (서버는 백그라운드에서 계속 실행됩니다)
echo 서버를 완전히 종료하려면 작업 관리자에서 "주식뷰어 서버" 창을 닫으세요.
timeout /t 3 /nobreak >nul
