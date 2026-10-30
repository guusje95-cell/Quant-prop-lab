@echo off
REM HyroTrader Hyro-platform MCP PROBE: lists the server's tools with a READ-ONLY agent token. Calls no tool, places no orders.
REM Create the token in HyroTrader -> Settings -> Agent tokens (2FA needed) WITH READ ACCESS ONLY. Never paste it in chat or a file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import mcp" 2>nul || pip install -q mcp
set /p HYRO_MCP_URL=MCP server URL (from HyroTrader's agent-token / MCP setup page): 
set /p HYRO_AGENT_TOKEN=Read-only agent token (stays in this window only): 
python -m qpl.bot.venue_hyro
git pull --no-rebase --no-edit
git add paper_trading/hyro_probe
git commit -m "Hyro MCP probe (tool list, no token)"
git push
pause
