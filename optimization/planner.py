"""
Orquestração da otimização: une as configurações (JSON) e os dados (Excel),
instancia o solver e devolve o resultado. Ponto único usado pela web e pela CLI.
"""
from processing.data import DataService
from optimization.solver import LotSizingSolver


def run_plan(settings: dict, data_service: DataService) -> dict:
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

    return solver.solve(
        solver_name=settings.get('solver_name', 'CBC').upper(),
        time_limit=int(settings.get('time_limit', 600)),
        threads=settings.get('threads'),
    )
