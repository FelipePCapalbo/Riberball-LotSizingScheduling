import time

import pulp
import pandas as pd

from optimization.solver import solve_lexicographic


def clean_name(str_raw):
    return str(str_raw).replace(' ', '_').replace(':', '_').replace('-', '_').replace('/', '_')


def complete_setup_matrix(dict_registered, list_items):
    float_cleaning = 0.0
    for tuple_pair in dict_registered:
        if tuple_pair[0] != tuple_pair[1] and dict_registered[tuple_pair] > float_cleaning:
            float_cleaning = dict_registered[tuple_pair]
    dict_complete = {}
    for str_to in list_items:
        dict_complete[('0', str_to)] = float_cleaning
        for str_from in list_items:
            if str_from == str_to:
                dict_complete[(str_from, str_to)] = 0.0
            elif (str_from, str_to) in dict_registered:
                dict_complete[(str_from, str_to)] = dict_registered[(str_from, str_to)]
            else:
                dict_complete[(str_from, str_to)] = float_cleaning
    return dict_complete


def build_color_reservation(dict_instance):
    list_colors = []
    for str_product in dict_instance['products']:
        for str_color in dict_instance['colors_by_product'][str_product]:
            if str_color not in list_colors:
                list_colors.append(str_color)
    dict_color_setup = complete_setup_matrix(dict_instance['color_setup'], list_colors)
    dict_color_reservation = {}
    for str_product in dict_instance['products']:
        for str_color in dict_instance['colors_by_product'][str_product]:
            float_reservation = 0.0
            for str_other in dict_instance['colors_by_product'][str_product]:
                if dict_color_setup[(str_other, str_color)] > float_reservation:
                    float_reservation = dict_color_setup[(str_other, str_color)]
            dict_color_reservation[f'{str_product}-{str_color}'] = float_reservation
    return dict_color_setup, dict_color_reservation


