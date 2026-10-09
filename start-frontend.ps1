$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'frontend')
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
