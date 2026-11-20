@echo off
rem 네이버 블로그 임시저장 (작업 스케줄러에서 이 파일을 실행)
chcp 65001 >nul
cd /d "%~dp0"
python naver_draft.py %*
