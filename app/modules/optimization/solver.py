import pulp
from app.config import Config
from app.utils import sanitize_name


class LotSizingSolver:
    """Solver MILP para planejamento de produção com subperíodos diários e operadores indexados."""

    def __init__(self, demand, productivity, initial_stock, active_machines,
                 start_period, end_period=None, costs=None,
                 hours_per_day=24.0, days_per_period=None,
                 step_hours=6.0, integer_var=True, safety_stock_pct=0.0,
                 manual_stops=None,
                 num_operators=0, operators_per_machine=1,
                 num_operators_on_vacation=0, vacation_days=0):

        self.demand = demand
        self.productivity = productivity
        self.initial_stock = initial_stock
        self.active_machines = active_machines
        self.costs = costs or {}

        self.hours_per_day = hours_per_day
        self.step_hours = step_hours
        self.integer_var = integer_var
        self.safety_stock_pct = safety_stock_pct

        self.manual_stops = manual_stops or set()
        self.num_operators = num_operators
        self.operators_per_machine = operators_per_machine
        self.num_operators_on_vacation = num_operators_on_vacation
        self.vacation_days = vacation_days

        self.products = list(demand.keys())
        all_dates = sorted(demand[self.products[0]].keys()) if self.products else []
        self.periods = [d for d in all_dates if d >= start_period and (not end_period or d <= end_period)]

        self.days_per_period = days_per_period or {t: 30 for t in self.periods}

        self._build_day_mapping()
        self._map_machine_products()
        self.prob = pulp.LpProblem("LotSizing", pulp.LpMinimize)

    def _build_day_mapping(self):
        """Gera mapeamentos globais dia -> período e período -> dias."""
        self.all_days = []
        self.days_in_period = {}
        self.period_of_day = {}
        day_idx = 0
        for t in self.periods:
            n_t = self.days_per_period.get(t, 30)
            days_t = list(range(day_idx, day_idx + n_t))
            self.days_in_period[t] = days_t
            for d in days_t:
                self.period_of_day[d] = t
            self.all_days.extend(days_t)
            day_idx += n_t

    def _map_machine_products(self):
        self.machine_products = {m: [] for m in self.active_machines}
        self.product_machines = {p: [] for p in self.products}

        for p in self.products:
            if p not in self.productivity:
                continue
            for m, rate in self.productivity[p].items():
                if m in self.active_machines:
                    self.machine_products[m].append(p)
                    self.product_machines[p].append(m)

    def solve(self, time_limit=600, log_path=None, solver_name='CBC', threads=None):
        if not self.periods:
            return {"status": "No valid periods found"}

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
            if log_path:
                opts.append(("LogFile", log_path))
            if threads:
                opts.append(("Threads", threads))
            return pulp.GUROBI_CMD(msg=1, options=opts)

        args = dict(msg=1, timeLimit=time_limit, logPath=log_path)
        if threads:
            args['threads'] = threads
        return pulp.PULP_CBC_CMD(**args)

    def _define_variables(self):
        var_cat = 'Integer' if self.integer_var else 'Continuous'

        self.H_steps, self.Y, self.S_state, self.Delta_Setup = {}, {}, {}, {}
        self.I, self.Q, self.K = {}, {}, {}
        self.Z_day = {}
        self.F_vac, self.G_start, self.R_assign = {}, {}, {}

        max_n_t = max(self.days_per_period.values()) if self.days_per_period else 30
        global_max_steps = int(self.hours_per_day * max_n_t / self.step_hours) + 1 if self.step_hours > 0 else 1

        for m in self.active_machines:
            for d in self.all_days:
                self.Z_day[(m, d)] = pulp.LpVariable(f"Z_{m}_{d}", cat='Binary')

            for t in self.periods:
                safe_t = sanitize_name(t)
                for p in self.machine_products[m]:
                    safe_p = sanitize_name(f"{p[0]}_{p[1]}")
                    key = (m, p, t)

                    self.S_state[key] = pulp.LpVariable(f"S_{m}_{safe_p}_{safe_t}", cat='Binary')
                    self.Delta_Setup[key] = pulp.LpVariable(f"Delta_{m}_{safe_p}_{safe_t}", cat='Binary')
                    self.Y[key] = pulp.LpVariable(f"Y_{m}_{safe_p}_{safe_t}", cat='Binary')
                    self.H_steps[key] = pulp.LpVariable(
                        f"H_{m}_{safe_p}_{safe_t}", lowBound=0, upBound=global_max_steps, cat=var_cat
                    )

        operators = list(range(self.num_operators))
        vacation_operators = list(range(self.num_operators_on_vacation))

        for k in operators:
            for d in self.all_days:
                for m in self.active_machines:
                    self.R_assign[(k, m, d)] = pulp.LpVariable(f"R_{k}_{m}_{d}", cat='Binary')

        for k in vacation_operators:
            for d in self.all_days:
                self.F_vac[(k, d)] = pulp.LpVariable(f"F_{k}_{d}", cat='Binary')
                self.G_start[(k, d)] = pulp.LpVariable(f"G_{k}_{d}", cat='Binary')

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
        operators = list(range(self.num_operators))
        vacation_operators = list(range(self.num_operators_on_vacation))

        for m in self.active_machines:
            setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW

            for t_idx, t in enumerate(self.periods):
                prods = self.machine_products[m]
                prev_t = self.periods[t_idx - 1] if t_idx > 0 else None
                n_t = self.days_per_period.get(t, 30)

                # (1) Estado único por máquina — relaxada para <=
                self.prob += pulp.lpSum([self.S_state[(m, p, t)] for p in prods]) <= 1

                usage = []
                for p in prods:
                    key = (m, p, t)
                    curr_s = self.S_state[key]
                    prev_s = self.S_state[(m, p, prev_t)] if prev_t else 0

                    # (2)-(3) Setup logic
                    self.prob += self.Delta_Setup[key] >= curr_s - prev_s
                    self.prob += self.Delta_Setup[key] >= self.Y[key] - prev_s

                    # (5) s <= y (simplificada, sem z_jt)
                    self.prob += curr_s <= self.Y[key]

                    # (6) Ativação Big-M constante
                    max_cap = self.hours_per_day * n_t
                    max_steps = int(max_cap / self.step_hours) + 1 if self.step_hours > 0 else 1
                    self.prob += self.H_steps[key] <= max_steps * self.Y[key]

                    usage.append(self.H_steps[key] * self.step_hours + setup_time * self.Delta_Setup[key])

                # (7) Capacidade derivada dos dias
                days_t = self.days_in_period[t]
                available_hours = self.hours_per_day * pulp.lpSum([1 - self.Z_day[(m, d)] for d in days_t])
                self.prob += pulp.lpSum(usage) <= available_hours

        # (8)-(9) Balanço de massa e estoque de segurança
        for p in self.products:
            curr_init = self.initial_stock.get(p, 0)
            for t_idx, t in enumerate(self.periods):
                prod_in = pulp.lpSum([
                    self.H_steps[(m, p, t)] * self.step_hours * self.productivity[p][m]
                    for m in self.product_machines[p]
                ])
                prev_inv = curr_init if t_idx == 0 else self.I[(p, self.periods[t_idx - 1])]
                dem = self.demand[p].get(t, 0)

                self.prob += prev_inv + prod_in == self.I[(p, t)] + dem - self.K[(p, t)]
                self.prob += self.Q[(p, t)] == dem - self.K[(p, t)]

                if self.safety_stock_pct > 0:
                    next_dem = self.demand[p].get(self.periods[t_idx + 1], dem) if t_idx + 1 < len(self.periods) else dem
                    self.prob += self.I[(p, t)] >= next_dem * self.safety_stock_pct

        # (A) Parada manual fixa: z_{jd} >= 1 para (j,d) no conjunto de paradas
        for (m, d) in self.manual_stops:
            if m in self.active_machines and d in self.all_days:
                self.prob += self.Z_day[(m, d)] >= 1

        # (B) Cobertura de máquina — operador necessário
        if self.num_operators > 0:
            for m in self.active_machines:
                for d in self.all_days:
                    self.prob += pulp.lpSum(
                        [self.R_assign[(k, m, d)] for k in operators]
                    ) >= 1 - self.Z_day[(m, d)]

        # (C) Operador de férias não trabalha
        for k in vacation_operators:
            for m in self.active_machines:
                for d in self.all_days:
                    self.prob += self.R_assign[(k, m, d)] <= 1 - self.F_vac[(k, d)]

        # (D) Operador em no máximo 1 máquina por dia
        if self.num_operators > 0:
            for k in operators:
                for d in self.all_days:
                    self.prob += pulp.lpSum(
                        [self.R_assign[(k, m, d)] for m in self.active_machines]
                    ) <= 1

        # (E) Total de dias de férias por operador
        for k in vacation_operators:
            self.prob += pulp.lpSum(
                [self.F_vac[(k, d)] for d in self.all_days]
            ) == self.vacation_days

        # (F) Férias contíguas (bloco sequencial)
        for k in vacation_operators:
            if self.all_days:
                first_d = self.all_days[0]
                self.prob += self.G_start[(k, first_d)] >= self.F_vac[(k, first_d)]
                for d in self.all_days[1:]:
                    prev_d = d - 1
                    self.prob += self.G_start[(k, d)] >= self.F_vac[(k, d)] - self.F_vac[(k, prev_d)]
                self.prob += pulp.lpSum([self.G_start[(k, d)] for d in self.all_days]) <= 1

    def _format_results(self, status):
        if status not in ['Optimal', 'Feasible']:
            return {"status": status, "kpis": {"total_cost": float('inf')}}

        def val(v):
            return v.varValue if v.varValue is not None else 0.0

        res_inv, res_prod, res_dem, res_setup, res_vacations = [], [], [], [], []
        res_machine_stops = []
        res_summary = {}

        for t_idx, t in enumerate(self.periods):
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
            total_machine_hours = 0.0

            for m in self.active_machines:
                days_t = self.days_in_period[t]
                n_t = len(days_t)
                days_stopped = sum(1 for d in days_t if val(self.Z_day[(m, d)]) > 0.5)
                days_active = n_t - days_stopped
                machine_hours_avail = self.hours_per_day * days_active
                total_machine_hours += machine_hours_avail

                if days_stopped > 0:
                    res_machine_stops.append({
                        "Period": t, "Machine": m,
                        "DaysStopped": days_stopped, "TotalDays": n_t
                    })

                prev_t = self.periods[t_idx - 1] if t_idx > 0 else None

                from_prod = "-"
                if prev_t:
                    prev_days = self.days_in_period[prev_t]
                    prev_all_stopped = all(val(self.Z_day[(m, d)]) > 0.5 for d in prev_days)
                    if prev_all_stopped:
                        from_prod = "Parada"
                    else:
                        for p_prev in self.machine_products[m]:
                            if val(self.S_state[(m, p_prev, prev_t)]) > 0.5:
                                from_prod = f"{p_prev[0]} {p_prev[1]}"
                                break

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
                        setup_time = Config.DEFAULT_SETUP_TIME_HIGH if m in Config.HIGH_SETUP_MACHINES else Config.DEFAULT_SETUP_TIME_LOW
                        rate = self.productivity[p][m]
                        c_p = self.costs.get(p, 0.0)
                        setup_cost_val = c_p * rate * setup_time

                        res_setup.append({
                            "Period": t, "Machine": m,
                            "From": from_prod,
                            "To": f"{p[0]} {p[1]}",
                            "Cost": setup_cost_val
                        })
                        machine_hours_used += setup_time

            res_summary[t]["Utilization"] = machine_hours_used / total_machine_hours if total_machine_hours > 0 else 0.0

        # Extract operator vacation schedules
        vacation_operators = list(range(self.num_operators_on_vacation))
        for k in vacation_operators:
            vac_days = [d for d in self.all_days if val(self.F_vac[(k, d)]) > 0.5]
            if vac_days:
                start_d = min(vac_days)
                end_d = max(vac_days)
                start_period = self.period_of_day.get(start_d, "")
                end_period = self.period_of_day.get(end_d, "")
                res_vacations.append({
                    "Operator": k + 1,
                    "StartDay": start_d + 1,
                    "EndDay": end_d + 1,
                    "Days": len(vac_days),
                    "StartPeriod": start_period,
                    "EndPeriod": end_period
                })

        total_cost = pulp.value(self.prob.objective)

        total_demand = sum(d['Demand'] for d in res_dem)
        total_lost = sum(d['Lost'] for d in res_dem)
        service_level = (1 - total_lost / total_demand) * 100 if total_demand > 0 else 100.0

        avg_inventory = sum(i['Inventory'] for i in res_inv) / len(self.periods) if self.periods else 0.0

        return {
            "status": status, "inventory": res_inv, "production": res_prod, "setups": res_setup,
            "vacations": res_vacations, "machine_stops": res_machine_stops,
            "demand": res_dem, "summary": list(res_summary.values()),
            "kpis": {
                "total_cost": total_cost,
                "service_level": service_level,
                "avg_inventory": avg_inventory
            }
        }
