"""
Camada de apresentação: serve a interface e expõe os dados persistidos nos JSONs.
As rotas são finas — toda a lógica vive nos módulos processing/ e optimization/.
"""
import os
import sys
import time
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.data import DataService
from processing.settings import load_settings, save_settings
from processing.history import save_run, list_runs, get_run
from optimization.planner import run_plan

app = Flask(__name__)
data_service = DataService()


@app.route('/')
def index():
    return render_template('index.html')


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
    result = run_plan(settings)
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
    app.run(debug=True, port=5000)
