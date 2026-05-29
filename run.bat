@echo off
if not exist .venv\Scripts\python.exe (
    echo Error: Virtual environment not found. Please run setup.bat first!
    pause
    exit /b 1
)

start "" .\.venv\Scripts\pythonw.exe main.py
