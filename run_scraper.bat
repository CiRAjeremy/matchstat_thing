@echo off
REM Matchstat Scraper - Automated Run Script
REM This script activates the venv and runs the scraper

cd /d C:\-\TO-DO\matchstat_thing
call venv\Scripts\activate
python -m src.scrapers.matchstat_selenium
pause
