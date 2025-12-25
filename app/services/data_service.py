import pandas as pd
from typing import Optional, Dict, List, Tuple
from app.modules.etl.loader import load_productivity, load_demand, load_inventory, load_costs

class DataService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataService, cls).__new__(cls)
            cls._instance._load_all_data()
        return cls._instance

    def _load_all_data(self):
        self.productivity = load_productivity()
        self.demand_dates, self.demand, _ = load_demand()
        self.inventory_dates, self.inventory = load_inventory()
        self.costs = load_costs()

    def get_initial_data(self) -> Dict:
        """Retorna dados iniciais para UI (datas e máquinas)."""
        machines = {m for p_map in self.productivity.values() for m in p_map.keys()}
        return {
            "periods": self.demand_dates,
            "machines": sorted(list(machines), key=lambda x: int(x) if x.isdigit() else 999)
        }

    def get_scenario_data(self, start_period: str, end_period: Optional[str] = None) -> Tuple[Dict, Dict, Dict, Dict]:
        """Prepara dados de demanda e estoque."""
        if not self.demand: return {}, {}, {}, {}

        local_demand = {k: v.copy() for k, v in self.demand.items()}
        
        # Extensão de datas se necessário
        if end_period and self.demand_dates and end_period > self.demand_dates[-1]:
            curr_dt, target_dt = pd.to_datetime(self.demand_dates[-1]), pd.to_datetime(end_period)
            while curr_dt < target_dt:
                curr_dt += pd.DateOffset(months=1)
                new_str = str(curr_dt)
                for k, v in local_demand.items():
                    v[new_str] = v.get(self.demand_dates[-1], 0)

        # Estoque inicial
        initial_inventory = {}
        for prod, date_vals in self.inventory.items():
            valid_dates = [d for d in date_vals if d <= start_period]
            initial_inventory[prod] = date_vals[max(valid_dates)] if valid_dates else 0.0
            
        return local_demand, initial_inventory, self.productivity, self.costs
