import os
import sys
import traceback
from flask import Flask, render_template, request, jsonify

# Adiciona o diretório raiz para importação de módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.data_service import DataService
from app.modules.optimization.solver import LotSizingSolver
from app.utils import calculate_hours_per_period, calculate_step_size

app = Flask(__name__)

# Serviço de Dados (Singleton)
data_service = DataService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init-data', methods=['GET'])
def get_init_data():
    """Endpoint para carregar dados iniciais."""
    return jsonify(data_service.get_initial_data())

@app.route('/api/run', methods=['POST'])
def run_optimization():
    """Endpoint principal de execução do solver."""
    data = request.json
    start_period = data.get('start_period')
    solver_name = data.get('solver_name', 'CBC').upper()
    
    if not start_period or not data.get('active_machines'):
        return jsonify({"error": "Parâmetros obrigatórios ausentes"}), 400
    
    capacity_params = data.get('capacity_params', {})
    decision_type = data.get('decision_type', 'hours')
    bucket_hours = float(data.get('bucket_hours', 6.0))
    
    # 1. Preparação de Dados
    hours_per_period = calculate_hours_per_period(capacity_params)
    step_hours, integer_var = calculate_step_size(decision_type, bucket_hours, capacity_params)
    
    demand, initial_inventory, productivity, costs = data_service.get_scenario_data(
        start_period, data.get('end_period')
    )
    
    # 2. Execução do Solver
    solver_instance = LotSizingSolver(
        demand=demand,
        productivity=productivity,
        initial_stock=initial_inventory,
        active_machines=data.get('active_machines', []),
        start_period=start_period,
        end_period=data.get('end_period'),
        costs=costs,
        hours_per_period=hours_per_period,
        step_hours=step_hours,
        integer_var=integer_var,
        safety_stock_pct=float(data.get('coverage_months', 0.5)),
        vacation_planning=bool(data.get('vacation_planning', False)),
        operators_per_machine=int(data.get('operators_per_machine', 2))
    )
    
    try:
        result = solver_instance.solve(
            solver_name=solver_name,
            time_limit=int(data.get('time_limit', 600)),
            threads=data.get('threads')
        )
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Erro ao executar solver {solver_name}: {error_msg}\n{traceback.format_exc()}")
        
        # Mensagem mais amigável para falha do Gurobi
        if solver_name == 'GUROBI' and ('license' in error_msg.lower() or 'gurobi' in error_msg.lower()):
            return jsonify({
                "status": "Error",
                "message": f"Falha ao inicializar o Gurobi. Verifique se a licença está ativa e o solver instalado. Detalhe: {error_msg}"
            }), 500
        
        return jsonify({
            "status": "Error",
            "message": f"Erro interno ao executar o solver {solver_name}: {error_msg}"
        }), 500
    
    # 3. Resposta — aceita Optimal e Feasible (solução válida por timeout)
    valid_statuses = ('Optimal', 'Feasible')
    if result.get('status') not in valid_statuses:
        return jsonify({
            "status": result.get('status', 'Unknown'),
            "message": f"Otimização falhou ou é inviável. Status: {result.get('status')}"
        })
        
    return jsonify({k: result.get(k) for k in [
        'status', 'inventory', 'production', 'setups', 'vacations', 'demand', 'summary', 'kpis'
    ] if result.get(k) is not None})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
