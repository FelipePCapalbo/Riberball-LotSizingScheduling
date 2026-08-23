#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

unset PYTHONHOME
unset PYTHONPATH
unset PYTHONSTARTUP
export PYTHONNOUSERSITE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_REQUIRE_VIRTUALENV=1

WORKER_URL="https://riberball-lotsizingscheduling.felipecapalbo.workers.dev"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
PROBE='import sys, venv, ensurepip; assert sys.version_info[:2] in ((3,10),(3,11),(3,12),(3,13)); assert sys.maxsize.bit_length() == 63'

echo
echo "Riberball - planejamento semanal e programacao por turno"
echo

case "$(uname -s)" in
    Linux)
        CLOUDFLARED_ASSET="cloudflared-linux-amd64"
        ;;
    Darwin)
        CLOUDFLARED_ASSET="cloudflared-darwin-amd64.tgz"
        ;;
    *)
        echo "Sistema nao suportado: $(uname -s)"
        exit 1
        ;;
esac

if [ "$(uname -m)" != "x86_64" ]; then
    echo "Esta maquina nao e x86_64 ($(uname -m))."
    echo "Baixe o binario do cloudflared para a sua arquitetura e coloque nesta pasta como ./cloudflared."
    echo
fi

echo "[1/5] Procurando um Python compativel ..."

BASE_PYTHON=""
for str_candidate in python3.12 python3.13 python3.11 python3.10 python3; do
    if [ -z "$BASE_PYTHON" ]; then
        if command -v "$str_candidate" >/dev/null 2>&1; then
            if "$str_candidate" -E -s -c "$PROBE" >/dev/null 2>&1; then
                BASE_PYTHON="$str_candidate"
            fi
        fi
    fi
done

if [ -z "$BASE_PYTHON" ]; then
    echo
    echo "Nenhum Python compativel foi encontrado nesta maquina."
    echo "Requisitos: versao 3.10 a 3.13, 64 bits, com os modulos venv e ensurepip."
    echo "Em Debian/Ubuntu/Mint pode faltar o pacote do venv:"
    echo "    sudo apt install python3-venv"
    echo
    exit 1
fi

echo "      Python base: $BASE_PYTHON"

echo "[2/5] Preparando o ambiente isolado em .venv ..."

bool_venv_ok=0
if [ -x "$VENV_PYTHON" ]; then
    if "$VENV_PYTHON" -E -s -c "import sys, pip" >/dev/null 2>&1; then
        bool_venv_ok=1
    fi
fi

if [ "$bool_venv_ok" -eq 0 ]; then
    if [ -d ".venv" ]; then
        echo "      ambiente anterior invalido (o Python base mudou) - recriando"
        rm -rf ".venv"
    fi
    "$BASE_PYTHON" -E -s -m venv ".venv"
fi

echo "[3/5] Conferindo as dependencias ..."

bool_need_install=1
if [ -f ".venv/requirements.stamp" ]; then
    if cmp -s "requirements.txt" ".venv/requirements.stamp"; then
        bool_need_install=0
    fi
fi

if [ "$bool_need_install" -eq 0 ]; then
    echo "      ja instaladas"
else
    if [ -d "wheels" ]; then
        echo "      instalando a partir de wheels/ (offline)"
        "$VENV_PYTHON" -E -s -m pip install --quiet --no-index --find-links "wheels" -r "requirements.txt"
    else
        echo "      baixando do PyPI (so na primeira execucao)"
        "$VENV_PYTHON" -E -s -m pip install --quiet -r "requirements.txt"
    fi
    cp "requirements.txt" ".venv/requirements.stamp"
fi

echo "[4/5] Conferindo o cloudflared ..."

if [ -x "./cloudflared" ]; then
    echo "      ja presente nesta pasta"
else
    echo "      baixando cloudflared para esta pasta"
    rm -f "./cloudflared.part"
    curl -fL --progress-bar -o "./cloudflared.part" \
        "https://github.com/cloudflare/cloudflared/releases/latest/download/$CLOUDFLARED_ASSET"
    chmod +x "./cloudflared.part"
    mv "./cloudflared.part" "./cloudflared"
fi

if [ ! -f "backend/.env" ]; then
    echo
    echo "backend/.env nao encontrado."
    echo "Copie para backend/.env o arquivo de configuracao enviado junto com o sistema"
    echo "(ou parta de backend/.env.example e preencha SHARED_SECRET)."
    echo
    exit 1
fi

echo "[5/5] Iniciando o backend e abrindo a interface ..."
echo
echo "      Interface: $WORKER_URL"
echo "      Ctrl+C encerra o sistema."
echo

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$WORKER_URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "$WORKER_URL" >/dev/null 2>&1 &
fi

exec "$VENV_PYTHON" -E -s -X utf8 "backend/app.py"
