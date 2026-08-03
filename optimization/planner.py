"""
Orquestração da otimização: une as configurações (JSON) e os dados (Excel),
instancia o solver e devolve o resultado. Ponto único usado pela web e pela CLI.
"""
from processing.data import DataService
from optimization.solver import LotSizingSolver
from optimization.color_problem import build_color_scheduling_problem
from optimization.scheduler_milp import solve_color_schedule_milp
from optimization.scheduler_heuristic import solve_color_schedule_heuristic


def run_tactical_plan(settings: dict, data_service: DataService):
    start_period = settings['start_period']
    end_period = settings.get('end_period')

    # Capacidade: horas/dia por máquina e dias úteis no mês médio (4.33 semanas)
    hours_per_day = float(settings['shifts_per_day']) * float(settings['hours_per_shift'])
    days_in_period = round(float(settings['days_per_week']) * 4.33)

    demand, initial_inventory, productivity, costs, machine_availability = data_service.get_scenario_data(
        start_period, end_period
    )

    all_periods = sorted(demand[list(demand.keys())[0]].keys()) if demand else []
    periods_in_scope = [
        p for p in all_periods
        if p >= start_period and (not end_period or p <= end_period)
    ]
    days_per_period = {t: days_in_period for t in periods_in_scope}

    solver = LotSizingSolver(
        demand=demand,
        productivity=productivity,
        initial_stock=initial_inventory,
        active_machines=settings['active_machines'],
        start_period=start_period,
        end_period=end_period,
        costs=costs,
        hours_per_day=hours_per_day,
        days_per_period=days_per_period,
        safety_stock_pct=int(settings.get('coverage_months', 0)),
        machine_availability=machine_availability,
        high_setup_machines=settings.get('high_setup_machines', []),
        setup_time_high=settings.get('setup_time_high'),
        setup_time_low=settings.get('setup_time_low'),
    )

    result = solver.solve(
        solver_name=settings.get('solver_name', 'CBC').upper(),
        time_limit=int(settings.get('time_limit', 600)),
        threads=settings.get('threads'),
    )

    return solver, result


def run_plan(settings: dict, data_service: DataService) -> dict:
    tactical_solver, result = run_tactical_plan(settings, data_service)
    return result


def run_color_plan(settings, data_service, tactical_solver):
    color_orders, color_initial_stock, color_setup_matrix = data_service.get_color_scenario_data()
    color_problem = build_color_scheduling_problem(
        tactical_solver, color_orders, color_initial_stock, color_setup_matrix,
        float(settings.get('setup_time_color_default', 1.0)),
    )

    color_method = settings.get('color_method', 'milp')
    if color_method == 'milp':
        color_result = solve_color_schedule_milp(
            color_problem,
            time_limit=int(settings.get('color_time_limit', 600)),
            solver_name=settings.get('color_solver_name', 'CBC').upper(),
            threads=settings.get('threads'),
        )
    elif color_method == 'heuristic':
        color_result = solve_color_schedule_heuristic(color_problem)

    return color_result
