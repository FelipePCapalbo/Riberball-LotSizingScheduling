def solve_color_schedule_heuristic(problem):
    windows = problem['windows']
    colors_by_product = problem['colors_by_product']
    orders_by_sku = problem['orders_by_sku']
    initial_stock_by_sku = problem['initial_stock_by_sku']
    daily_capacity = problem['daily_capacity']
    productivity = problem['productivity']
    costs = problem['costs']
    setup_matrix = problem['setup_matrix']
    setup_time_color_default = problem['setup_time_color_default']

    production_slots = []
    for window in windows:
        for day_index in range(len(window['days'])):
            production_slots.append({
                'machine': window['machine'],
                'product': window['product'],
                'day': window['days'][day_index],
                'first_day_of_window': day_index == 0,
            })
    production_slots = sorted(production_slots, key=lambda slot: slot['day'])

    next_order_index_by_sku = {}
    for sku in orders_by_sku:
        next_order_index_by_sku[sku] = 0

    previous_color_by_machine = {}
    production_by_sku = {}
    color_schedule, color_setups = [], []

    for slot in production_slots:
        machine = slot['machine']
        product = slot['product']
        current_day = slot['day']
        product_colors = colors_by_product.get(product, [])
        product_has_known_colors = len(product_colors) > 0

        if product_has_known_colors:
            urgency_by_color = {}
            for color in product_colors:
                color_sku = f'{product}-{color}'
                sku_orders = orders_by_sku.get(color_sku, [])
                if color_sku not in next_order_index_by_sku:
                    next_order_index_by_sku[color_sku] = 0
                while (next_order_index_by_sku[color_sku] < len(sku_orders)
                      and sku_orders[next_order_index_by_sku[color_sku]]['due_day'] < current_day):
                    next_order_index_by_sku[color_sku] += 1
                has_future_order = next_order_index_by_sku[color_sku] < len(sku_orders)
                if has_future_order:
                    urgency_by_color[color] = sku_orders[next_order_index_by_sku[color_sku]]['due_day']
                else:
                    urgency_by_color[color] = float('inf')

            colors_sorted_by_urgency = sorted(product_colors, key=lambda color: urgency_by_color[color])
            previous_color_on_machine = previous_color_by_machine.get(machine)

            chosen_color = None
            for candidate_color in colors_sorted_by_urgency:
                already_chose_a_color = chosen_color is not None
                if not already_chose_a_color:
                    repeats_previous_color = candidate_color == previous_color_on_machine
                    if slot['first_day_of_window'] or repeats_previous_color:
                        chosen_color = candidate_color
                    else:
                        transition_allowed = (previous_color_on_machine, candidate_color) in setup_matrix
                        if transition_allowed:
                            chosen_color = candidate_color

            if slot['first_day_of_window']:
                applied_setup_time = setup_time_color_default
                origin_color = '-'
            else:
                if chosen_color == previous_color_on_machine:
                    applied_setup_time = 0.0
                    origin_color = previous_color_on_machine
                else:
                    applied_setup_time = setup_matrix[(previous_color_on_machine, chosen_color)]
                    origin_color = previous_color_on_machine

            hours_available_on_day = daily_capacity[(machine, current_day)]
            effective_hours = hours_available_on_day - applied_setup_time
            productivity_rate = productivity.get(product, {}).get(machine, 0.0)
            production_kg = effective_hours * productivity_rate

            color_schedule.append({
                'machine': machine, 'day': current_day, 'product': product,
                'color': chosen_color, 'kg': production_kg, 'hours': effective_hours,
            })
            if applied_setup_time > 0.0:
                product_cost = costs.get(product, 0.0)
                color_setups.append({
                    'machine': machine, 'day': current_day, 'product': product,
                    'from_color': origin_color, 'to_color': chosen_color,
                    'setup_time': applied_setup_time,
                    'cost': product_cost * productivity_rate * applied_setup_time,
                })

            produced_sku = f'{product}-{chosen_color}'
            if produced_sku not in production_by_sku:
                production_by_sku[produced_sku] = []
            production_by_sku[produced_sku].append((current_day, production_kg))

            previous_color_by_machine[machine] = chosen_color

    orders_result = []
    for sku in orders_by_sku:
        sku_orders = orders_by_sku[sku]
        sku_production = production_by_sku.get(sku, [])
        previous_inventory = initial_stock_by_sku.get(sku, 0.0)
        previous_due_day = -1
        for order_index in range(len(sku_orders)):
            current_order = sku_orders[order_index]
            order_due_day = current_order['due_day']

            production_in_interval = 0.0
            for production_day, production_kg in sku_production:
                within_interval = production_day > previous_due_day and production_day <= order_due_day
                if within_interval:
                    production_in_interval += production_kg

            available_balance = previous_inventory + production_in_interval
            order_fully_covered = available_balance >= current_order['quantity']
            if order_fully_covered:
                delayed_quantity = 0.0
                next_inventory = available_balance - current_order['quantity']
            else:
                delayed_quantity = current_order['quantity'] - available_balance
                next_inventory = 0.0

            orders_result.append({
                'sku': sku, 'product': current_order['product'], 'color': current_order['color'],
                'due_day': order_due_day, 'quantity': current_order['quantity'],
                'delayed_qty': delayed_quantity,
            })

            previous_inventory = next_inventory
            previous_due_day = order_due_day

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
        'status': 'Optimal',
        'method': 'heuristic',
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
