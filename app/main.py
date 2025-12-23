import os
import sys
from flask import Flask, render_template, request, jsonify

# Adiciona o diretório raiz para importação de módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.data_service import DataService
from app.modules.optimization.solver import LotSizingSolver

app = Flask(__name__)

# Serviço de Dados (Singleton)
data_service = DataService()

def calculate_hours_per_period(capacity_params):
    """
    Calcula o total de horas disponíveis por máquina no período (mês médio).
    Fórmula: Turnos * Horas * Dias * 4.33 (semanas/mês)
    """
    if not capacity_params:
        return 720.0
        
    shifts = float(capacity_params.get('shifts_per_day', 3))
    hours_shift = float(capacity_params.get('hours_per_shift', 8))
    days_week = float(capacity_params.get('days_per_week', 7))
    
    return shifts * hours_shift * days_week * 4.33

def calculate_step_size(decision_type, bucket_hours, capacity_params):
    """
    Define a granularidade da variável de decisão (tamanho do passo H) e se é inteira.
    """
    shifts = float(capacity_params.get('shifts_per_day', 3))
    hours_shift = float(capacity_params.get('hours_per_shift', 8))
    days_week = float(capacity_params.get('days_per_week', 7))
    
    step_hours = 1.0
    integer_var = True
    
    if decision_type == 'kg':
        step_hours = 1.0
        integer_var = False
    elif decision_type == 'hours':
        step_hours = float(bucket_hours)
        integer_var = True
    elif decision_type == 'shifts':
        step_hours = hours_shift
        integer_var = True
    elif decision_type == 'days':
        step_hours = hours_shift * shifts
        integer_var = True
    elif decision_type == 'weeks':
        step_hours = hours_shift * shifts * days_week
        integer_var = True
        
    return step_hours, integer_var

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init-data', methods=['GET'])
def get_init_data():
    """
    Endpoint para carregar dados iniciais (datas disponíveis, máquinas).
    """
    data = data_service.get_initial_data()
    return jsonify(data)
    
@app.route('/api/run', methods=['POST'])
def run_optimization():
    """
    Endpoint principal de execução do solver.
    """
    data = request.json
    start_period = data.get('start_period')
    end_period = data.get('end_period')
    active_machines = data.get('active_machines', [])
    max_delay = int(data.get('max_delay', 0))
    coverage_months = float(data.get('coverage_months', 0.5))
    capacity_params = data.get('capacity_params', {})
    decision_type = data.get('decision_type', 'hours')
    bucket_hours = float(data.get('bucket_hours', 6.0))
    
    if not start_period or not active_machines:
        return jsonify({"error": "Parâmetros obrigatórios ausentes"}), 400
    
    # 1. Preparação de Dados
    hours_per_period = calculate_hours_per_period(capacity_params)
    step_hours, integer_var = calculate_step_size(decision_type, bucket_hours, capacity_params)
    
    demand, initial_inventory, productivity, costs = data_service.get_scenario_data(start_period, end_period)
    
    # 2. Execução do Solver
    solver = LotSizingSolver(
        demand=demand,
        productivity=productivity,
        initial_stock=initial_inventory,
        active_machines=active_machines,
        start_period=start_period,
        end_period=end_period,
        costs=costs,
        hours_per_period=hours_per_period,
        max_delay=max_delay,
        step_hours=step_hours,
        integer_var=integer_var,
        safety_stock_pct=coverage_months
    )
    result = solver.solve()
    
    # 3. Resposta
    if result['status'] != 'Optimal':
        return jsonify({"status": result['status'], "message": "Otimização falhou ou é inviável."})
        
    return jsonify({
        "status": result['status'],
        "inventory": result['inventory'],
        "production": result['production'],
        "setups": result.get('setups', []),
        "demand": result['demand'],
        "summary": result['summary'],
        "kpis": result.get('kpis', {})
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