def build_weekly_scenario(dict_instance, dict_settings):
    timestamp_start = pd.Timestamp(dict_settings['start_week'])
    int_weeks_in_plan = int(dict_settings['weeks_in_plan'])

    list_all_weeks = dict_instance['weeks']
    list_weeks = []
    for timestamp_week in list_all_weeks:
        if timestamp_week >= timestamp_start and len(list_weeks) < int_weeks_in_plan:
            list_weeks.append(timestamp_week)

    dict_orders = {}
    for str_product in dict_instance['products']:
        dict_orders[str_product] = {}
        for timestamp_week in list_all_weeks:
            dict_orders[str_product][timestamp_week] = 0.0

    for dict_order in dict_instance['orders']:
        timestamp_due_week = None
        for timestamp_week in list_all_weeks:
            if timestamp_week <= dict_order['due_date']:
                timestamp_due_week = timestamp_week
        if timestamp_due_week is None:
            timestamp_due_week = list_all_weeks[0]
        for dict_item in dict_order['items']:
            dict_orders[dict_item['product']][timestamp_due_week] += dict_item['quantity']

    dict_forecast = {}
    for str_product in dict_instance['products']:
        dict_forecast[str_product] = {}
        for timestamp_week in list_all_weeks:
            float_net = dict_instance['demand'][str_product][timestamp_week] - dict_orders[str_product][timestamp_week]
            if float_net < 0.0:
                float_net = 0.0
            dict_forecast[str_product][timestamp_week] = float_net

    dict_stock_minimum = {}
    for str_product in dict_instance['products']:
        float_mts_share = 0.0
        for str_color in dict_instance['colors_by_product'][str_product]:
            if dict_instance['sku_is_mts'][f'{str_product}-{str_color}']:
                if str_color in dict_instance['color_mix'][str_product]:
                    float_mts_share += dict_instance['color_mix'][str_product][str_color]
        float_average_forecast = 0.0
        for timestamp_week in list_weeks:
            float_average_forecast += dict_instance['demand'][str_product][timestamp_week]
        float_average_forecast = float_average_forecast / len(list_weeks)
        float_mts_demand = float_average_forecast * float_mts_share
        dict_stock_minimum[str_product] = float_mts_demand * (1.0 + dict_instance['mape'][str_product] / 100.0)

    float_hours_per_week = (float(dict_settings['working_days_per_week'])
                            * float(dict_settings['shifts_per_day'])
                            * float(dict_settings['hours_per_shift']))
    dict_capacity = {}
    for str_machine in dict_instance['machines']:
        dict_capacity[str_machine] = {}
        for timestamp_week in list_weeks:
            float_availability = dict_instance['availability'][str_machine][timestamp_week]
            dict_capacity[str_machine][timestamp_week] = float_hours_per_week * float_availability

    dict_form_setup = complete_setup_matrix(dict_instance['form_setup'], dict_instance['products'])
    dict_color_setup, dict_color_reservation = build_color_reservation(dict_instance)
    dict_average_setup = {}
    for str_product in dict_instance['products']:
        float_form_total = 0.0
        for str_other in dict_instance['products']:
            float_form_total += dict_form_setup[(str_other, str_product)]
        float_color_total = 0.0
        for str_color in dict_instance['colors_by_product'][str_product]:
            float_color_total += dict_color_reservation[f'{str_product}-{str_color}']
        dict_average_setup[str_product] = float_form_total / len(dict_instance['products']) + float_color_total

    dict_machines_of_product = {}
    for str_product in dict_instance['products']:
        dict_machines_of_product[str_product] = []
        for str_machine in dict_instance['machines']:
            if str_machine in dict_instance['productivity'][str_product]:
                dict_machines_of_product[str_product].append(str_machine)

    float_warehouse_capacity = dict_settings['warehouse_capacity_kg']
    if float_warehouse_capacity is not None:
        float_initial_total = 0.0
        for str_product in dict_instance['products']:
            float_initial_total += dict_instance['initial_inventory'][str_product]
        float_warehouse_capacity = float(float_warehouse_capacity)
        if float_initial_total > float_warehouse_capacity:
            float_warehouse_capacity = float_initial_total

    return {
        'weeks': list_weeks,
        'products': dict_instance['products'],
        'machines': list(dict_instance['machines']),
        'orders': dict_orders,
        'forecast': dict_forecast,
        'stock_minimum': dict_stock_minimum,
        'capacity': dict_capacity,
        'productivity': dict_instance['productivity'],
        'machines_of_product': dict_machines_of_product,
        'average_setup': dict_average_setup,
        'setup_hourly_cost': dict_instance['setup_hourly_cost'],
        'initial_inventory': dict_instance['initial_inventory'],
        'min_lot': dict_instance['min_lot'],
        'unit_cost': dict_instance['unit_cost'],
        'margin': dict_instance['margin'],
        'warehouse_capacity': float_warehouse_capacity,
    }


