import time

import pulp
import pandas as pd


def clean_name(str_raw):
    return str(str_raw).replace(' ', '_').replace(':', '_').replace('-', '_').replace('/', '_')


def build_daily_scenario(dict_instance, dict_settings, dict_weekly_result):
    timestamp_start = pd.Timestamp(dict_settings['start_week'])
    int_frozen_weeks = int(dict_settings['frozen_weeks'])
    int_shifts_per_day = int(dict_settings['shifts_per_day'])
    int_working_days = int(dict_settings['working_days_per_week'])
    float_hours_per_shift = float(dict_settings['hours_per_shift'])

    list_frozen_weeks = []
    for timestamp_week in dict_instance['weeks']:
        if timestamp_week >= timestamp_start and len(list_frozen_weeks) < int_frozen_weeks:
            list_frozen_weeks.append(timestamp_week)

    list_shifts = []
    for timestamp_week in list_frozen_weeks:
        for int_day in range(int_working_days):
            for int_shift in range(int_shifts_per_day):
                list_shifts.append({
                    'index': len(list_shifts),
                    'date': timestamp_week + pd.Timedelta(days=int_day),
                    'shift_number': int_shift + 1,
                    'day_index': len(list_shifts) // int_shifts_per_day,
                    'week': timestamp_week,
                })

    dict_color_weight = {}
    for str_product in dict_instance['products']:
        dict_color_weight[str_product] = {}
    for dict_order in dict_instance['orders']:
        for dict_item in dict_order['items']:
            str_product = dict_item['product']
            if dict_item['color'] not in dict_color_weight[str_product]:
                dict_color_weight[str_product][dict_item['color']] = 0.0
            dict_color_weight[str_product][dict_item['color']] += dict_item['quantity']
    for str_product in dict_color_weight:
        float_total = 0.0
        for str_color in dict_color_weight[str_product]:
            float_total += dict_color_weight[str_product][str_color]
        if float_total > 0.0:
            for str_color in dict_color_weight[str_product]:
                dict_color_weight[str_product][str_color] = dict_color_weight[str_product][str_color] / float_total
        else:
            list_colors = dict_instance['colors_by_product'][str_product]
            for str_color in list_colors:
                dict_color_weight[str_product][str_color] = 1.0 / len(list_colors)

    dict_skus_of_product = {}
    dict_product_of_sku = {}
    dict_color_of_sku = {}
    for str_product in dict_instance['products']:
        dict_skus_of_product[str_product] = []
        for str_color in dict_instance['colors_by_product'][str_product]:
            str_sku = f'{str_product}-{str_color}'
            dict_skus_of_product[str_product].append(str_sku)
            dict_product_of_sku[str_sku] = str_product
            dict_color_of_sku[str_sku] = str_color

    dict_orders_by_sku_shift = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            for dict_shift in list_shifts:
                dict_orders_by_sku_shift[(str_sku, dict_shift['index'])] = 0.0

    timestamp_first_date = list_shifts[0]['date']
    timestamp_last_date = list_shifts[-1]['date']
    for dict_order in dict_instance['orders']:
        int_target_shift = None
        for dict_shift in list_shifts:
            if dict_shift['date'] <= dict_order['due_date']:
                int_target_shift = dict_shift['index']
        if dict_order['due_date'] < timestamp_first_date:
            int_target_shift = 0
        if dict_order['due_date'] > timestamp_last_date:
            int_target_shift = None
        if int_target_shift is not None:
            for dict_item in dict_order['items']:
                tuple_key = (dict_item['sku'], int_target_shift)
                if tuple_key in dict_orders_by_sku_shift:
                    dict_orders_by_sku_shift[tuple_key] += dict_item['quantity']

    dict_forecast_by_sku_shift = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            for dict_shift in list_shifts:
                dict_forecast_by_sku_shift[(str_sku, dict_shift['index'])] = 0.0
    int_shifts_per_week = int_working_days * int_shifts_per_day
    for str_product in dict_instance['products']:
        for timestamp_week in list_frozen_weeks:
            float_weekly_forecast = 0.0
            for dict_row in dict_weekly_result['demand']:
                if dict_row['product'] == str_product and dict_row['week'] == timestamp_week.strftime('%Y-%m-%d'):
                    float_weekly_forecast = dict_row['forecast']
            for str_color in dict_color_weight[str_product]:
                str_sku = f'{str_product}-{str_color}'
                if str_sku in dict_product_of_sku:
                    for dict_shift in list_shifts:
                        if dict_shift['week'] == timestamp_week:
                            float_share = dict_color_weight[str_product][str_color]
                            dict_forecast_by_sku_shift[(str_sku, dict_shift['index'])] += (
                                float_weekly_forecast * float_share / int_shifts_per_week)

    dict_target = {}
    timestamp_last_week = list_frozen_weeks[-1]
    for str_product in dict_instance['products']:
        dict_target[str_product] = dict_weekly_result['targets'][str_product][
            timestamp_last_week.strftime('%Y-%m-%d')]

    dict_machines_of_product = {}
    for str_product in dict_instance['products']:
        dict_machines_of_product[str_product] = []
        for str_machine in dict_settings['active_machines']:
            if str_machine in dict_instance['productivity'][str_product]:
                dict_machines_of_product[str_product].append(str_machine)

    dict_products_of_machine = {}
    for str_machine in dict_settings['active_machines']:
        dict_products_of_machine[str_machine] = []
        for str_product in dict_instance['products']:
            if str_machine in dict_machines_of_product[str_product]:
                dict_products_of_machine[str_machine].append(str_product)

    dict_shift_capacity = {}
    for str_machine in dict_settings['active_machines']:
        for dict_shift in list_shifts:
            float_availability = dict_instance['availability'][str_machine][dict_shift['week']]
            dict_shift_capacity[(str_machine, dict_shift['index'])] = float_hours_per_shift * float_availability

    dict_setup_hourly_cost = {}
    for str_machine in dict_settings['active_machines']:
        if str_machine in dict_settings['setup_hourly_cost_by_machine']:
            dict_setup_hourly_cost[str_machine] = float(
                dict_settings['setup_hourly_cost_by_machine'][str_machine])
        else:
            dict_setup_hourly_cost[str_machine] = float(dict_settings['setup_hourly_cost_default'])

    dict_initial_stock = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            if str_sku in dict_instance['color_initial_stock']:
                dict_initial_stock[str_sku] = dict_instance['color_initial_stock'][str_sku]
            else:
                dict_initial_stock[str_sku] = 0.0

    return {
        'shifts': list_shifts,
        'machines': list(dict_settings['active_machines']),
        'products': dict_instance['products'],
        'skus_of_product': dict_skus_of_product,
        'product_of_sku': dict_product_of_sku,
        'color_of_sku': dict_color_of_sku,
        'machines_of_product': dict_machines_of_product,
        'products_of_machine': dict_products_of_machine,
        'shift_capacity': dict_shift_capacity,
        'productivity': dict_instance['productivity'],
        'form_setup': dict_instance['form_setup'],
        'color_setup': dict_instance['color_setup'],
        'orders': dict_orders_by_sku_shift,
        'forecast': dict_forecast_by_sku_shift,
        'initial_stock': dict_initial_stock,
        'target': dict_target,
        'min_lot': dict_instance['min_lot'],
        'unit_cost': dict_instance['unit_cost'],
        'margin': dict_instance['margin'],
        'setup_hourly_cost': dict_setup_hourly_cost,
        'positions': int(dict_settings['positions_per_shift']),
        'shifts_per_week': int_shifts_per_week,
    }


