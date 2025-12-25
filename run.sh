#!/bin/bash
echo "Verificando dependencias de sistema..."

# Função para verificar e instalar GLPK no macOS via Homebrew
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v glpsol &> /dev/null; then
        echo "GLPK não encontrado. Tentando instalar via Homebrew..."
        if command -v brew &> /dev/null; then
            brew install glpk
        else
            echo "ERRO: Homebrew não encontrado. Instale o GLPK manualmente (brew install glpk)."
        fi
    else
        echo "GLPK já instalado."
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v glpsol &> /dev/null; then
         echo "AVISO: GLPK não encontrado. Em Debian/Ubuntu, use: sudo apt-get install glpk-utils"
    fi
fi

echo "Instalando dependencias Python..."
pip3 install -r requirements.txt

echo "Iniciando aplicacao..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 app/main.py