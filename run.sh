#!/bin/bash
echo "Instalando dependencias..."
pip3 install -r requirements.txt

echo "Iniciando aplicacao..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 app/main.py