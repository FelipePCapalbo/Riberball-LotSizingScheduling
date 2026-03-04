#!/bin/bash
echo "Instalando dependencias Python..."
pip3 install -r requirements.txt

echo "Iniciando aplicacao..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 app/main.py
