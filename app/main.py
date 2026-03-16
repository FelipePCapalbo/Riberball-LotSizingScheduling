import os
import sys
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_service import DataService
from app.modules.optimization.solver import LotSizingSolver
from app.utils import calculate_hours_per_day, calculate_days_in_period, calculate_step_size

app = Flask(__name__)

data_service = DataService()


def _convert_ranges_to_day_indices(ranges_by_machine, periods, days_per_period):
    """
    Converte intervalos de datas {machine: [{start, end}, ...]} em
    set de (machine, day_index) compatível com o solver.

    Cada período (mês) tem n_t dias úteis indexados sequencialmente.
    Uma data calendário dentro do mês M é mapeada ao dia útil proporcional:
      day_index_global = cumulative_days_before_period + floor((cal_day / cal_days_in_month) * n_t)
    """
    stop_set = set()
    if not ranges_by_machine or not periods:
        return stop_set

    period_info = []
    cum_day = 0
    for t in periods:
        date_str = t.split(' ')[0]
        year, month = int(date_str[:4]), int(date_str[5:7])
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime(year, month + 1, 1)
        month_start = datetime(year, month, 1)
        cal_days = (next_month_start - month_start).days

        n_t = days_per_period.get(t, 30)
        period_info.append({
            'period': t,
            'month_start': month_start,
            'cal_days': cal_days,
            'n_t': n_t,
            'cum_day': cum_day
        })
        cum_day += n_t

    for machine, ranges in ranges_by_machine.items():
        if not ranges:
            continue
        for rng in ranges:
            try:
                r_start = datetime.strptime(rng['start'], '%Y-%m-%d')
                r_end = datetime.strptime(rng['end'], '%Y-%m-%d')
            except (ValueError, KeyError):
                continue
            if r_end < r_start:
                r_start, r_end = r_end, r_start

            for pi in period_info:
                ms = pi['month_start']
                me = ms + timedelta(days=pi['cal_days'] - 1)

                overlap_start = max(r_start, ms)
                overlap_end = min(r_end, me)
                if overlap_start > overlap_end:
                    continue

                for day_offset in range((overlap_end - overlap_start).days + 1):
                    cal_date = overlap_start + timedelta(days=day_offset)
                    day_in_month = (cal_date - ms).days
                    working_day = int(day_in_month * pi['n_t'] / pi['cal_days'])
                    working_day = min(working_day, pi['n_t'] - 1)
                    global_idx = pi['cum_day'] + working_day
                    stop_set.add((machine, global_idx))

    return stop_set


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

    hours_per_day = calculate_hours_per_day(capacity_params)
    days_in_period = calculate_days_in_period(capacity_params)
    step_hours, integer_var = calculate_step_size(decision_type, bucket_hours, capacity_params)

    demand, initial_inventory, productivity, costs = data_service.get_scenario_data(
        start_period, data.get('end_period')
    )

    active_machines = data.get('active_machines', [])

    all_periods = sorted(demand[list(demand.keys())[0]].keys()) if demand else []
    end_period = data.get('end_period')
    periods_in_scope = [
        p for p in all_periods
        if p >= start_period and (not end_period or p <= end_period)
    ]

    days_per_period = {t: days_in_period for t in periods_in_scope}

    manual_stops_ranges = data.get('manual_stops_ranges', {})
    manual_stops = _convert_ranges_to_day_indices(
        manual_stops_ranges, periods_in_scope, days_per_period
    )

    num_operators = int(data.get('num_operators', 0))
    operators_per_machine = int(data.get('operators_per_machine', 1))
    num_operators_on_vacation = int(data.get('num_operators_on_vacation', 0))
    vacation_days = int(data.get('vacation_days', 0))

    solver_instance = LotSizingSolver(
        demand=demand,
        productivity=productivity,
        initial_stock=initial_inventory,
        active_machines=active_machines,
        start_period=start_period,
        end_period=end_period,
        costs=costs,
        hours_per_day=hours_per_day,
        days_per_period=days_per_period,
        step_hours=step_hours,
        integer_var=integer_var,
        safety_stock_pct=float(data.get('coverage_months', 0.5)),
        manual_stops=manual_stops,
        num_operators=num_operators,
        operators_per_machine=operators_per_machine,
        num_operators_on_vacation=num_operators_on_vacation,
        vacation_days=vacation_days
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

        if solver_name == 'GUROBI' and ('license' in error_msg.lower() or 'gurobi' in error_msg.lower()):
            return jsonify({
                "status": "Error",
                "message": f"Falha ao inicializar o Gurobi. Verifique se a licença está ativa e o solver instalado. Detalhe: {error_msg}"
            }), 500

        return jsonify({
            "status": "Error",
            "message": f"Erro interno ao executar o solver {solver_name}: {error_msg}"
        }), 500

    valid_statuses = ('Optimal', 'Feasible')
    if result.get('status') not in valid_statuses:
        return jsonify({
            "status": result.get('status', 'Unknown'),
            "message": f"Otimização falhou ou é inviável. Status: {result.get('status')}"
        })

    return jsonify({k: result.get(k) for k in [
        'status', 'inventory', 'production', 'setups', 'vacations',
        'machine_stops', 'demand', 'summary', 'kpis'
    ] if result.get(k) is not None})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
