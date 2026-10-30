@echo off
REM Quant Trading Hub dashboard: opens http://localhost:8502 . Reads / writes the hub database only.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import streamlit" 2>/dev/null || pip install -q -r requirements-lab.txt
python -m streamlit run app\hub.py --server.port 8502
pause
