import pandas as pd


def build_color_scheduling_problem(tactical_solver, color_orders, color_initial_stock,
                                   color_setup_matrix, setup_time_color_default):
    windows = []
    for machine in tactical_solver.active_machines:
        for product in tactical_solver.machine_products[machine]:
            current_window_days = []
            for day in tactical_solver.all_days:
                state_variable = tactical_solver.S_state[(machine, product, day)]
                day_in_production = state_variable.varValue is not None and state_variable.varValue > 0.5
                if day_in_production:
                    current_window_days.append(day)
                else:
                    if len(current_window_days) > 0:
                        windows.append({'machine': machine, 'product': product, 'days': current_window_days})
                    current_window_days = []
            if len(current_window_days) > 0:
                windows.append({'machine': machine, 'product': product, 'days': current_window_days})

    colors_by_product = {}
    for order in color_orders:
        order_product = order['product']
        if order_product not in colors_by_product:
            colors_by_product[order_product] = []
        if order['color'] not in colors_by_product[order_product]:
            colors_by_product[order_product].append(order['color'])
    for sku_with_stock in color_initial_stock:
        sku_parts = sku_with_stock.split('-')
        sku_product = f'{sku_parts[0]}-{sku_parts[1]}'
        sku_color = sku_parts[2]
        if sku_product not in colors_by_product:
            colors_by_product[sku_product] = []
        if sku_color not in colors_by_product[sku_product]:
            colors_by_product[sku_product].append(sku_color)

    orders_by_sku = {}
    for order in color_orders:
        due_period = None
        for candidate_period in tactical_solver.periods:
            period_date = pd.to_datetime(candidate_period)
            due_date_in_same_month = (order['due_date'].year == period_date.year
                                      and order['due_date'].month == period_date.month)
            if due_date_in_same_month:
                due_period = candidate_period

        if due_period is None:
            due_global_day = tactical_solver.all_days[-1]
        else:
            period_days = tactical_solver.days_in_period[due_period]
            days_in_month = order['due_date'].days_in_month
            relative_position = (order['due_date'].day - 1) / days_in_month
            day_index = int(relative_position * len(period_days))
            if day_index >= len(period_days):
                day_index = len(period_days) - 1
            due_global_day = period_days[day_index]

        order_with_global_day = {
            'quantity': order['quantity'],
            'due_day': due_global_day,
            'product': order['product'],
            'color': order['color'],
        }
        if order['sku'] not in orders_by_sku:
            orders_by_sku[order['sku']] = []
        orders_by_sku[order['sku']].append(order_with_global_day)

    for sku_with_orders in orders_by_sku:
        orders_by_sku[sku_with_orders] = sorted(orders_by_sku[sku_with_orders], key=lambda order: order['due_day'])

    daily_capacity = {}
    for window in windows:
        for day in window['days']:
            daily_capacity[(window['machine'], day)] = tactical_solver.daily_capacity[(window['machine'], day)]

    return {
        'windows': windows,
        'colors_by_product': colors_by_product,
        'orders_by_sku': orders_by_sku,
        'initial_stock_by_sku': color_initial_stock,
        'daily_capacity': daily_capacity,
        'productivity': tactical_solver.productivity,
        'costs': tactical_solver.costs,
        'setup_matrix': color_setup_matrix,
        'setup_time_color_default': setup_time_color_default,
    }
