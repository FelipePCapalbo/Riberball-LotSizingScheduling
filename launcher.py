"""
Entrypoint do executável .exe — inicia o servidor Flask e abre o navegador.

Os módulos Python (frontend, processing, optimization) ficam como pacotes na
raiz do projeto. Este arquivo é o único empacotado como executável.
"""
import sys
import os
import threading
import time
import webbrowser

# Garante que os logs do solver (CBC/Gurobi) apareçam no terminal sem buffering
os.environ['PYTHONUNBUFFERED'] = '1'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# ---------------------------------------------------------------------------
# Resolução de caminhos para modo congelado (PyInstaller) e modo script normal
# ---------------------------------------------------------------------------
def get_base_dir() -> str:
    """Retorna o diretório raiz da aplicação."""
    if getattr(sys, 'frozen', False):
        # Executando como .exe gerado pelo PyInstaller
        return os.path.dirname(sys.executable)
    # Executando como script Python normal
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()

# Garante que os pacotes da raiz do projeto sejam encontrados pelo Python
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# Configuração do Flask e inicialização
# ---------------------------------------------------------------------------
HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def open_browser():
    """Aguarda o servidor inicializar e abre o navegador padrão."""
    time.sleep(1.5)
    webbrowser.open(URL)


def main():
    # Importa a app Flask — os pacotes precisam estar no sys.path
    try:
        from frontend.app import app
    except ImportError as exc:
        print(
            f"[ERRO] Não foi possível importar a aplicação Flask.\n"
            f"Verifique se os pacotes 'frontend/', 'processing/' e 'optimization/' "
            f"estão no mesmo diretório que o executável.\n"
            f"Detalhe: {exc}"
        )
        input("\nPressione ENTER para fechar...")
        sys.exit(1)

    # Abre o navegador em paralelo (não bloqueia o servidor)
    threading.Thread(target=open_browser, daemon=True).start()

    print(f"Iniciando Riberball Lot Sizing em {URL} ...")
    print("Feche esta janela para encerrar o servidor.\n")

    # Roda em modo produção (debug=False) — essencial para o .exe
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