def solve_daily_model(dict_scenario, dict_settings):
    list_shifts = dict_scenario['shifts']
    list_machines = dict_scenario['machines']
    list_products = dict_scenario['products']
    int_positions = dict_scenario['positions']

    float_holding_rate = float(dict_settings['annual_holding_rate'])
    float_backlog_multiplier = float(dict_settings['order_backlog_multiplier'])
    float_coverage_weight = float(dict_settings['coverage_weight'])

    problem = pulp.LpProblem('DailyScheduling', pulp.LpMinimize)

    dict_mount = {}
    dict_active = {}
    dict_color_state = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            dict_active[(str_machine, int_shift)] = pulp.LpVariable(
                f'act_{str_machine}_{int_shift}', lowBound=0, upBound=1)
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                dict_mount[(str_product, str_machine, int_shift)] = pulp.LpVariable(
                    f'mnt_{clean_name(str_product)}_{str_machine}_{int_shift}', lowBound=0, upBound=1)
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    dict_color_state[(str_sku, str_machine, int_shift)] = pulp.LpVariable(
                        f'cs_{clean_name(str_sku)}_{str_machine}_{int_shift}', lowBound=0, upBound=1)

    dict_slot = {}
    dict_quantity = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_position in range(int_positions):
                        tuple_key = (str_sku, str_machine, int_shift, int_position)
                        str_label = f'{clean_name(str_sku)}_{str_machine}_{int_shift}_{int_position}'
                        dict_slot[tuple_key] = pulp.LpVariable(f'v_{str_label}', cat='Binary')
                        dict_quantity[tuple_key] = pulp.LpVariable(f'x_{str_label}', lowBound=0)

    dict_form_change = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            if int_shift > 0:
                for str_from in dict_scenario['products_of_machine'][str_machine]:
                    for str_to in dict_scenario['products_of_machine'][str_machine]:
                        if str_from != str_to:
                            tuple_key = (str_from, str_to, str_machine, int_shift)
                            str_label = f'{clean_name(str_from)}_{clean_name(str_to)}_{str_machine}_{int_shift}'
                            dict_form_change[tuple_key] = pulp.LpVariable(
                                f'phi_{str_label}', lowBound=0, upBound=1)

    dict_color_change = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_from in dict_scenario['skus_of_product'][str_product]:
                    for str_to in dict_scenario['skus_of_product'][str_product]:
                        if str_from != str_to:
                            for int_position in range(int_positions):
                                bool_inside = int_position > 0
                                bool_boundary = int_position == 0 and int_shift > 0
                                if bool_inside or bool_boundary:
                                    tuple_pair = (dict_scenario['color_of_sku'][str_from],
                                                  dict_scenario['color_of_sku'][str_to])
                                    if tuple_pair in dict_scenario['color_setup']:
                                        tuple_key = (str_from, str_to, str_machine, int_shift, int_position)
                                        str_label = (f'{clean_name(str_from)}_{clean_name(str_to)}'
                                                     f'_{str_machine}_{int_shift}_{int_position}')
                                        dict_color_change[tuple_key] = pulp.LpVariable(
                                            f'zc_{str_label}', lowBound=0, upBound=1)

    dict_inventory = {}
    dict_backlog = {}
    dict_lost = {}
    dict_deliver_order = {}
    dict_deliver_forecast = {}
    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                tuple_key = (str_sku, int_shift)
                str_label = f'{clean_name(str_sku)}_{int_shift}'
                dict_inventory[tuple_key] = pulp.LpVariable(f'Ic_{str_label}', lowBound=0)
                dict_backlog[tuple_key] = pulp.LpVariable(f'ac_{str_label}', lowBound=0)
                dict_lost[tuple_key] = pulp.LpVariable(f'lc_{str_label}', lowBound=0)
                dict_deliver_order[tuple_key] = pulp.LpVariable(f'eo_{str_label}', lowBound=0)
                dict_deliver_forecast[tuple_key] = pulp.LpVariable(f'ed_{str_label}', lowBound=0)

    dict_target_slack = {}
    for str_product in list_products:
        dict_target_slack[str_product] = pulp.LpVariable(
            f'g_{clean_name(str_product)}', lowBound=0)

    list_objective_terms = []
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        float_unit_cost = dict_scenario['unit_cost'][str_product]
        list_objective_terms.append(float_coverage_weight * float_margin * dict_target_slack[str_product])
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for int_index in range(len(list_shifts)):
                tuple_key = (str_sku, int_index)
                list_objective_terms.append(
                    float_backlog_multiplier * float_margin * dict_backlog[tuple_key])
                list_objective_terms.append(float_margin * dict_lost[tuple_key])
                float_holding_per_shift = (float_holding_rate * float_unit_cost
                                           / (52.0 * dict_scenario['shifts_per_week']))
                if int_index == 0:
                    list_objective_terms.append(
                        float_holding_per_shift * 0.5 * dict_scenario['initial_stock'][str_sku])
                else:
                    list_objective_terms.append(
                        float_holding_per_shift * 0.5 * dict_inventory[(str_sku, int_index - 1)])
                list_objective_terms.append(float_holding_per_shift * 0.5 * dict_inventory[tuple_key])

    for tuple_key in dict_form_change:
        str_from, str_to, str_machine, int_shift = tuple_key
        float_hours = dict_scenario['form_setup'][(str_from, str_to)]
        list_objective_terms.append(
            dict_scenario['setup_hourly_cost'][str_machine] * float_hours * dict_form_change[tuple_key])

    for tuple_key in dict_color_change:
        str_from, str_to, str_machine, int_shift, int_position = tuple_key
        tuple_pair = (dict_scenario['color_of_sku'][str_from], dict_scenario['color_of_sku'][str_to])
        float_hours = dict_scenario['color_setup'][tuple_pair]
        list_objective_terms.append(
            dict_scenario['setup_hourly_cost'][str_machine] * float_hours * dict_color_change[tuple_key])

    problem += pulp.lpSum(list_objective_terms)

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            list_mount_terms = []
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                list_mount_terms.append(dict_mount[(str_product, str_machine, int_shift)])
            problem += pulp.lpSum(list_mount_terms) <= 1
            problem += dict_active[(str_machine, int_shift)] <= pulp.lpSum(list_mount_terms)

            for int_position in range(int_positions):
                list_slot_terms = []
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        list_slot_terms.append(dict_slot[(str_sku, str_machine, int_shift, int_position)])
                problem += pulp.lpSum(list_slot_terms) == dict_active[(str_machine, int_shift)]

            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_position in range(int_positions):
                        problem += (dict_slot[(str_sku, str_machine, int_shift, int_position)]
                                    <= dict_mount[(str_product, str_machine, int_shift)])

                list_state_terms = []
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    list_state_terms.append(dict_color_state[(str_sku, str_machine, int_shift)])
                problem += pulp.lpSum(list_state_terms) == dict_mount[(str_product, str_machine, int_shift)]

                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    problem += (dict_color_state[(str_sku, str_machine, int_shift)]
                                >= dict_slot[(str_sku, str_machine, int_shift, int_positions - 1)])

            if int_shift > 0:
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    problem += (dict_mount[(str_product, str_machine, int_shift)]
                                - dict_mount[(str_product, str_machine, int_shift - 1)]
                                <= dict_active[(str_machine, int_shift)])
                    problem += (dict_mount[(str_product, str_machine, int_shift - 1)]
                                - dict_mount[(str_product, str_machine, int_shift)]
                                <= dict_active[(str_machine, int_shift)])
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        problem += (dict_color_state[(str_sku, str_machine, int_shift)]
                                    - dict_color_state[(str_sku, str_machine, int_shift - 1)]
                                    <= dict_active[(str_machine, int_shift)])
                        problem += (dict_color_state[(str_sku, str_machine, int_shift - 1)]
                                    - dict_color_state[(str_sku, str_machine, int_shift)]
                                    <= dict_active[(str_machine, int_shift)])

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            if int_shift > 0:
                for str_from in dict_scenario['products_of_machine'][str_machine]:
                    for str_to in dict_scenario['products_of_machine'][str_machine]:
                        if str_from != str_to:
                            problem += (dict_form_change[(str_from, str_to, str_machine, int_shift)]
                                        >= dict_mount[(str_from, str_machine, int_shift - 1)]
                                        + dict_mount[(str_to, str_machine, int_shift)] - 1)

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_from in dict_scenario['skus_of_product'][str_product]:
                    for str_to in dict_scenario['skus_of_product'][str_product]:
                        if str_from != str_to:
                            for int_position in range(int_positions):
                                if int_position > 0:
                                    variable_previous = dict_slot[
                                        (str_from, str_machine, int_shift, int_position - 1)]
                                    variable_current = dict_slot[
                                        (str_to, str_machine, int_shift, int_position)]
                                elif int_shift > 0:
                                    variable_previous = dict_color_state[
                                        (str_from, str_machine, int_shift - 1)]
                                    variable_current = dict_slot[
                                        (str_to, str_machine, int_shift, 0)]
                                else:
                                    variable_previous = None
                                    variable_current = None
                                if variable_previous is not None:
                                    tuple_key = (str_from, str_to, str_machine, int_shift, int_position)
                                    if tuple_key in dict_color_change:
                                        problem += (dict_color_change[tuple_key]
                                                    >= variable_previous + variable_current - 1)
                                    else:
                                        problem += variable_previous + variable_current <= 1

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            list_capacity_terms = []
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                float_rate = dict_scenario['productivity'][str_product][str_machine]
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_position in range(int_positions):
                        list_capacity_terms.append(
                            dict_quantity[(str_sku, str_machine, int_shift, int_position)] / float_rate)
            for tuple_key in dict_form_change:
                if tuple_key[2] == str_machine and tuple_key[3] == int_shift:
                    float_hours = dict_scenario['form_setup'][(tuple_key[0], tuple_key[1])]
                    list_capacity_terms.append(float_hours * dict_form_change[tuple_key])
            for tuple_key in dict_color_change:
                if tuple_key[2] == str_machine and tuple_key[3] == int_shift:
                    tuple_pair = (dict_scenario['color_of_sku'][tuple_key[0]],
                                  dict_scenario['color_of_sku'][tuple_key[1]])
                    float_hours = dict_scenario['color_setup'][tuple_pair]
                    list_capacity_terms.append(float_hours * dict_color_change[tuple_key])
            problem += (pulp.lpSum(list_capacity_terms)
                        <= dict_scenario['shift_capacity'][(str_machine, int_shift)])

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            float_capacity = dict_scenario['shift_capacity'][(str_machine, int_shift)]
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                float_rate = dict_scenario['productivity'][str_product][str_machine]
                float_min_lot = dict_scenario['min_lot'][str_product]
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_position in range(int_positions):
                        tuple_key = (str_sku, str_machine, int_shift, int_position)
                        problem += (dict_quantity[tuple_key]
                                    <= float_rate * float_capacity * dict_slot[tuple_key])
                        if int_position > 0:
                            variable_previous = dict_slot[
                                (str_sku, str_machine, int_shift, int_position - 1)]
                        elif int_shift > 0:
                            variable_previous = dict_color_state[
                                (str_sku, str_machine, int_shift - 1)]
                        else:
                            variable_previous = 0
                        problem += (dict_quantity[tuple_key]
                                    >= float_min_lot * (dict_slot[tuple_key] - variable_previous))

    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for int_index in range(len(list_shifts)):
                tuple_key = (str_sku, int_index)
                list_production_terms = []
                for str_machine in dict_scenario['machines_of_product'][str_product]:
                    for int_position in range(int_positions):
                        list_production_terms.append(
                            dict_quantity[(str_sku, str_machine, int_index, int_position)])

                if int_index == 0:
                    expression_previous_stock = dict_scenario['initial_stock'][str_sku]
                    expression_previous_backlog = 0.0
                else:
                    expression_previous_stock = dict_inventory[(str_sku, int_index - 1)]
                    expression_previous_backlog = dict_backlog[(str_sku, int_index - 1)]

                float_orders = dict_scenario['orders'][(str_sku, int_index)]
                float_forecast = dict_scenario['forecast'][(str_sku, int_index)]

                problem += (dict_inventory[tuple_key]
                            == expression_previous_stock + pulp.lpSum(list_production_terms)
                            - dict_deliver_order[tuple_key] - dict_deliver_forecast[tuple_key])
                problem += (dict_backlog[tuple_key]
                            == expression_previous_backlog + float_orders - dict_deliver_order[tuple_key])
                problem += (dict_deliver_forecast[tuple_key] + dict_lost[tuple_key] == float_forecast)

    for str_product in list_products:
        list_final_stock_terms = []
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            list_final_stock_terms.append(dict_inventory[(str_sku, len(list_shifts) - 1)])
        problem += (pulp.lpSum(list_final_stock_terms) + dict_target_slack[str_product]
                    >= dict_scenario['target'][str_product])

    str_solver_name = str(dict_settings['daily_solver_name']).upper()
    int_time_limit = int(dict_settings['daily_time_limit'])
    if str_solver_name == 'GUROBI':
        list_options = [('TimeLimit', int_time_limit)]
        if dict_settings['threads']:
            list_options.append(('Threads', dict_settings['threads']))
        solver_instance = pulp.GUROBI_CMD(msg=0, options=list_options)
    else:
        dict_arguments = {'msg': 0, 'timeLimit': int_time_limit}
        if dict_settings['threads']:
            dict_arguments['threads'] = dict_settings['threads']
        solver_instance = pulp.PULP_CBC_CMD(**dict_arguments)

    float_started_at = time.perf_counter()
    problem.solve(solver_instance)
    float_solve_seconds = time.perf_counter() - float_started_at
    bool_hit_time_limit = float_solve_seconds >= 0.98 * int_time_limit

    str_status = pulp.LpStatus[problem.status]
    if str_status not in ('Optimal', 'Feasible'):
        return {'status': str_status, 'kpis': {}}

    def resolve(variable):
        if isinstance(variable, float):
            return variable
        elif isinstance(variable, int):
            return float(variable)
        elif variable.varValue is None:
            return 0.0
        else:
            return variable.varValue

    float_max_fractional = 0.0
    for tuple_key in dict_mount:
        float_value = resolve(dict_mount[tuple_key])
        float_gap = abs(float_value - round(float_value))
        if float_gap > float_max_fractional:
            float_max_fractional = float_gap
    for tuple_key in dict_active:
        float_value = resolve(dict_active[tuple_key])
        float_gap = abs(float_value - round(float_value))
        if float_gap > float_max_fractional:
            float_max_fractional = float_gap
    for tuple_key in dict_color_state:
        float_value = resolve(dict_color_state[tuple_key])
        float_gap = abs(float_value - round(float_value))
        if float_gap > float_max_fractional:
            float_max_fractional = float_gap
    for tuple_key in dict_form_change:
        float_value = resolve(dict_form_change[tuple_key])
        float_gap = abs(float_value - round(float_value))
        if float_gap > float_max_fractional:
            float_max_fractional = float_gap
    for tuple_key in dict_color_change:
        float_value = resolve(dict_color_change[tuple_key])
        float_gap = abs(float_value - round(float_value))
        if float_gap > float_max_fractional:
            float_max_fractional = float_gap

    list_schedule_rows = []
    float_form_setup_hours = 0.0
    float_color_setup_hours = 0.0
    float_setup_cost = 0.0

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for int_position in range(int_positions):
                str_active_sku = None
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        if resolve(dict_slot[(str_sku, str_machine, int_shift, int_position)]) > 0.5:
                            str_active_sku = str_sku
                if str_active_sku is not None:
                    str_product = dict_scenario['product_of_sku'][str_active_sku]
                    float_rate = dict_scenario['productivity'][str_product][str_machine]
                    float_quantity = resolve(
                        dict_quantity[(str_active_sku, str_machine, int_shift, int_position)])

                    float_form_hours = 0.0
                    str_previous_form = '-'
                    for tuple_key in dict_form_change:
                        if (tuple_key[1] == str_product and tuple_key[2] == str_machine
                                and tuple_key[3] == int_shift and int_position == 0):
                            if resolve(dict_form_change[tuple_key]) > 0.5:
                                float_form_hours = dict_scenario['form_setup'][(tuple_key[0], tuple_key[1])]
                                str_previous_form = tuple_key[0]

                    float_color_hours = 0.0
                    str_previous_color = '-'
                    for tuple_key in dict_color_change:
                        if (tuple_key[1] == str_active_sku and tuple_key[2] == str_machine
                                and tuple_key[3] == int_shift and tuple_key[4] == int_position):
                            if resolve(dict_color_change[tuple_key]) > 0.5:
                                tuple_pair = (dict_scenario['color_of_sku'][tuple_key[0]],
                                              dict_scenario['color_of_sku'][tuple_key[1]])
                                float_color_hours = dict_scenario['color_setup'][tuple_pair]
                                str_previous_color = dict_scenario['color_of_sku'][tuple_key[0]]

                    if float_quantity > 1e-6 or float_form_hours > 0.0 or float_color_hours > 0.0:
                        list_schedule_rows.append({
                            'date': dict_shift['date'].strftime('%Y-%m-%d'),
                            'shift': dict_shift['shift_number'],
                            'shift_index': int_shift,
                            'machine': str_machine,
                            'position': int_position + 1,
                            'product': str_product,
                            'color': dict_scenario['color_of_sku'][str_active_sku],
                            'sku': str_active_sku,
                            'kg': float_quantity,
                            'production_hours': float_quantity / float_rate,
                            'form_setup_hours': float_form_hours,
                            'color_setup_hours': float_color_hours,
                            'previous_form': str_previous_form,
                            'previous_color': str_previous_color,
                        })
                    float_form_setup_hours += float_form_hours
                    float_color_setup_hours += float_color_hours
                    float_setup_cost += dict_scenario['setup_hourly_cost'][str_machine] * (
                        float_form_hours + float_color_hours)

    list_order_rows = []
    float_backlog_cost = 0.0
    float_lost_cost = 0.0
    float_holding_cost = 0.0
    float_total_orders = 0.0
    float_total_forecast = 0.0
    float_total_lost = 0.0
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        float_unit_cost = dict_scenario['unit_cost'][str_product]
        float_holding_per_shift = (float_holding_rate * float_unit_cost
                                   / (52.0 * dict_scenario['shifts_per_week']))
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for int_index in range(len(list_shifts)):
                tuple_key = (str_sku, int_index)
                float_backlog = resolve(dict_backlog[tuple_key])
                float_lost = resolve(dict_lost[tuple_key])
                float_inventory = resolve(dict_inventory[tuple_key])
                if int_index == 0:
                    float_previous_stock = dict_scenario['initial_stock'][str_sku]
                else:
                    float_previous_stock = resolve(dict_inventory[(str_sku, int_index - 1)])
                float_backlog_cost += float_backlog_multiplier * float_margin * float_backlog
                float_lost_cost += float_margin * float_lost
                float_holding_cost += float_holding_per_shift * 0.5 * (float_previous_stock + float_inventory)
                float_total_orders += dict_scenario['orders'][(str_sku, int_index)]
                float_total_forecast += dict_scenario['forecast'][(str_sku, int_index)]
                float_total_lost += float_lost
                list_order_rows.append({
                    'sku': str_sku, 'product': str_product,
                    'color': dict_scenario['color_of_sku'][str_sku],
                    'shift_index': int_index,
                    'date': list_shifts[int_index]['date'].strftime('%Y-%m-%d'),
                    'shift': list_shifts[int_index]['shift_number'],
                    'orders': dict_scenario['orders'][(str_sku, int_index)],
                    'forecast': dict_scenario['forecast'][(str_sku, int_index)],
                    'delivered_orders': resolve(dict_deliver_order[tuple_key]),
                    'delivered_forecast': resolve(dict_deliver_forecast[tuple_key]),
                    'backlog': float_backlog, 'lost': float_lost, 'inventory': float_inventory,
                })

    list_target_rows = []
    float_coverage_cost = 0.0
    for str_product in list_products:
        float_slack = resolve(dict_target_slack[str_product])
        float_final_stock = 0.0
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            float_final_stock += resolve(dict_inventory[(str_sku, len(list_shifts) - 1)])
        float_coverage_cost += float_coverage_weight * dict_scenario['margin'][str_product] * float_slack
        list_target_rows.append({
            'product': str_product,
            'target': dict_scenario['target'][str_product],
            'final_stock': float_final_stock,
            'slack': float_slack,
        })

    float_final_backlog = 0.0
    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            float_final_backlog += resolve(dict_backlog[(str_sku, len(list_shifts) - 1)])

    if float_total_orders > 0:
        float_order_service = (1.0 - float_final_backlog / float_total_orders) * 100.0
    else:
        float_order_service = 100.0
    if float_total_forecast > 0:
        float_forecast_service = (1.0 - float_total_lost / float_total_forecast) * 100.0
    else:
        float_forecast_service = 100.0

    return {
        'status': str_status,
        'schedule': list_schedule_rows,
        'orders': list_order_rows,
        'targets': list_target_rows,
        'shifts': len(list_shifts),
        'kpis': {
            'total_cost': (float_backlog_cost + float_lost_cost + float_coverage_cost
                           + float_setup_cost + float_holding_cost),
            'backlog_cost': float_backlog_cost,
            'lost_sales_cost': float_lost_cost,
            'coverage_cost': float_coverage_cost,
            'setup_cost': float_setup_cost,
            'holding_cost': float_holding_cost,
            'order_service_level': float_order_service,
            'forecast_service_level': float_forecast_service,
            'form_setup_hours': float_form_setup_hours,
            'color_setup_hours': float_color_setup_hours,
            'total_setups': len(list_schedule_rows),
            'solve_seconds': float_solve_seconds,
            'hit_time_limit': bool_hit_time_limit,
            'max_fractional_deviation': float_max_fractional,
        },
    }
