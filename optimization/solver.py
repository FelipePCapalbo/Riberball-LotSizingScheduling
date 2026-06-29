import pulp
import pandas as pd


def sanitize_name(name) -> str:
    """Sanitiza nomes para compatibilidade com o solver (sem espaços/símbolos)."""
    return str(name).replace(' ', '_').replace(':', '_').replace('-', '_')


class LotSizingSolver:
    """Solver MILP para planejamento de produção com subperíodos diários e operadores indexados."""

    def __init__(self, demand, productivity, initial_stock, active_machines,
                 start_period, end_period=None, costs=None,
                 hours_per_day=24.0, days_per_period=None,
                 safety_stock_pct=0,
                 manual_stops=None,
                 high_setup_machines=None, setup_time_high=7.0, setup_time_low=3.0):

        self.demand = demand
        self.productivity = productivity
        self.initial_stock = initial_stock
        self.active_machines = active_machines
        self.costs = costs or {}

        self.hours_per_day = hours_per_day
        self.safety_stock_pct = int(safety_stock_pct)

        # Tempos de setup por máquina (config externa, antes em Config)
        self.high_setup_machines = high_setup_machines or []
        self.setup_time_high = setup_time_high
        self.setup_time_low = setup_time_low

        self.manual_stops = manual_stops or set()

        self.products = list(demand.keys())
        all_dates = sorted(demand[self.products[0]].keys()) if self.products else []
        self.periods = [d for d in all_dates if d >= start_period and (not end_period or d <= end_period)]

        self.days_per_period = days_per_period or {t: 30 for t in self.periods}

        self._ensure_demand_coverage()
        self._build_day_mapping()
        self._precompute_daily_capacity()
        self._map_machine_products()
        self.prob = pulp.LpProblem("LotSizing", pulp.LpMinimize)

    def _ensure_demand_coverage(self):
        """Garante que self.demand contenha demanda para os α períodos além do fim do horizonte.

        Se o valor não existir no dict, usa sazonalidade do ano anterior (mesmo mês, -1 ano).
        Isso é necessário para que eq:seguranca seja corretamente aplicada nos últimos períodos.
        """
        if self.safety_stock_pct <= 0 or not self.periods:
            return

        last_period = self.periods[-1]
        last_dt = pd.to_datetime(last_period)

        for k in range(1, self.safety_stock_pct + 1):
            future_dt = last_dt + pd.DateOffset(months=k)
            future_str = str(future_dt)
            hist_dt = future_dt - pd.DateOffset(years=1)
            hist_str = str(hist_dt)

            for p in self.products:
                if future_str not in self.demand[p]:
                    # Usa o mesmo mês do ano anterior como proxy sazonal
                    fallback = self.demand[p].get(hist_str, 0.0)
                    self.demand[p][future_str] = fallback

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

    def _precompute_daily_capacity(self):
        """Pré-calcula H_{jd}: hours_per_day em dias normais, 0 em dias com parada programada."""
        stops_by_machine = {}
        for (m, d) in self.manual_stops:
            stops_by_machine.setdefault(m, set()).add(d)

        self.daily_capacity = {}
        for m in self.active_machines:
            machine_stops = stops_by_machine.get(m, set())
            for d in self.all_days:
                self.daily_capacity[(m, d)] = 0.0 if d in machine_stops else self.hours_per_day

    def _setup_time(self, m):
        """Tempo de setup da máquina: alto para máquinas listadas, baixo nas demais."""
        return self.setup_time_high if m in self.high_setup_machines else self.setup_time_low

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

    def solve(self, time_limit=600, solver_name='CBC', threads=None):
        if not self.periods:
            return {"status": "No valid periods found"}

        self._define_variables()
        self._build_objective_function()
        self._add_constraints()

        n_vars = len(self.prob.variables())
        n_cons = len(self.prob.constraints)
        print(f"\n{'─'*60}", flush=True)
        print(f"  Solver : {solver_name.upper()}", flush=True)
        print(f"  Vars   : {n_vars}  |  Restrições: {n_cons}", flush=True)
        print(f"  Limite : {time_limit}s", flush=True)
        print(f"{'─'*60}\n", flush=True)

        solver = self._get_solver_instance(solver_name, time_limit, threads)
        self.prob.solve(solver)

        status = pulp.LpStatus[self.prob.status]
        obj = pulp.value(self.prob.objective)
        print(f"\n{'─'*60}", flush=True)
        print(f"  Status : {status}", flush=True)
        if obj is not None:
            print(f"  Obj    : {obj:,.2f}", flush=True)
        print(f"{'─'*60}\n", flush=True)

        return self._format_results(status)

    def _get_solver_instance(self, name, time_limit, threads=None):
        name = name.upper()
        if name == 'GUROBI':
            opts = [("TimeLimit", time_limit)]
            if threads:
                opts.append(("Threads", threads))
            return pulp.GUROBI_CMD(msg=1, options=opts)

        args = dict(msg=1, timeLimit=time_limit)
        if threads:
            args['threads'] = threads
        return pulp.PULP_CBC_CMD(**args)

    def _define_variables(self):
        # Com granularidade em dias, S_state[m,p,d] = 1 implica produção integral do dia.
        # H_steps não é necessário: produção = S_state * hours_per_day * productivity.
        self.S_state, self.Delta_Setup = {}, {}
        self.I, self.K = {}, {}
        self.Z_day = {}

        for m in self.active_machines:
            for d in self.all_days:
                self.Z_day[(m, d)] = pulp.LpVariable(f"Z_{m}_{d}", cat='Binary')

                for p in self.machine_products[m]:
                    safe_p = sanitize_name(p)
                    key = (m, p, d)

                    self.S_state[key] = pulp.LpVariable(f"S_{m}_{safe_p}_{d}", cat='Binary')
                    self.Delta_Setup[key] = pulp.LpVariable(f"Delta_{m}_{safe_p}_{d}", cat='Binary')

        for p in self.products:
            safe_p = sanitize_name(p)
            for t in self.periods:
                safe_t = sanitize_name(t)
                key = (p, t)
                self.I[key] = pulp.LpVariable(f"I_{safe_p}_{safe_t}", lowBound=0)
                self.K[key] = pulp.LpVariable(f"K_{safe_p}_{safe_t}", lowBound=0)

    def _build_objective_function(self):
        lost_sales = [self.costs.get(p, 0.0) * self.K[(p, t)] for p in self.products for t in self.periods]

        setup_costs = []
        for m in self.active_machines:
            setup_time = self._setup_time(m)
            for p in self.machine_products[m]:
                cost = self.costs.get(p, 0.0) * self.productivity[p][m] * setup_time
                setup_costs.extend([cost * self.Delta_Setup[(m, p, d)] for d in self.all_days])

        self.prob += pulp.lpSum(lost_sales + setup_costs)

    def _add_constraints(self):
        for m in self.active_machines:
            setup_time = self._setup_time(m)
            prods = self.machine_products[m]

            for d_idx, d in enumerate(self.all_days):
                h_jd = self.daily_capacity[(m, d)]
                prev_d = self.all_days[d_idx - 1] if d_idx > 0 else None

                # eq:estado_unico — no máximo um balão por máquina por dia
                self.prob += pulp.lpSum([self.S_state[(m, p, d)] for p in prods]) <= 1

                for p in prods:
                    key = (m, p, d)
                    curr_s = self.S_state[key]
                    prev_s = self.S_state[(m, p, prev_d)] if prev_d else 0

                    # eq:setup_delta — detecção de setup dia a dia
                    self.prob += self.Delta_Setup[key] >= curr_s - prev_s

                # eq:capacidade — no máximo um balão ativo por máquina por dia disponível.
                # Paradas programadas (h_jd=0) impedem qualquer ativação.
                if h_jd == 0:
                    self.prob += pulp.lpSum([self.S_state[(m, p, d)] for p in prods]) == 0
                else:
                    self.prob += pulp.lpSum([self.S_state[(m, p, d)] for p in prods]) <= 1 - self.Z_day[(m, d)]

        # eq:balanco e eq:seguranca — nível de período, produção agregada dos dias
        for p in self.products:
            curr_init = self.initial_stock.get(p, 0)
            for t_idx, t in enumerate(self.periods):
                days_t = self.days_in_period[t]
                # Horas efetivas no dia d: h_jd se produção contínua, (h_jd - t^s_j) no dia do setup.
                # prod_in = Σ_{d,j} s_ijd * (h_jd - t^s_j * δ_ijd) * p_ij
                prod_in_terms = []
                for m in self.product_machines[p]:
                    setup_time = self._setup_time(m)
                    for d in days_t:
                        h_jd = self.daily_capacity[(m, d)]
                        if h_jd > 0:
                            effective_hours = h_jd * self.S_state[(m, p, d)] - setup_time * self.Delta_Setup[(m, p, d)]
                            prod_in_terms.append(effective_hours * self.productivity[p][m])
                prod_in = pulp.lpSum(prod_in_terms)
                prev_inv = curr_init if t_idx == 0 else self.I[(p, self.periods[t_idx - 1])]
                dem = self.demand[p].get(t, 0)

                self.prob += prev_inv + prod_in == self.I[(p, t)] + dem - self.K[(p, t)]

                if self.safety_stock_pct > 0:
                    # Soma a demanda dos próximos α períodos completos (eq:seguranca).
                    # Períodos além do horizonte são buscados diretamente em self.demand
                    # usando a extensão sazonal já calculada pelo loader.
                    t_dt = pd.to_datetime(t)
                    coverage_demand = 0.0
                    for k in range(1, self.safety_stock_pct + 1):
                        future_dt = t_dt + pd.DateOffset(months=k)
                        future_str = str(future_dt)
                        coverage_demand += self.demand[p].get(future_str, 0.0)
                    self.prob += self.I[(p, t)] >= coverage_demand


    def _format_results(self, status):
        if status not in ['Optimal', 'Feasible']:
            return {"status": status, "kpis": {"total_cost": float('inf')}}

        def val(v):
            return v.varValue if v.varValue is not None else 0.0

        res_inv, res_prod, res_dem, res_setup = [], [], [], []
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
                lost_val = min(val(self.K[(p, t)]), dem_val)
                met_val = dem_val - lost_val

                res_inv.append({"Period": t, "Product": p, "Inventory": inv_val})
                res_dem.append({
                    "Period": t, "Product": p,
                    "Demand": dem_val, "Met": met_val, "Lost": lost_val
                })

                res_summary[t]["Inventory"] += inv_val
                res_summary[t]["Demand"] += dem_val
                res_summary[t]["Lost"] += lost_val

            machine_hours_used = 0.0
            total_machine_hours = 0.0
            days_t = self.days_in_period[t]

            for m in self.active_machines:
                n_t = len(days_t)

                days_stopped = sum(
                    1 for d in days_t
                    if self.daily_capacity[(m, d)] == 0.0 or val(self.Z_day[(m, d)]) > 0.5
                )
                machine_hours_avail = sum(
                    self.daily_capacity[(m, d)] * (1 - (1 if val(self.Z_day[(m, d)]) > 0.5 else 0))
                    for d in days_t
                )
                total_machine_hours += machine_hours_avail

                if days_stopped > 0:
                    res_machine_stops.append({
                        "Period": t, "Machine": m,
                        "DaysStopped": days_stopped, "TotalDays": n_t
                    })

                # Agrega produção e setups dos dias do período
                for p in self.machine_products[m]:
                    setup_time_p = self._setup_time(m)
                    hours_used = 0.0
                    prod_qty = 0.0
                    for d in days_t:
                        if val(self.S_state[(m, p, d)]) > 0.5:
                            h_jd = self.daily_capacity[(m, d)]
                            setup_discount = setup_time_p if val(self.Delta_Setup[(m, p, d)]) > 0.5 else 0.0
                            eff_hours = max(0.0, h_jd - setup_discount)
                            hours_used += eff_hours
                            prod_qty += eff_hours * self.productivity[p][m]

                    if hours_used > 0:
                        res_prod.append({
                            "Period": t, "Machine": m, "Product": p,
                            "Kg": prod_qty, "Hours": hours_used
                        })
                        res_summary[t]["Production"] += prod_qty
                        machine_hours_used += hours_used

                    # Setups: um registro por dia em que ocorre setup
                    for d_idx, d in enumerate(days_t):
                        if val(self.Delta_Setup[(m, p, d)]) > 0.5:
                            rate = self.productivity[p][m]
                            c_p = self.costs.get(p, 0.0)
                            setup_cost_val = c_p * rate * setup_time_p

                            # Balão anterior: último s=1 antes deste dia
                            from_prod = "-"
                            prev_d = days_t[d_idx - 1] if d_idx > 0 else None
                            if prev_d is not None:
                                for p_prev in self.machine_products[m]:
                                    if val(self.S_state[(m, p_prev, prev_d)]) > 0.5:
                                        from_prod = p_prev
                                        break
                            elif t_idx > 0:
                                prev_days = self.days_in_period[self.periods[t_idx - 1]]
                                for p_prev in self.machine_products[m]:
                                    if val(self.S_state[(m, p_prev, prev_days[-1])]) > 0.5:
                                        from_prod = p_prev
                                        break

                            res_setup.append({
                                "Period": t, "Machine": m, "Day": d + 1,
                                "From": from_prod,
                                "To": p,
                                "Cost": setup_cost_val
                            })
                            machine_hours_used += setup_time_p

            res_summary[t]["Utilization"] = machine_hours_used / total_machine_hours if total_machine_hours > 0 else 0.0

        total_cost = pulp.value(self.prob.objective)

        total_demand = sum(d['Demand'] for d in res_dem)
        total_lost = sum(d['Lost'] for d in res_dem)
        service_level = (1 - total_lost / total_demand) * 100 if total_demand > 0 else 100.0

        avg_inventory = sum(i['Inventory'] for i in res_inv) / len(self.periods) if self.periods else 0.0

        # Giro = demanda total atendida / estoque médio no horizonte
        total_met = total_demand - total_lost
        inventory_turnover = total_met / avg_inventory if avg_inventory > 0 else 0.0

        return {
            "status": status, "inventory": res_inv, "production": res_prod, "setups": res_setup,
            "machine_stops": res_machine_stops, "demand": res_dem, "summary": list(res_summary.values()),
            "kpis": {
                "total_cost": total_cost,
                "service_level": service_level,
                "avg_inventory": avg_inventory,
                "inventory_turnover": inventory_turnover
            }
        }
