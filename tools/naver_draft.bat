@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
python naver_draft.py %* >> "%USERPROFILE%\.nurse_jobs_naver\run.txt" 2>&1
