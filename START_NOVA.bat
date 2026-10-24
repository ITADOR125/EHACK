@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo Add your GROQ_API_KEY to .env, save the file and close Notepad.
  notepad .env
)
python demo.py
pause
