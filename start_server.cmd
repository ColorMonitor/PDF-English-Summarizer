@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -u manage.py runserver 127.0.0.1:8000 --noreload >> "%~dp0server.out.log" 2>> "%~dp0server.err.log"
