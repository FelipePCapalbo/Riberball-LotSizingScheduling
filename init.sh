#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual em .venv ..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Instalando dependências ..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared não encontrado no PATH."
    echo "Instale antes de continuar: brew install cloudflared (macOS) ou veja"
    echo "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
fi

if [ ! -f "backend/.env" ]; then
    echo "backend/.env não encontrado — copiando de backend/.env.example."
    cp backend/.env.example backend/.env
    echo "Edite backend/.env e preencha SHARED_SECRET (mesmo valor configurado no Worker) antes de rodar novamente."
    exit 1
fi

echo "Iniciando backend FastAPI (conectando ao frontend em riberball-lotsizingscheduling.felipecapalbo.workers.dev) ..."
python3 backend/app.py
