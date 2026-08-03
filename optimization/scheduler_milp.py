import pulp


def sanitize_name(name) -> str:
    return str(name).replace(' ', '_').replace(':', '_').replace('-', '_')


def solve_color_schedule_milp(problem, time_limit=600, solver_name='CBC', threads=None):
    windows = problem['windows']
    colors_by_product = problem['colors_by_product']
    orders_by_sku = problem['orders_by_sku']
    initial_stock_by_sku = problem['initial_stock_by_sku']
    daily_capacity = problem['daily_capacity']
    productivity = problem['productivity']
    costs = problem['costs']
    setup_matrix = problem['setup_matrix']
    setup_time_color_default = problem['setup_time_color_default']

    prob = pulp.LpProblem('ColorSequencing', pulp.LpMinimize)

    Sc = {}
    for window in windows:
        machine = window['machine']
        product = window['product']
        product_colors = colors_by_product.get(product, [])
        for day in window['days']:
            for color in product_colors:
                var_name = f'Sc_{sanitize_name(machine)}_{sanitize_name(color)}_{day}'
                Sc[(machine, color, day)] = pulp.LpVariable(var_name, cat='Binary')

    Trans = {}
    setup_cost_terms = []
    for window in windows:
        machine = window['machine']
        product = window['product']
        product_colors = colors_by_product.get(product, [])
        product_cost = costs.get(product, 0.0)
        productivity_rate = productivity.get(product, {}).get(machine, 0.0)
        window_days = window['days']
        for day_index in range(1, len(window_days)):
            current_day = window_days[day_index]
            previous_day = window_days[day_index - 1]
            for previous_color in product_colors:
                for current_color in product_colors:
                    colors_differ = previous_color != current_color
                    if colors_differ:
                        setup_time = setup_matrix.get((previous_color, current_color))
                        transition_allowed = setup_time is not None
                        if transition_allowed:
                            var_name = f'Trans_{sanitize_name(machine)}_{sanitize_name(previous_color)}_{sanitize_name(current_color)}_{current_day}'
                            trans_variable = pulp.LpVariable(var_name, cat='Binary')
                            Trans[(machine, previous_color, current_color, current_day)] = trans_variable
                            prob += trans_variable >= Sc[(machine, previous_color, previous_day)] + Sc[(machine, current_color, current_day)] - 1
                            prob += trans_variable <= Sc[(machine, previous_color, previous_day)]
                            prob += trans_variable <= Sc[(machine, current_color, current_day)]
                            setup_cost_terms.append(product_cost * productivity_rate * setup_time * trans_variable)
                        else:
                            prob += Sc[(machine, previous_color, previous_day)] + Sc[(machine, current_color, current_day)] <= 1

    for window in windows:
        machine = window['machine']
        product = window['product']
        product_colors = colors_by_product.get(product, [])
        for day in window['days']:
            day_terms = []
            for color in product_colors:
                day_terms.append(Sc[(machine, color, day)])
            prob += pulp.lpSum(day_terms) == 1

    production_by_sku = {}
    for window in windows:
        machine = window['machine']
        product = window['product']
        product_colors = colors_by_product.get(product, [])
        productivity_rate = productivity.get(product, {}).get(machine, 0.0)
        window_days = window['days']
        for day_index in range(len(window_days)):
            current_day = window_days[day_index]
            hours_available_on_day = daily_capacity[(machine, current_day)]
            first_day_of_window = day_index == 0
            for color in product_colors:
                if first_day_of_window:
                    effective_hours_for_color = (hours_available_on_day * Sc[(machine, color, current_day)]
                                                 - setup_time_color_default * Sc[(machine, color, current_day)])
                else:
                    setup_discount_terms = []
                    for previous_color in product_colors:
                        trans_key = (machine, previous_color, color, current_day)
                        if trans_key in Trans:
                            setup_time = setup_matrix[(previous_color, color)]
                            setup_discount_terms.append(setup_time * Trans[trans_key])
                    effective_hours_for_color = hours_available_on_day * Sc[(machine, color, current_day)] - pulp.lpSum(setup_discount_terms)
                color_production_on_day = effective_hours_for_color * productivity_rate
                color_sku = f'{product}-{color}'
                if color_sku not in production_by_sku:
                    production_by_sku[color_sku] = []
                production_by_sku[color_sku].append((current_day, color_production_on_day))

    I_color, K_color = {}, {}
    delay_cost_terms = []
    for sku in orders_by_sku:
        sku_orders = orders_by_sku[sku]
        sku_production = production_by_sku.get(sku, [])
        previous_due_day = -1
        for order_index in range(len(sku_orders)):
            current_order = sku_orders[order_index]
            order_due_day = current_order['due_day']

            I_color[(sku, order_index)] = pulp.LpVariable(f'Icolor_{sanitize_name(sku)}_{order_index}', lowBound=0)
            K_color[(sku, order_index)] = pulp.LpVariable(f'Kcolor_{sanitize_name(sku)}_{order_index}', lowBound=0)

            production_terms_in_interval = []
            for production_day, production_term in sku_production:
                within_interval = production_day > previous_due_day and production_day <= order_due_day
                if within_interval:
                    production_terms_in_interval.append(production_term)
            production_in_interval = pulp.lpSum(production_terms_in_interval)

            if order_index == 0:
                previous_inventory = initial_stock_by_sku.get(sku, 0.0)
            else:
                previous_inventory = I_color[(sku, order_index - 1)]

            prob += (previous_inventory + production_in_interval
                    == I_color[(sku, order_index)] + current_order['quantity'] - K_color[(sku, order_index)])

            order_product_cost = costs.get(current_order['product'], 0.0)
            delay_cost_terms.append(order_product_cost * K_color[(sku, order_index)])

            previous_due_day = order_due_day

    prob += pulp.lpSum(delay_cost_terms + setup_cost_terms)

    if solver_name.upper() == 'GUROBI':
        gurobi_options = [('TimeLimit', time_limit)]
        if threads:
            gurobi_options.append(('Threads', threads))
        solver_instance = pulp.GUROBI_CMD(msg=1, options=gurobi_options)
    else:
        cbc_arguments = dict(msg=1, timeLimit=time_limit)
        if threads:
            cbc_arguments['threads'] = threads
        solver_instance = pulp.PULP_CBC_CMD(**cbc_arguments)

    prob.solve(solver_instance)
    status = pulp.LpStatus[prob.status]

    def resolved_value(variable):
        if variable.varValue is None:
            return 0.0
        else:
            return variable.varValue

    color_schedule, color_setups = [], []
    for window in windows:
        machine = window['machine']
        product = window['product']
        product_colors = colors_by_product.get(product, [])
        product_cost = costs.get(product, 0.0)
        productivity_rate = productivity.get(product, {}).get(machine, 0.0)
        window_days = window['days']
        for day_index in range(len(window_days)):
            current_day = window_days[day_index]
            hours_available_on_day = daily_capacity[(machine, current_day)]
            first_day_of_window = day_index == 0
            active_color_on_day = None
            for color in product_colors:
                if resolved_value(Sc[(machine, color, current_day)]) > 0.5:
                    active_color_on_day = color

            if active_color_on_day is not None:
                applied_setup_time = 0.0
                origin_color = '-'
                if first_day_of_window:
                    applied_setup_time = setup_time_color_default
                else:
                    for previous_color in product_colors:
                        trans_key = (machine, previous_color, active_color_on_day, current_day)
                        if trans_key in Trans and resolved_value(Trans[trans_key]) > 0.5:
                            applied_setup_time = setup_matrix[(previous_color, active_color_on_day)]
                            origin_color = previous_color

                effective_hours = hours_available_on_day - applied_setup_time
                production_kg = effective_hours * productivity_rate
                color_schedule.append({
                    'machine': machine, 'day': current_day, 'product': product,
                    'color': active_color_on_day, 'kg': production_kg, 'hours': effective_hours,
                })
                if applied_setup_time > 0.0:
                    color_setups.append({
                        'machine': machine, 'day': current_day, 'product': product,
                        'from_color': origin_color, 'to_color': active_color_on_day,
                        'setup_time': applied_setup_time,
                        'cost': product_cost * productivity_rate * applied_setup_time,
                    })

    orders_result = []
    for sku in orders_by_sku:
        sku_orders = orders_by_sku[sku]
        for order_index in range(len(sku_orders)):
            current_order = sku_orders[order_index]
            delayed_quantity = resolved_value(K_color[(sku, order_index)])
            orders_result.append({
                'sku': sku, 'product': current_order['product'], 'color': current_order['color'],
                'due_day': current_order['due_day'], 'quantity': current_order['quantity'],
                'delayed_qty': delayed_quantity,
            })

    total_delay_cost = 0.0
    for result_order in orders_result:
        total_delay_cost += costs.get(result_order['product'], 0.0) * result_order['delayed_qty']

    total_setup_cost = 0.0
    for result_setup in color_setups:
        total_setup_cost += result_setup['cost']

    total_ordered_quantity = 0.0
    total_delayed_quantity = 0.0
    for result_order in orders_result:
        total_ordered_quantity += result_order['quantity']
        total_delayed_quantity += result_order['delayed_qty']

    if total_ordered_quantity > 0:
        service_level = (1 - total_delayed_quantity / total_ordered_quantity) * 100
    else:
        service_level = 100.0

    return {
        'status': status,
        'method': 'milp',
        'color_schedule': color_schedule,
        'color_setups': color_setups,
        'orders': orders_result,
        'kpis': {
            'total_cost': total_delay_cost + total_setup_cost,
            'delay_cost': total_delay_cost,
            'setup_cost': total_setup_cost,
            'service_level': service_level,
            'total_setups': len(color_setups),
        },
    }
