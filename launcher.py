"""
Entrypoint do executável .exe — inicia o servidor Flask e abre o navegador.

Os demais módulos Python (solver, ETL, etc.) continuam como arquivos .py
na pasta da aplicação. Este arquivo é o único empacotado como executável.
"""
import sys
import os
import threading
import time
import webbrowser

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

# Garante que os módulos da pasta 'app/' sejam encontrados pelo Python
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
    # Importa a app Flask — os módulos 'app/' precisam estar no sys.path
    try:
        from app.main import app
    except ImportError as exc:
        print(
            f"[ERRO] Não foi possível importar a aplicação Flask.\n"
            f"Verifique se a pasta 'app/' está no mesmo diretório que o executável.\n"
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
