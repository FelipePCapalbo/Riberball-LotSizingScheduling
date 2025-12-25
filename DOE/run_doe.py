import json
import itertools
import pandas as pd
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_service import DataService
from app.modules.optimization.solver import LotSizingSolver
from app.utils import calculate_step_size, calculate_hours_per_period
from app.config import Config

def run_doe(config_file='DOE/config_doe.json', output_file='DOE/doe_results.csv'):
    print(f"Loading configuration from {config_file}...")
    with open(config_file, 'r') as f:
        config = json.load(f)

    scenarios = config.get('scenarios', {})
    fixed = config.get('fixed_params', {})
    combinations = [dict(zip(scenarios.keys(), v)) for v in itertools.product(*scenarios.values())]
    
    print(f"Found {len(combinations)} combinations to run.")

    data_service = DataService()
    start_period = fixed.get('start_period')
    demand, initial_inventory, productivity, costs = data_service.get_scenario_data(start_period, fixed.get('end_period'))
    
    results = []
    
    for i, current_params in enumerate(combinations):
        print(f"\nRunning Scenario {i+1}/{len(combinations)}: {current_params}")
        
        run_params = {**fixed, **current_params}
        capacity_params = run_params.get('capacity_params', {}).copy()
        capacity_params.update({k: v for k, v in current_params.items() if k in capacity_params})
        run_params['capacity_params'] = capacity_params

        # Calculate parameters
        operators = int(run_params.get('operators_per_machine', 2))
        hours_per_period = float(current_params.get('hours_per_period', calculate_hours_per_period(capacity_params)))
        step_hours, integer_var = calculate_step_size(
            run_params.get('decision_type', 'hours'),
            run_params.get('bucket_hours', 6.0),
            capacity_params
        )

        solver_name = run_params.get('solver_name', 'CBC')

        solver = LotSizingSolver(
            demand=demand, productivity=productivity, initial_stock=initial_inventory,
            active_machines=run_params.get('active_machines', []),
            start_period=start_period, end_period=run_params.get('end_period'),
            costs=costs, hours_per_period=hours_per_period, step_hours=step_hours,
            integer_var=integer_var, safety_stock_pct=float(run_params.get('safety_stock_pct', 0.0)),
            vacation_planning=(operators > 0), operators_per_machine=operators
        )
        
        start_time = time.time()
        # threads=None will let solver use max threads available
        result = solver.solve(
            time_limit=int(run_params.get('time_limit', 600)),
            log_path=f"logs/doe_run_{i}.log",
            solver_name=solver_name,
            threads=None 
        )
        elapsed = time.time() - start_time
        
        # Metrics
        kpis = result.get('kpis', {})
        summary_df = pd.DataFrame(result.get('summary', []))
        demand_df = pd.DataFrame(result.get('demand', []))
        
        # Setup calculation
        total_setup_hours = sum(
            Config.DEFAULT_SETUP_TIME_HIGH if str(s.get('Machine')) in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
            for s in result.get('setups', [])
        )

        row = {
            "Scenario_ID": i,
            **current_params,
            "Status": result['status'],
            "Objective_Cost": kpis.get('total_cost', 0.0),
            "Service_Level": kpis.get('service_level', 0.0),
            "Total_Lost_Demand_kg": demand_df['Lost'].sum() if not demand_df.empty else 0.0,
            "Avg_Inventory": kpis.get('avg_inventory', 0.0),
            "Avg_Utilization": summary_df['Utilization'].mean() if not summary_df.empty else 0.0,
            "Total_Setup_Hours": total_setup_hours,
            "Elapsed_Time": round(elapsed, 2)
        }
        
        results.append(row)
        pd.DataFrame(results).to_csv(output_file, index=False)
        print(f"Result: {result['status']}, Cost: {row['Objective_Cost']}")

    print(f"\nDOE Completed. Results saved to {output_file}")

if __name__ == "__main__":
    run_doe()

