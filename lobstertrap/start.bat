@echo off
setlocal
cd /d "%~dp0"

echo.
echo  *** VaultIQ — Lobster Trap AI Governance Proxy ***
echo  Routing: Streamlit app -^> Lobster Trap (:8080) -^> Groq API
echo.

if not exist "lobstertrap.exe" (
    echo  [ERROR] lobstertrap.exe not found in this directory.
    echo.
    echo  Build from source (requires Go 1.22+):
    echo    git clone https://github.com/veeainc/lobstertrap
    echo    cd lobstertrap
    echo    make build-windows
    echo    copy lobstertrap.exe ..\lobstertrap\
    echo.
    pause
    exit /b 1
)

echo  Policy  : policy.yaml
echo  Audit   : audit.jsonl
echo  Listen  : http://localhost:8080
echo  Backend : https://api.groq.com/openai/v1
echo  Dashboard: http://localhost:8080/_lobstertrap/
echo.
echo  Press Ctrl+C to stop.
echo.

lobstertrap.exe serve ^
    --backend https://api.groq.com/openai/v1 ^
    --listen :8080 ^
    --policy policy.yaml ^
    --audit-log audit.jsonl
