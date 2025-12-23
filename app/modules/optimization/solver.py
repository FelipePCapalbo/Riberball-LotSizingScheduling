import pulp
import pandas as pd
import math
from app.config import Config

class LotSizingSolver:
    """
    Classe responsável pela construção e resolução do modelo matemático de otimização (MILP).
    Otimiza o planejamento de produção minimizando custos de vendas perdidas, backlog e setup.
    """

    def __init__(self, demand, productivity, initial_stock, active_machines, 
                 start_period, end_period=None, costs=None,
                 hours_per_period=720, max_delay=0, step_hours=6.0, integer_var=True, safety_stock_pct=0.0):
        
        self.demand = demand
        self.productivity = productivity
        self.initial_stock = initial_stock
        self.active_machines = active_machines
        self.costs = costs or {}
        self.hours_per_period = hours_per_period
        self.max_delay = max_delay
        self.step_hours = step_hours
        self.integer_var = integer_var
        self.safety_stock_pct = safety_stock_pct 
        
        # --- Definição de Períodos ---
        self.products = list(demand.keys())
        all_dates = sorted(list(demand[self.products[0]].keys()))
        
        if end_period:
            self.periods = [d for d in all_dates if d >= start_period and d <= end_period]
        else:
            self.periods = [d for d in all_dates if d >= start_period]
            
        # --- Mapeamentos ---
        self.machine_products = {m: [] for m in active_machines}
        self.product_machines = {p: [] for p in self.products}
        
        for p in self.products:
            if p in productivity:
                for m, rate in productivity[p].items():
                    if m in active_machines:
                        self.machine_products[m].append(p)
                        self.product_machines[p].append(m)
        
        # --- Variáveis do Modelo Pulp ---
        self.prob = pulp.LpProblem("LotSizing", pulp.LpMinimize)
        
        # Variáveis de Decisão
        self.H_steps = {}
        self.Y = {}
        self.X_expr = {}
        self.S_state = {} 
        self.Delta_Setup = {} 
        self.Idle = {} 
        
        # Variáveis de Estado
        self.I = {}
        self.Q = {}
        self.K = {}
        self.B = {}
        
        # Termos da Função Objetivo
        self.terms_lost_sales = []
        self.terms_backlog = []
        self.terms_setup = []

    def solve(self):
        """
        Executa o pipeline completo de resolução: Definição -> Restrições -> Solve -> Formatação.
        """
        if not self.periods:
            return {"status": "No valid periods found"}

        self._define_variables()
        self._build_objective_function()
        self._add_constraints()
        
        # Resolução (com logs no terminal)
        self.prob.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=600))
        status = pulp.LpStatus[self.prob.status]
        
        if status != "Optimal":
            return {"status": status}
            
        return self._format_results(status)

    def _define_variables(self):
        """
        Inicializa todas as variáveis de decisão do modelo.
        """
        # --- Cálculo de Demanda Restante (Tight Big-M) ---
        remaining_demand = {}
        for p in self.products:
            d_list = [self.demand[p].get(t, 0) for t in self.periods]
            current_rem = 0
            for i in range(len(self.periods)-1, -1, -1):
                current_rem += d_list[i]
                remaining_demand[(p, i)] = current_rem

        # --- Definição de Variáveis de Produção ---
        var_cat = 'Integer' if self.integer_var else 'Continuous'
        
        max_steps_cap = int(self.hours_per_period / self.step_hours) if self.integer_var else (self.hours_per_period / self.step_hours)

        for m in self.active_machines:
            prods = self.machine_products[m]
            
            # Estado Persistente e Setup
            for p in prods:
                for t in self.periods:
                    self.S_state[(m, p, t)] = pulp.LpVariable(f"S_{m}_{p}_{t}", cat='Binary')
                    self.Delta_Setup[(m, p, t)] = pulp.LpVariable(f"Delta_{m}_{p}_{t}", cat='Binary')
            
            # Ociosidade
            for t in self.periods:
                self.Idle[(m, t)] = pulp.LpVariable(f"Idle_{m}_{t}", cat='Binary')

            # Produção por Produto
            for p in prods:
                rate = self.productivity[p][m]
                
                for t_idx, t in enumerate(self.periods):
                    # Tight Big-M Calculation
                    needed_qty = remaining_demand.get((p, t_idx), 0)
                    if rate > 0:
                        val_dem = needed_qty / (rate * self.step_hours)
                        ub_dem = int(math.ceil(val_dem)) if self.integer_var else val_dem
                    else:
                        ub_dem = 0
                    
                    max_steps = min(max_steps_cap, ub_dem)
                    
                    self.H_steps[(m, p, t)] = pulp.LpVariable(f"H_{m}_{p}_{t}", lowBound=0, upBound=max_steps, cat=var_cat)
                    self.Y[(m, p, t)] = pulp.LpVariable(f"Y_{m}_{p}_{t}", cat='Binary')
                    
                    hours_prod = self.H_steps[(m, p, t)] * self.step_hours
                    self.X_expr[(m, p, t)] = hours_prod * rate
                    
                    # Link Lógico: Se produz, Y=1
                    self.prob += self.H_steps[(m, p, t)] <= max_steps * self.Y[(m, p, t)]

        # --- Definição de Variáveis de Estoque ---
        for p in self.products:
            for t in self.periods:
                self.I[(p, t)] = pulp.LpVariable(f"I_{p}_{t}", lowBound=0)
                self.Q[(p, t)] = pulp.LpVariable(f"Q_{p}_{t}", lowBound=0) # Entregue
                self.K[(p, t)] = pulp.LpVariable(f"K_{p}_{t}", lowBound=0) # Venda Perdida
                if self.max_delay > 0:
                    self.B[(p, t)] = pulp.LpVariable(f"B_{p}_{t}", lowBound=0) # Backlog

    def _build_objective_function(self):
        """
        Constrói a função objetivo minimizando custos totais.
        """
        # 1. Custo de Venda Perdida
        for p in self.products:
            cost = self.costs.get(p, 0.0) 
            for t in self.periods:
                self.terms_lost_sales.append(cost * self.K[(p, t)])

        # 2. Custo de Backlog
        if self.max_delay > 0:
            for p in self.products:
                cost = self.costs.get(p, 0.0)
                penalty = cost * Config.BACKLOG_PENALTY_FACTOR
                for t in self.periods:
                    self.terms_backlog.append(penalty * self.B[(p, t)])

        # 3. Setup Otimizado
        for m in self.active_machines:
            setup_time_hours = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
            prods = self.machine_products[m]
            
            for t_idx, t in enumerate(self.periods):
                for p in prods:
                    delta = self.Delta_Setup[(m, p, t)]
                    c_p = self.costs.get(p, 0.0)
                    rate_p = self.productivity[p][m]
                    cost_val = c_p * rate_p * setup_time_hours
                    self.terms_setup.append(cost_val * delta)
                    
        self.prob += pulp.lpSum(self.terms_lost_sales + self.terms_backlog + self.terms_setup)

    def _add_constraints(self):
        """
        Adiciona as restrições físicas e lógicas ao modelo.
        """
        # --- 1. Restrições de Estado da Máquina ---
        for m in self.active_machines:
            for t in self.periods:
                # Apenas um produto configurado por vez
                self.prob += pulp.lpSum([self.S_state[(m, p, t)] for p in self.machine_products[m]]) == 1, f"OneState_{m}_{t}"

        # --- 2. Detecção de Setup (Delta) ---
        for m in self.active_machines:
            prods = self.machine_products[m]
            for t_idx, t in enumerate(self.periods):
                prev_t = self.periods[t_idx-1] if t_idx > 0 else None
                
                for p in prods:
                    curr_s = self.S_state[(m, p, t)]
                    prev_s = self.S_state[(m, p, prev_t)] if prev_t else 0
                    
                    # Custo de setup por mudança de estado final
                    self.prob += self.Delta_Setup[(m, p, t)] >= curr_s - prev_s, f"DeltaDef_{m}_{p}_{t}"
                    
                    # Custo de setup se houver produção e não era o estado anterior (Setup para produzir)
                    # Isso garante que se produzirmos múltiplos itens no mesmo período, pagamos setup
                    # exceto para aquele que já estava na máquina (carry-over).
                    self.prob += self.Delta_Setup[(m, p, t)] >= self.Y[(m, p, t)] - prev_s, f"DeltaProd_{m}_{p}_{t}"

        # --- 3. Link Lógico Y -> S (Setup Force) ---
        for m in self.active_machines:
            prods = self.machine_products[m]
            for t in self.periods:
                sum_y = pulp.lpSum([self.Y[(m, p, t)] for p in prods])
                n_prods = len(prods)
                
                # Definição de Ociosidade (Idle)
                self.prob += sum_y <= n_prods * (1 - self.Idle[(m, t)]), f"IdleDef_{m}_{t}"
                
                # Se Y=1, então S deve ser 1 (a menos que Idle)
                for p in prods:
                    self.prob += self.S_state[(m, p, t)] <= self.Y[(m, p, t)] + self.Idle[(m, t)], f"LinkSY_{m}_{p}_{t}"

        # --- 4. Restrições de Capacidade ---
        for m in self.active_machines:
            setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
            
            for t in self.periods:
                # Capacidade = Produção + Setup
                self.prob += pulp.lpSum([
                    self.H_steps[(m, p, t)] * self.step_hours + setup_time * self.Delta_Setup[(m, p, t)]
                    for p in self.machine_products[m]
                ]) <= self.hours_per_period, f"Cap_{m}_{t}"

        # --- 5. Backlog (Janela de Tempo) ---
        if self.max_delay > 0:
            for p in self.products:
                for t_idx, t in enumerate(self.periods):
                    start_window = max(0, t_idx - self.max_delay + 1)
                    window_sum = sum(self.demand[p].get(self.periods[k], 0) for k in range(start_window, t_idx + 1))
                    self.prob += self.B[(p, t)] <= window_sum

        # --- 6. Balanço de Estoque e Demanda ---
        for p in self.products:
            curr_initial = self.initial_stock.get(p, 0)
            for t_idx, t in enumerate(self.periods):
                prod_in = pulp.lpSum([self.X_expr[(m, p, t)] for m in self.product_machines[p]])
                prev_inv = curr_initial if t_idx == 0 else self.I[(p, self.periods[t_idx-1])]
                
                prev_back = 0
                curr_back = 0
                if self.max_delay > 0:
                    curr_back = self.B[(p, t)]
                    if t_idx > 0:
                        prev_back = self.B[(p, self.periods[t_idx-1])]
                
                d_val = self.demand[p].get(t, 0)
                
                # Equação de Balanço
                self.prob += prev_inv + prod_in + curr_back == \
                             self.I[(p, t)] + prev_back + d_val - self.K[(p, t)]
                
                # Definição de Quantidade Entregue (Q)
                backlog_change = 0
                if self.max_delay > 0:
                    if t_idx > 0:
                        backlog_change = self.B[(p, t)] - self.B[(p, self.periods[t_idx-1])]
                    else:
                        backlog_change = self.B[(p, t)]
                        
                self.prob += self.Q[(p, t)] == d_val - self.K[(p, t)] - backlog_change

                # Restrição de Estoque de Segurança (Forward Coverage)
                if self.safety_stock_pct > 0:
                    next_dem = 0
                    if t_idx + 1 < len(self.periods):
                        next_dem = self.demand[p].get(self.periods[t_idx+1], 0)
                    else:
                        next_dem = d_val # Fallback
                    
                    min_stock = next_dem * self.safety_stock_pct
                    self.prob += self.I[(p, t)] >= min_stock, f"SafetyStock_{p}_{t}"

    def _format_results(self, status):
        """
        Formata a saída do solver em DataFrames amigáveis.
        """
        res_inventory = []
        res_production = []
        res_demand = []
        res_setups = []
        
        total_inv_val = 0
        total_demand_val = 0
        total_met_val = 0
        
        for t_idx, t in enumerate(self.periods):
            # Resultados de Inventário e Demanda
            for p in self.products:
                inv_val = self.I[(p, t)].varValue
                total_inv_val += inv_val
                
                d_val = self.demand[p].get(t, 0)
                met_val = self.Q[(p, t)].varValue
                total_demand_val += d_val
                total_met_val += met_val
                
                fut_dem = 0
                if t_idx + 1 < len(self.periods):
                    fut_dem = self.demand[p].get(self.periods[t_idx+1], 0)
                
                res_inventory.append({
                    "Period": t,
                    "Product": f"{p[0]} {p[1]}",
                    "Inventory": inv_val,
                    "TargetInventory": fut_dem, 
                    "Shortage": 0.0
                })
                
                res_demand.append({
                    "Period": t,
                    "Product": f"{p[0]} {p[1]}",
                    "Demand": d_val,
                    "Met": met_val,
                    "Lost": self.K[(p, t)].varValue,
                    "Backlog": self.B[(p, t)].varValue if self.max_delay > 0 else 0
                })

            # Resultados de Produção
            for m in self.active_machines:
                # 1. Identificar Estado Anterior (From)
                prev_state_prod = "Início/Ocioso"
                if t_idx > 0:
                    prev_t = self.periods[t_idx-1]
                    for p_check in self.machine_products[m]:
                        if round(pulp.value(self.S_state[(m, p_check, prev_t)]) or 0) == 1:
                            prev_state_prod = f"{p_check[0]} {p_check[1]}"
                            break

                # 2. Identificar Setups e Estado Final
                current_period_setups = []
                final_state_prod = None

                for p in self.machine_products[m]:
                    if round(pulp.value(self.S_state[(m, p, t)]) or 0) == 1:
                        final_state_prod = p
                    
                    if round(pulp.value(self.Delta_Setup[(m, p, t)]) or 0) == 1:
                        current_period_setups.append(p)

                # 3. Gerar Registros de Setup Ordenados
                if current_period_setups:
                    # Separa o estado final dos intermediários para criar a cadeia
                    intermediaries = [p for p in current_period_setups if p != final_state_prod]
                    
                    # A lista ordenada termina com o estado final (se ele gerou setup)
                    ordered_chain = intermediaries
                    if final_state_prod in current_period_setups:
                        ordered_chain.append(final_state_prod)
                    
                    # Caso especial: Se houver setups mas o estado final não gerou setup (raro/impossível pela restrição Delta >= S - Prev)
                    # A menos que S seja igual a Prev, mas houve produção intermediária.
                    # Nesse caso, current_period_setups conteria apenas os intermediários.
                    
                    curr_from = prev_state_prod
                    for p_dest in ordered_chain:
                        res_setups.append({
                            "Period": t,
                            "Machine": m,
                            "From": curr_from,
                            "To": f"{p_dest[0]} {p_dest[1]}"
                        })
                        curr_from = f"{p_dest[0]} {p_dest[1]}"

                # 4. Dados de Produção (Mantido)
                for p in self.machine_products[m]:
                    val_steps = self.H_steps[(m, p, t)].varValue
                    if val_steps and val_steps > 0:
                        prod_hours = val_steps * self.step_hours
                        prod_qty = prod_hours * self.productivity[p][m]
                        res_production.append({
                            "Period": t,
                            "Machine": m,
                            "Product": f"{p[0]} {p[1]}",
                            "Quantity": prod_qty,
                            "Hours": prod_hours
                        })

        # Cálculos de KPIs
        total_demand_safe = total_demand_val if total_demand_val > 0 else 1.0
        service_level = (total_met_val / total_demand_safe) if total_demand_val > 0 else 1.0
        avg_inv = total_inv_val / len(self.periods) if self.periods else 0.0
        
        summary_data = []
        for t in self.periods:
            p_inv = sum(self.I[(p, t)].varValue for p in self.products)
            p_dem = sum(self.demand[p].get(t, 0) for p in self.products)
            p_lost = sum(self.K[(p, t)].varValue for p in self.products)
            
            p_prod = 0
            p_hours = 0
            for m in self.active_machines:
                setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
                
                for p in self.machine_products[m]:
                    # Recupera valores do solver (tratando None como 0)
                    steps_val = self.H_steps[(m, p, t)].varValue or 0
                    binary_setup = self.Delta_Setup[(m, p, t)].varValue or 0

                    # Limpeza numérica (0.999 -> 1, 0.001 -> 0)
                    is_setup = round(binary_setup)

                    # Cálculo direto de horas
                    prod_hours = steps_val * self.step_hours
                    
                    # Acumula totais
                    p_prod += prod_hours * self.productivity[p][m]
                    p_hours += prod_hours + (is_setup * setup_time)
            
            avail = self.hours_per_period * len(self.active_machines)
            util = (p_hours / avail) if avail > 0 else 0.0
            
            summary_data.append({
                "Period": t,
                "Inventory": p_inv,
                "Utilization": util,
                "Demand": p_dem,
                "Lost": p_lost,
                "Production": p_prod
            })

        cost_breakdown = {
            "lost_sales": sum(pulp.value(t) for t in self.terms_lost_sales),
            "backlog": sum(pulp.value(t) for t in self.terms_backlog),
            "setup": sum(pulp.value(t) for t in self.terms_setup)
        }
        
        def sanitize(val):
            if val is None: return 0.0
            if math.isnan(val) or math.isinf(val): return 0.0
            return float(val)

        print(f"Optimization Status: {status}")
        print(f"Total Cost: {pulp.value(self.prob.objective)}")
        
        return {
            "status": status,
            "inventory": pd.DataFrame(res_inventory).fillna(0.0).to_dict(orient='records'),
            "production": pd.DataFrame(res_production).fillna(0.0).to_dict(orient='records'),
            "setups": pd.DataFrame(res_setups).fillna("").to_dict(orient='records'),
            "demand": pd.DataFrame(res_demand).fillna(0.0).to_dict(orient='records'),
            "summary": pd.DataFrame(summary_data).fillna(0.0).to_dict(orient='records'),
            "kpis": {
                "service_level": sanitize(service_level),
                "avg_inventory": sanitize(avg_inv),
                "total_cost": sanitize(pulp.value(self.prob.objective)),
                "cost_breakdown": {k: sanitize(v) for k, v in cost_breakdown.items()}
            }
        }

def build_and_solve_model(**kwargs):
    """
    Wrapper para manter compatibilidade com a chamada antiga ou simplificar a API.
    """
    solver = LotSizingSolver(**kwargs)
    return solver.solve()
