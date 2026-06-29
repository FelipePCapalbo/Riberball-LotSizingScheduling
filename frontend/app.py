"""
Camada de apresentação: serve a interface e expõe os dados persistidos nos JSONs.
As rotas são finas — toda a lógica vive nos módulos processing/ e optimization/.
"""
import os
import sys
import time
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.data import DataService, DATA_DIR, list_data_files
from processing.settings import load_settings, save_settings
from processing.history import save_run, list_runs, get_run
from optimization.planner import run_plan

app = Flask(__name__)

# Inicializa com o primeiro arquivo disponível
_available = list_data_files()
data_service = DataService(os.path.join(DATA_DIR, _available[0])) if _available else None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data-files', methods=['GET'])
def get_data_files():
    """Lista os arquivos de input disponíveis em data/ e qual está ativo."""
    files = list_data_files()
    active = os.path.basename(data_service.data_file) if data_service else None
    return jsonify({"files": files, "active": active})


@app.route('/api/set-data-file', methods=['POST'])
def set_data_file():
    """Recarrega o DataService com o arquivo selecionado."""
    global data_service
    filename = request.json.get('file', '')
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Arquivo não encontrado."}), 404
    data_service = DataService(path)
    return jsonify({"status": "loaded", "file": filename})


@app.route('/api/init-data', methods=['GET'])
def get_init_data():
    """Períodos disponíveis e lista de máquinas (vindos do Excel)."""
    return jsonify(data_service.get_initial_data())


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Configurações atuais persistidas nos JSONs."""
    return jsonify(load_settings())


@app.route('/api/settings', methods=['POST'])
def post_settings():
    """Persiste as configurações enviadas pela interface nos JSONs."""
    save_settings(request.json)
    return jsonify({"status": "saved"})


@app.route('/api/run', methods=['POST'])
def run_optimization():
    """Executa o solver lendo as configurações persistidas nos JSONs."""
    label = request.json.get('label', '') if request.json else ''
    settings = load_settings()

    t_start = time.perf_counter()
    result = run_plan(settings, data_service)
    duration = time.perf_counter() - t_start

    if result.get('status') not in ('Optimal', 'Feasible'):
        return jsonify({
            "status": result.get('status', 'Unknown'),
            "message": f"Otimização falhou ou é inviável. Status: {result.get('status')}"
        })

    run_id = save_run(settings, duration, result, label=label)

    payload = {k: result.get(k) for k in [
        'status', 'inventory', 'production', 'setups',
        'machine_stops', 'demand', 'summary', 'kpis'
    ] if result.get(k) is not None}
    payload['run_id'] = run_id
    payload['duration_seconds'] = round(duration, 2)
    return jsonify(payload)


@app.route('/api/history', methods=['GET'])
def get_history():
    """Lista metadados + KPIs de todas as execuções."""
    return jsonify(list_runs())


@app.route('/api/history/<run_id>', methods=['GET'])
def get_history_run(run_id):
    """Retorna o registro completo de uma execução."""
    record = get_run(run_id)
    if not record:
        return jsonify({"error": "not found"}), 404
    return jsonify(record)


if __name__ == '__main__':
    import threading
    import webbrowser

    HOST = '127.0.0.1'
    PORT = 5000

    threading.Thread(
        target=lambda: (webbrowser.open(f'http://{HOST}:{PORT}'), ),
        daemon=True
    ).start()

    print(f'Iniciando Riberball em http://{HOST}:{PORT} ...')
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
