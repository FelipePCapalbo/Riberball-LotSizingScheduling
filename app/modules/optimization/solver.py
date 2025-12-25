import pulp
import pandas as pd
import os
import math
from app.config import Config
from app.utils import sanitize_name

class LotSizingSolver:
    """Solver MILP para planejamento de produção."""

    def __init__(self, demand, productivity, initial_stock, active_machines, 
                 start_period, end_period=None, costs=None,
                 hours_per_period=720, step_hours=6.0, integer_var=True, safety_stock_pct=0.0,
                 vacation_planning=False, operators_per_machine=2):
        
        self.demand = demand
        self.productivity = productivity
        self.initial_stock = initial_stock
        self.active_machines = active_machines
        self.costs = costs or {}
        
        self.hours_per_period = hours_per_period
        self.step_hours = step_hours
        self.integer_var = integer_var
        self.safety_stock_pct = safety_stock_pct
        self.vacation_planning = vacation_planning
        self.operators_per_machine = operators_per_machine 
        
        self.products = list(demand.keys())
        all_dates = sorted(demand[self.products[0]].keys()) if self.products else []
        self.periods = [d for d in all_dates if d >= start_period and (not end_period or d <= end_period)]
        
        self._map_machine_products()
        self.prob = pulp.LpProblem("LotSizing", pulp.LpMinimize)

    def _map_machine_products(self):
        self.machine_products = {m: [] for m in self.active_machines}
        self.product_machines = {p: [] for p in self.products}
        
        for p in self.products:
            if p not in self.productivity: continue
            for m, rate in self.productivity[p].items():
                if m in self.active_machines:
                    self.machine_products[m].append(p)
                    self.product_machines[p].append(m)

    def solve(self, time_limit=600, log_path=None, solver_name='CBC', threads=None):
        if not self.periods: return {"status": "No valid periods found"}

        self._define_variables()
        self._build_objective_function()
        self._add_constraints()
        
        solver = self._get_solver_instance(solver_name, time_limit, log_path, threads)
        self.prob.solve(solver)
        
        return self._format_results(pulp.LpStatus[self.prob.status])

    def _get_solver_instance(self, name, time_limit, log_path, threads=None):
        name = name.upper()
        if name == 'GUROBI':
            opts = [("TimeLimit", time_limit)]
            if log_path: opts.append(("LogFile", log_path))
            if threads: opts.append(("Threads", threads))
            return pulp.GUROBI_CMD(msg=1, options=opts)
        
        if name == 'GLPK':
            opts = [f"--log {log_path}"] if log_path else []
            return pulp.GLPK_CMD(msg=1, timeLimit=time_limit, options=opts)
            
        # CBC is the default for 'CBC' and fallback for others
        args = dict(msg=1, timeLimit=time_limit, logPath=log_path)
        if threads: args['threads'] = threads
        return pulp.PULP_CBC_CMD(**args)

    def _define_variables(self):
        self.vars = {}
        max_steps = int(self.hours_per_period / self.step_hours) + 1
        var_cat = 'Integer' if self.integer_var else 'Continuous'

        # Variables containers
        self.H_steps, self.Y, self.S_state, self.Delta_Setup, self.Idle = {}, {}, {}, {}, {}
        self.I, self.Q, self.K = {}, {}, {}

        for m in self.active_machines:
            for t in self.periods:
                safe_t = sanitize_name(t)
                self.Idle[(m, t)] = pulp.LpVariable(f"Idle_{m}_{safe_t}", cat='Binary')
                
                for p in self.machine_products[m]:
                    safe_p = sanitize_name(f"{p[0]}_{p[1]}")
                    key = (m, p, t)
                    
                    self.S_state[key] = pulp.LpVariable(f"S_{m}_{safe_p}_{safe_t}", cat='Binary')
                    self.Delta_Setup[key] = pulp.LpVariable(f"Delta_{m}_{safe_p}_{safe_t}", cat='Binary')
                    self.Y[key] = pulp.LpVariable(f"Y_{m}_{safe_p}_{safe_t}", cat='Binary')
                    self.H_steps[key] = pulp.LpVariable(f"H_{m}_{safe_p}_{safe_t}", lowBound=0, upBound=max_steps, cat=var_cat)
                    
                    self.prob += self.H_steps[key] <= max_steps * self.Y[key]

        for p in self.products:
            safe_p = sanitize_name(f"{p[0]}_{p[1]}")
            for t in self.periods:
                safe_t = sanitize_name(t)
                key = (p, t)
                self.I[key] = pulp.LpVariable(f"I_{safe_p}_{safe_t}", lowBound=0)
                self.Q[key] = pulp.LpVariable(f"Q_{safe_p}_{safe_t}", lowBound=0)
                self.K[key] = pulp.LpVariable(f"K_{safe_p}_{safe_t}", lowBound=0)

    def _build_objective_function(self):
        lost_sales = [self.costs.get(p, 0.0) * self.K[(p, t)] for p in self.products for t in self.periods]
        
        setup_costs = []
        for m in self.active_machines:
            setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
            for p in self.machine_products[m]:
                cost = self.costs.get(p, 0.0) * self.productivity[p][m] * setup_time
                setup_costs.extend([cost * self.Delta_Setup[(m, p, t)] for t in self.periods])
                
        self.prob += pulp.lpSum(lost_sales + setup_costs)

    def _add_constraints(self):
        for m in self.active_machines:
            setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
            
            for t_idx, t in enumerate(self.periods):
                prods = self.machine_products[m]
                prev_t = self.periods[t_idx-1] if t_idx > 0 else None
                
                # 1. Machine State & Idle
                self.prob += pulp.lpSum([self.S_state[(m, p, t)] for p in prods]) == 1
                self.prob += pulp.lpSum([self.Y[(m, p, t)] for p in prods]) <= len(prods) * (1 - self.Idle[(m, t)])
                
                usage = []
                for p in prods:
                    # 2. Setup Logic
                    curr_s = self.S_state[(m, p, t)]
                    prev_s = self.S_state[(m, p, prev_t)] if prev_t else 0
                    
                    self.prob += self.Delta_Setup[(m, p, t)] >= curr_s - prev_s
                    self.prob += self.Delta_Setup[(m, p, t)] >= self.Y[(m, p, t)] - prev_s
                    self.prob += curr_s <= self.Y[(m, p, t)] + self.Idle[(m, t)]
                    
                    # 3. Capacity Usage
                    usage.append(self.H_steps[(m, p, t)] * self.step_hours + setup_time * self.Delta_Setup[(m, p, t)])
                
                self.prob += pulp.lpSum(usage) <= self.hours_per_period

        # 4. Mass Balance
        for p in self.products:
            curr_init = self.initial_stock.get(p, 0)
            for t_idx, t in enumerate(self.periods):
                prod_in = pulp.lpSum([
                    self.H_steps[(m, p, t)] * self.step_hours * self.productivity[p][m]
                    for m in self.product_machines[p]
                ])
                prev_inv = curr_init if t_idx == 0 else self.I[(p, self.periods[t_idx-1])]
                dem = self.demand[p].get(t, 0)
                
                self.prob += prev_inv + prod_in == self.I[(p, t)] + dem - self.K[(p, t)]
                self.prob += self.Q[(p, t)] == dem - self.K[(p, t)]
                
                if self.safety_stock_pct > 0:
                    next_dem = self.demand[p].get(self.periods[t_idx+1], dem) if t_idx + 1 < len(self.periods) else dem
                    self.prob += self.I[(p, t)] >= next_dem * self.safety_stock_pct

        # 5. Vacation Planning Constraint
        if self.vacation_planning and len(self.periods) > 0:
            horizon_years = len(self.periods) / 12.0
            # Arredonda para cima para garantir cobertura mínima completa
            required_idle_periods = math.ceil(len(self.active_machines) * horizon_years)
            
            total_idle = pulp.lpSum([self.Idle[(m, t)] for m in self.active_machines for t in self.periods])
            
            # Fixa exatamente o número de paradas para evitar que o solver use Idle para ociosidade comum,
            # o que inflaria o relatório de férias desnecessariamente.
            self.prob += total_idle == required_idle_periods

    def _format_results(self, status):
        if status not in ['Optimal', 'Feasible']:
            return {"status": status, "kpis": {"total_cost": float('inf')}}
            
        def val(v): return v.varValue if v.varValue is not None else 0.0

        res_inv, res_prod, res_dem, res_setup, res_vacations = [], [], [], [], []
        res_summary = {}

        for t_idx, t in enumerate(self.periods):
            # Init summary for period
            res_summary[t] = {
                "Period": t, "Inventory": 0.0, "Utilization": 0.0,
                "Demand": 0.0, "Lost": 0.0, "Production": 0.0
            }

            for p in self.products:
                inv_val = val(self.I[(p, t)])
                dem_val = self.demand[p].get(t, 0)
                met_val = val(self.Q[(p, t)])
                lost_val = val(self.K[(p, t)])
                
                res_inv.append({"Period": t, "Product": f"{p[0]} {p[1]}", "Inventory": inv_val})
                res_dem.append({
                    "Period": t, "Product": f"{p[0]} {p[1]}",
                    "Demand": dem_val, "Met": met_val, "Lost": lost_val
                })
                
                res_summary[t]["Inventory"] += inv_val
                res_summary[t]["Demand"] += dem_val
                res_summary[t]["Lost"] += lost_val
            
            machine_hours_used = 0.0
            total_machine_hours = len(self.active_machines) * self.hours_per_period

            for m in self.active_machines:
                # Vacations / Idle
                if self.vacation_planning and val(self.Idle[(m, t)]) > 0.5:
                    res_vacations.append({"Period": t, "Machine": m, "Operators": self.operators_per_machine})

                prev_t = self.periods[t_idx-1] if t_idx > 0 else None
                
                # Check setup (From -> To)
                # To find "From", check which product was active in prev_t
                from_prod = "-"
                
                # Logic to identify if setup comes from idle (vacation/stop)
                was_idle = False
                if prev_t:
                    if val(self.Idle[(m, prev_t)]) > 0.5:
                        from_prod = "Parada/Férias"
                        was_idle = True
                    else:
                        for p_prev in self.machine_products[m]:
                            if val(self.S_state[(m, p_prev, prev_t)]) > 0.5:
                                from_prod = f"{p_prev[0]} {p_prev[1]}"
                                break
                
                # If first period and machine starts idle/clean, we can assume "-" or special state
                # But here we focus on transitions

                for p in self.machine_products[m]:
                    h_val = val(self.H_steps[(m, p, t)])
                    prod_qty = h_val * self.step_hours * self.productivity[p][m]
                    hours_used = h_val * self.step_hours
                    
                    if h_val > 0:
                        res_prod.append({
                            "Period": t, "Machine": m, "Product": f"{p[0]} {p[1]}",
                            "Quantity": prod_qty, "Hours": hours_used
                        })
                        res_summary[t]["Production"] += prod_qty
                        machine_hours_used += hours_used
                    
                    if val(self.Delta_Setup[(m, p, t)]) > 0.5:
                        # Setup cost calculation
                        setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
                        rate = self.productivity[p][m]
                        c_p = self.costs.get(p, 0.0)
                        
                        # If coming from Idle, cost might be different or standard setup
                        # In this model, Delta_Setup handles all transitions to State S. 
                        # If S changed or Y activated, Delta=1.
                        setup_cost_val = c_p * rate * setup_time

                        res_setup.append({
                            "Period": t, "Machine": m, 
                            "From": from_prod,
                            "To": f"{p[0]} {p[1]}",
                            "Cost": setup_cost_val
                        })
                        
                        machine_hours_used += setup_time

            res_summary[t]["Utilization"] = machine_hours_used / total_machine_hours if total_machine_hours > 0 else 0.0

        total_cost = pulp.value(self.prob.objective)
        
        # Calculate KPIs
        total_demand = sum(d['Demand'] for d in res_dem)
        total_lost = sum(d['Lost'] for d in res_dem)
        service_level = (1 - total_lost / total_demand) * 100 if total_demand > 0 else 100.0
        
        avg_inventory = sum(i['Inventory'] for i in res_inv) / len(self.periods) if self.periods else 0.0

        return {
            "status": status, "inventory": res_inv, "production": res_prod, "setups": res_setup,
            "vacations": res_vacations, "demand": res_dem, "summary": list(res_summary.values()),
            "kpis": {
                "total_cost": total_cost,
                "service_level": service_level,
                "avg_inventory": avg_inventory
            }
        }