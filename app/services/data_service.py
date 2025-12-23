from app.modules.etl.loader import load_productivity, load_demand, load_inventory, load_costs
import pandas as pd

class DataService:
    """
    Serviço responsável pelo carregamento e cache dos dados do sistema.
    Implementa o padrão Singleton para evitar recarregamento desnecessário.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.productivity = None
        self.demand_dates = None
        self.demand = None
        self.inventory_dates = None
        self.inventory = None
        self.costs = None

    def load_all_data(self):
        """
        Carrega todos os dados se ainda não estiverem em cache.
        """
        if self.productivity is None:
            self.productivity = load_productivity()
            self.demand_dates, self.demand, _ = load_demand()
            self.inventory_dates, self.inventory = load_inventory()
            self.costs = load_costs()
            
    def get_initial_data(self):
        """
        Retorna os dados necessários para popular a interface (datas e máquinas).
        """
        self.load_all_data()
        
        machines = set()
        for p_map in self.productivity.values():
            for m in p_map.keys():
                machines.add(m)
        
        sorted_machines = sorted(list(machines), key=lambda x: int(x) if x.isdigit() else 999)
        
        return {
            "periods": self.demand_dates,
            "machines": sorted_machines
        }

    def get_scenario_data(self, start_period, end_period):
        """
        Prepara e recorta os dados de demanda e estoque para o horizonte solicitado.
        """
        self.load_all_data()
        
        local_dates = self.demand_dates[:]
        local_demand = {k: v.copy() for k, v in self.demand.items()}
        
        # Extensão de datas se o fim solicitado for além do disponível
        if end_period and end_period > local_dates[-1]:
            last_known_dt = pd.to_datetime(local_dates[-1])
            target_end_dt = pd.to_datetime(end_period)
            
            current_dt = last_known_dt
            while current_dt < target_end_dt:
                current_dt = current_dt + pd.DateOffset(months=1)
                new_date_str = str(current_dt)
                
                # Lógica simplificada de replicação do último valor conhecido
                # (Sazonalidade já foi tratada no loader, aqui é apenas fallback)
                for key in local_demand:
                    val_to_use = local_demand[key].get(local_dates[-1], 0)
                    local_demand[key][new_date_str] = val_to_use
                    
                local_dates.append(new_date_str)
        
        # Define estoque inicial baseado na data de início
        initial_inventory = {}
        for product, date_vals in self.inventory.items():
            sorted_inv_dates = sorted(date_vals.keys())
            init_val = 0
            for d in sorted_inv_dates:
                if d <= start_period:
                    init_val = date_vals[d]
                else:
                    break
            initial_inventory[product] = init_val
            
        return local_demand, initial_inventory, self.productivity, self.costs
