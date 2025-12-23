@echo off
echo Instalando dependencias...
pip install -r requirements.txt

echo Iniciando aplicacao...
set PYTHONPATH=%PYTHONPATH%;%CD%
python app/main.py
pause