def solve_weekly_model(dict_scenario, dict_settings):
    list_weeks = dict_scenario['weeks']
    list_products = dict_scenario['products']

    float_holding_rate = float(dict_settings['annual_holding_rate'])

    problem = pulp.LpProblem('WeeklyPlanning', pulp.LpMinimize)

    dict_production = {}
    dict_setup = {}
    for str_product in list_products:
        for str_machine in dict_scenario['machines_of_product'][str_product]:
            for timestamp_week in list_weeks:
                tuple_key = (str_product, str_machine, timestamp_week)
                str_label = f'{clean_name(str_product)}_{str_machine}_{clean_name(timestamp_week.date())}'
                dict_production[tuple_key] = pulp.LpVariable(f'x_{str_label}', lowBound=0)
                dict_setup[tuple_key] = pulp.LpVariable(f'y_{str_label}', cat='Binary')

    dict_inventory = {}
    dict_backlog = {}
    dict_lost = {}
    dict_floor_slack = {}
    for str_product in list_products:
        for timestamp_week in list_weeks:
            tuple_key = (str_product, timestamp_week)
            str_label = f'{clean_name(str_product)}_{clean_name(timestamp_week.date())}'
            dict_inventory[tuple_key] = pulp.LpVariable(f'I_{str_label}', lowBound=0)
            dict_backlog[tuple_key] = pulp.LpVariable(f'b_{str_label}', lowBound=0)
            dict_lost[tuple_key] = pulp.LpVariable(f'l_{str_label}', lowBound=0)
            dict_floor_slack[tuple_key] = pulp.LpVariable(f'g_{str_label}', lowBound=0)

    list_backlog_terms = []
    list_lost_terms = []
    list_floor_terms = []
    list_cost_terms = []
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        float_holding_per_week = (float_holding_rate / 52.0) * dict_scenario['unit_cost'][str_product]
        for int_index in range(len(list_weeks)):
            tuple_key = (str_product, list_weeks[int_index])
            list_backlog_terms.append(float_margin * dict_backlog[tuple_key])
            list_lost_terms.append(float_margin * dict_lost[tuple_key])
            list_floor_terms.append(float_margin * dict_floor_slack[tuple_key])
            list_cost_terms.append(float_holding_per_week * dict_inventory[tuple_key])

    for str_product in list_products:
        float_setup_time = dict_scenario['average_setup'][str_product]
        for str_machine in dict_scenario['machines_of_product'][str_product]:
            float_hourly_cost = dict_scenario['setup_hourly_cost'][str_machine]
            for timestamp_week in list_weeks:
                list_cost_terms.append(
                    float_hourly_cost * float_setup_time * dict_setup[(str_product, str_machine, timestamp_week)])

    for str_product in list_products:
        for int_index in range(len(list_weeks)):
            timestamp_week = list_weeks[int_index]
            tuple_key = (str_product, timestamp_week)
            str_label = f'{clean_name(str_product)}_{clean_name(timestamp_week.date())}'

            list_production_terms = []
            for str_machine in dict_scenario['machines_of_product'][str_product]:
                list_production_terms.append(dict_production[(str_product, str_machine, timestamp_week)])

            if int_index == 0:
                expression_previous_inventory = dict_scenario['initial_inventory'][str_product]
                expression_previous_backlog = 0.0
            else:
                tuple_previous = (str_product, list_weeks[int_index - 1])
                expression_previous_inventory = dict_inventory[tuple_previous]
                expression_previous_backlog = dict_backlog[tuple_previous]

            problem += (expression_previous_inventory + pulp.lpSum(list_production_terms)
                        + dict_backlog[tuple_key] + dict_lost[tuple_key]
                        == dict_inventory[tuple_key] + dict_scenario['orders'][str_product][timestamp_week]
                        + dict_scenario['forecast'][str_product][timestamp_week] + expression_previous_backlog,
                        f'balanco_{str_label}')

    for str_product in list_products:
        for timestamp_week in list_weeks:
            str_label = f'{clean_name(str_product)}_{clean_name(timestamp_week.date())}'
            problem += (dict_lost[(str_product, timestamp_week)]
                        <= dict_scenario['forecast'][str_product][timestamp_week],
                        f'folga_limite_{str_label}')

    for str_product in list_products:
        for timestamp_week in list_weeks:
            tuple_key = (str_product, timestamp_week)
            str_label = f'{clean_name(str_product)}_{clean_name(timestamp_week.date())}'
            problem += (dict_inventory[tuple_key] + dict_floor_slack[tuple_key]
                        >= dict_scenario['stock_minimum'][str_product],
                        f'piso_estoque_{str_label}')

    if dict_scenario['warehouse_capacity'] is not None:
        for timestamp_week in list_weeks:
            list_stock_terms = []
            for str_product in list_products:
                list_stock_terms.append(dict_inventory[(str_product, timestamp_week)])
            problem += (pulp.lpSum(list_stock_terms) <= dict_scenario['warehouse_capacity'],
                        f'capacidade_armazem_{clean_name(timestamp_week.date())}')

    for str_machine in dict_scenario['machines']:
        for timestamp_week in list_weeks:
            list_capacity_terms = []
            for str_product in list_products:
                if str_machine in dict_scenario['machines_of_product'][str_product]:
                    tuple_key = (str_product, str_machine, timestamp_week)
                    float_rate = dict_scenario['productivity'][str_product][str_machine]
                    list_capacity_terms.append(dict_production[tuple_key] / float_rate)
                    list_capacity_terms.append(dict_scenario['average_setup'][str_product] * dict_setup[tuple_key])
            problem += (pulp.lpSum(list_capacity_terms) <= dict_scenario['capacity'][str_machine][timestamp_week],
                        f'capacidade_semanal_{str_machine}_{clean_name(timestamp_week.date())}')

    for str_product in list_products:
        float_min_lot = dict_scenario['min_lot'][str_product]
        for int_index in range(len(list_weeks)):
            timestamp_week = list_weeks[int_index]
            float_remaining_demand = dict_scenario['stock_minimum'][str_product]
            for int_other in range(len(list_weeks)):
                timestamp_other = list_weeks[int_other]
                float_remaining_demand += dict_scenario['orders'][str_product][timestamp_other]
                if int_other >= int_index:
                    float_remaining_demand += dict_scenario['forecast'][str_product][timestamp_other]
            for str_machine in dict_scenario['machines_of_product'][str_product]:
                tuple_key = (str_product, str_machine, timestamp_week)
                str_label = f'{clean_name(str_product)}_{str_machine}_{clean_name(timestamp_week.date())}'
                float_rate = dict_scenario['productivity'][str_product][str_machine]
                float_big_m = float_rate * dict_scenario['capacity'][str_machine][timestamp_week]
                if float_remaining_demand < float_big_m:
                    float_big_m = float_remaining_demand
                problem += (float_min_lot * dict_setup[tuple_key] <= dict_production[tuple_key],
                            f'lote_minimo_inferior_{str_label}')
                problem += (dict_production[tuple_key] <= float_big_m * dict_setup[tuple_key],
                            f'lote_minimo_superior_{str_label}')

    list_stage_expressions = [pulp.lpSum(list_backlog_terms), pulp.lpSum(list_lost_terms),
                              pulp.lpSum(list_floor_terms), pulp.lpSum(list_cost_terms)]
    float_started_at = time.perf_counter()
    str_status, bool_hit_time_limit, list_stage_values, list_stage_reports = solve_lexicographic(
        problem, list_stage_expressions, dict_settings['weekly_solver_name'], int(dict_settings['weekly_time_limit']),
        dict_settings['threads'])
    float_solve_seconds = time.perf_counter() - float_started_at

    if str_status not in ('Optimal', 'Feasible'):
        dict_result = {'status': str_status, 'stage_reports': list_stage_reports, 'kpis': {}}
    else:
        def resolve(variable):
            if isinstance(variable, float):
                return variable
            elif variable.varValue is None:
                return 0.0
            else:
                return variable.varValue

        list_production_rows = []
        list_inventory_rows = []
        list_demand_rows = []
        dict_targets = {}
        float_setup_cost = 0.0
        float_setup_hours = 0.0
        float_holding_cost = 0.0
        float_backlog_cost = 0.0
        float_lost_cost = 0.0
        float_floor_slack_cost = 0.0

        for str_product in list_products:
            dict_targets[str_product] = {}
            float_margin = dict_scenario['margin'][str_product]
            float_holding_per_week = (float_holding_rate / 52.0) * dict_scenario['unit_cost'][str_product]
            for int_index in range(len(list_weeks)):
                timestamp_week = list_weeks[int_index]
                tuple_key = (str_product, timestamp_week)
                str_week = timestamp_week.strftime('%Y-%m-%d')

                float_inventory = resolve(dict_inventory[tuple_key])
                float_backlog = resolve(dict_backlog[tuple_key])
                float_lost = resolve(dict_lost[tuple_key])
                float_floor_slack = resolve(dict_floor_slack[tuple_key])
                dict_targets[str_product][str_week] = float_inventory

                if int_index == 0:
                    float_previous_backlog = 0.0
                else:
                    tuple_previous = (str_product, list_weeks[int_index - 1])
                    float_previous_backlog = resolve(dict_backlog[tuple_previous])

                float_orders = dict_scenario['orders'][str_product][timestamp_week]
                float_forecast = dict_scenario['forecast'][str_product][timestamp_week]

                list_inventory_rows.append({
                    'week': str_week, 'product': str_product,
                    'inventory': float_inventory,
                    'stock_minimum': dict_scenario['stock_minimum'][str_product],
                    'floor_slack': float_floor_slack,
                })
                list_demand_rows.append({
                    'week': str_week, 'product': str_product,
                    'orders': float_orders, 'forecast': float_forecast,
                    'delivered_orders': float_orders + float_previous_backlog - float_backlog,
                    'backlog': float_backlog,
                    'delivered_forecast': float_forecast - float_lost,
                    'lost': float_lost,
                })

                float_backlog_cost += float_margin * float_backlog
                float_lost_cost += float_margin * float_lost
                float_floor_slack_cost += float_margin * float_floor_slack
                float_holding_cost += float_holding_per_week * float_inventory

                for str_machine in dict_scenario['machines_of_product'][str_product]:
                    tuple_production = (str_product, str_machine, timestamp_week)
                    float_quantity = resolve(dict_production[tuple_production])
                    float_active = resolve(dict_setup[tuple_production])
                    if float_quantity > 1e-6:
                        float_rate = dict_scenario['productivity'][str_product][str_machine]
                        list_production_rows.append({
                            'week': str_week, 'machine': str_machine, 'product': str_product,
                            'kg': float_quantity,
                            'hours': float_quantity / float_rate,
                            'setup_hours': dict_scenario['average_setup'][str_product] * float_active,
                        })
                    if float_active > 0.5:
                        float_hours = dict_scenario['average_setup'][str_product]
                        float_setup_hours += float_hours
                        float_setup_cost += dict_scenario['setup_hourly_cost'][str_machine] * float_hours

        float_total_orders = 0.0
        float_total_forecast = 0.0
        float_total_backlog = 0.0
        float_total_lost = 0.0
        for dict_row in list_demand_rows:
            float_total_orders += dict_row['orders']
            float_total_forecast += dict_row['forecast']
            float_total_lost += dict_row['lost']
        for str_product in list_products:
            float_total_backlog += resolve(dict_backlog[(str_product, list_weeks[-1])])

        if float_total_orders > 0:
            float_order_service = (1.0 - float_total_backlog / float_total_orders) * 100.0
        else:
            float_order_service = 100.0
        if float_total_forecast > 0:
            float_forecast_service = (1.0 - float_total_lost / float_total_forecast) * 100.0
        else:
            float_forecast_service = 100.0

        float_average_inventory = 0.0
        for dict_row in list_inventory_rows:
            float_average_inventory += dict_row['inventory']
        float_average_inventory = float_average_inventory / len(list_weeks)

        float_delivered = float_total_orders - float_total_backlog + float_total_forecast - float_total_lost
        if float_average_inventory > 0:
            float_turnover = float_delivered / float_average_inventory
        else:
            float_turnover = 0.0

        list_week_labels = []
        for timestamp_week in list_weeks:
            list_week_labels.append(timestamp_week.strftime('%Y-%m-%d'))

        dict_result = {
            'status': str_status,
            'stage_objectives': list_stage_values,
            'stage_reports': list_stage_reports,
            'weeks': list_week_labels,
            'production': list_production_rows,
            'inventory': list_inventory_rows,
            'demand': list_demand_rows,
            'targets': dict_targets,
            'stock_minimum': dict_scenario['stock_minimum'],
            'warehouse_capacity': dict_scenario['warehouse_capacity'],
            'kpis': {
                'total_cost': (float_backlog_cost + float_lost_cost + float_floor_slack_cost
                               + float_setup_cost + float_holding_cost),
                'backlog_cost': float_backlog_cost,
                'lost_sales_cost': float_lost_cost,
                'floor_slack_cost': float_floor_slack_cost,
                'setup_cost': float_setup_cost,
                'holding_cost': float_holding_cost,
                'order_service_level': float_order_service,
                'forecast_service_level': float_forecast_service,
                'avg_inventory': float_average_inventory,
                'inventory_turnover': float_turnover,
                'setup_hours': float_setup_hours,
                'solve_seconds': float_solve_seconds,
                'hit_time_limit': bool_hit_time_limit,
            },
        }

    return dict_result
