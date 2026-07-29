"""
Launcher: abre o navegador e sobe o servidor uvicorn com a app FastAPI.

Uso:
    python run_app.py
"""
import threading
import webbrowser

import uvicorn

HOST = '127.0.0.1'
PORT = 5000


def main():
    threading.Thread(
        target=lambda: (webbrowser.open(f'http://{HOST}:{PORT}'), ),
        daemon=True
    ).start()

    print(f'Iniciando Riberball em http://{HOST}:{PORT} ...')
    uvicorn.run('backend.main:app', host=HOST, port=PORT, reload=False)


if __name__ == '__main__':
    main()
