import time

import pulp
import pandas as pd


def clean_name(str_raw):
    return str(str_raw).replace(' ', '_').replace(':', '_').replace('-', '_').replace('/', '_')


def build_weekly_scenario(dict_instance, dict_settings):
    timestamp_start = pd.Timestamp(dict_settings['start_week'])
    int_weeks_in_plan = int(dict_settings['weeks_in_plan'])
    int_coverage_weeks = int(dict_settings['coverage_weeks'])

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

    dict_coverage_target = {}
    for str_product in dict_instance['products']:
        dict_coverage_target[str_product] = {}
        for int_index in range(len(list_weeks)):
            float_target = 0.0
            for int_ahead in range(1, int_coverage_weeks + 1):
                int_future = list_all_weeks.index(list_weeks[int_index]) + int_ahead
                if int_future < len(list_all_weeks):
                    timestamp_future = list_all_weeks[int_future]
                    float_target += dict_orders[str_product][timestamp_future]
                    float_target += dict_forecast[str_product][timestamp_future]
                else:
                    timestamp_last = list_all_weeks[-1]
                    float_target += dict_orders[str_product][timestamp_last]
                    float_target += dict_forecast[str_product][timestamp_last]
            dict_coverage_target[str_product][list_weeks[int_index]] = float_target

    float_hours_per_week = (float(dict_settings['working_days_per_week'])
                            * float(dict_settings['shifts_per_day'])
                            * float(dict_settings['hours_per_shift']))
    dict_capacity = {}
    for str_machine in dict_settings['active_machines']:
        dict_capacity[str_machine] = {}
        for timestamp_week in list_weeks:
            float_availability = dict_instance['availability'][str_machine][timestamp_week]
            dict_capacity[str_machine][timestamp_week] = float_hours_per_week * float_availability

    dict_average_setup = {}
    for str_product in dict_instance['products']:
        float_total = 0.0
        int_count = 0
        for str_other in dict_instance['products']:
            if str_other != str_product:
                float_total += dict_instance['form_setup'][(str_other, str_product)]
                int_count += 1
        if int_count > 0:
            dict_average_setup[str_product] = float_total / int_count
        else:
            dict_average_setup[str_product] = 0.0

    dict_setup_hourly_cost = {}
    for str_machine in dict_settings['active_machines']:
        if str_machine in dict_settings['setup_hourly_cost_by_machine']:
            dict_setup_hourly_cost[str_machine] = float(
                dict_settings['setup_hourly_cost_by_machine'][str_machine])
        else:
            dict_setup_hourly_cost[str_machine] = float(dict_settings['setup_hourly_cost_default'])

    dict_machines_of_product = {}
    for str_product in dict_instance['products']:
        dict_machines_of_product[str_product] = []
        for str_machine in dict_settings['active_machines']:
            if str_machine in dict_instance['productivity'][str_product]:
                dict_machines_of_product[str_product].append(str_machine)

    return {
        'weeks': list_weeks,
        'products': dict_instance['products'],
        'machines': list(dict_settings['active_machines']),
        'orders': dict_orders,
        'forecast': dict_forecast,
        'coverage_target': dict_coverage_target,
        'capacity': dict_capacity,
        'productivity': dict_instance['productivity'],
        'machines_of_product': dict_machines_of_product,
        'average_setup': dict_average_setup,
        'setup_hourly_cost': dict_setup_hourly_cost,
        'initial_inventory': dict_instance['initial_inventory'],
        'min_lot': dict_instance['min_lot'],
        'unit_cost': dict_instance['unit_cost'],
        'margin': dict_instance['margin'],
    }


def solve_weekly_model(dict_scenario, dict_settings):
    list_weeks = dict_scenario['weeks']
    list_products = dict_scenario['products']

    float_holding_rate = float(dict_settings['annual_holding_rate'])
    float_backlog_multiplier = float(dict_settings['order_backlog_multiplier'])
    float_coverage_weight = float(dict_settings['coverage_weight'])

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
    dict_coverage_slack = {}
    for str_product in list_products:
        for timestamp_week in list_weeks:
            tuple_key = (str_product, timestamp_week)
            str_label = f'{clean_name(str_product)}_{clean_name(timestamp_week.date())}'
            dict_inventory[tuple_key] = pulp.LpVariable(f'I_{str_label}', lowBound=0)
            dict_backlog[tuple_key] = pulp.LpVariable(f'a_{str_label}', lowBound=0)
            dict_lost[tuple_key] = pulp.LpVariable(f'l_{str_label}', lowBound=0)
            dict_coverage_slack[tuple_key] = pulp.LpVariable(f'g_{str_label}', lowBound=0)

    list_objective_terms = []
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        float_unit_cost = dict_scenario['unit_cost'][str_product]
        for int_index in range(len(list_weeks)):
            timestamp_week = list_weeks[int_index]
            tuple_key = (str_product, timestamp_week)
            list_objective_terms.append(float_backlog_multiplier * float_margin * dict_backlog[tuple_key])
            list_objective_terms.append(float_margin * dict_lost[tuple_key])
            list_objective_terms.append(float_coverage_weight * float_margin * dict_coverage_slack[tuple_key])
            if int_index == 0:
                float_previous = dict_scenario['initial_inventory'][str_product]
                list_objective_terms.append(
                    (float_holding_rate / 52.0) * float_unit_cost * 0.5 * float_previous)
                list_objective_terms.append(
                    (float_holding_rate / 52.0) * float_unit_cost * 0.5 * dict_inventory[tuple_key])
            else:
                tuple_previous = (str_product, list_weeks[int_index - 1])
                list_objective_terms.append(
                    (float_holding_rate / 52.0) * float_unit_cost * 0.5 * dict_inventory[tuple_previous])
                list_objective_terms.append(
                    (float_holding_rate / 52.0) * float_unit_cost * 0.5 * dict_inventory[tuple_key])

    for str_product in list_products:
        float_setup_time = dict_scenario['average_setup'][str_product]
        for str_machine in dict_scenario['machines_of_product'][str_product]:
            float_hourly_cost = dict_scenario['setup_hourly_cost'][str_machine]
            for timestamp_week in list_weeks:
                list_objective_terms.append(
                    float_hourly_cost * float_setup_time * dict_setup[(str_product, str_machine, timestamp_week)])

    problem += pulp.lpSum(list_objective_terms)

    for str_product in list_products:
        for int_index in range(len(list_weeks)):
            timestamp_week = list_weeks[int_index]
            tuple_key = (str_product, timestamp_week)

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

            float_orders = dict_scenario['orders'][str_product][timestamp_week]
            float_forecast = dict_scenario['forecast'][str_product][timestamp_week]

            problem += (expression_previous_inventory + pulp.lpSum(list_production_terms)
                        == dict_inventory[tuple_key]
                        + (float_orders + expression_previous_backlog - dict_backlog[tuple_key])
                        + (float_forecast - dict_lost[tuple_key]))

            problem += dict_backlog[tuple_key] <= float_orders + expression_previous_backlog
            problem += dict_lost[tuple_key] <= float_forecast
            problem += (dict_inventory[tuple_key] + dict_coverage_slack[tuple_key]
                        >= dict_scenario['coverage_target'][str_product][timestamp_week])

    for str_machine in dict_scenario['machines']:
        for timestamp_week in list_weeks:
            list_capacity_terms = []
            for str_product in list_products:
                if str_machine in dict_scenario['machines_of_product'][str_product]:
                    tuple_key = (str_product, str_machine, timestamp_week)
                    float_rate = dict_scenario['productivity'][str_product][str_machine]
                    list_capacity_terms.append(dict_production[tuple_key] / float_rate)
                    list_capacity_terms.append(
                        dict_scenario['average_setup'][str_product] * dict_setup[tuple_key])
            problem += pulp.lpSum(list_capacity_terms) <= dict_scenario['capacity'][str_machine][timestamp_week]

    for str_product in list_products:
        float_min_lot = dict_scenario['min_lot'][str_product]
        for int_index in range(len(list_weeks)):
            timestamp_week = list_weeks[int_index]
            float_remaining_demand = dict_scenario['initial_inventory'][str_product]
            for int_future in range(int_index, len(list_weeks)):
                timestamp_future = list_weeks[int_future]
                float_remaining_demand += dict_scenario['orders'][str_product][timestamp_future]
                float_remaining_demand += dict_scenario['forecast'][str_product][timestamp_future]
            float_remaining_demand += dict_scenario['coverage_target'][str_product][list_weeks[-1]]
            for str_machine in dict_scenario['machines_of_product'][str_product]:
                tuple_key = (str_product, str_machine, timestamp_week)
                float_rate = dict_scenario['productivity'][str_product][str_machine]
                float_capacity_bound = float_rate * dict_scenario['capacity'][str_machine][timestamp_week]
                float_big_m = float_capacity_bound
                if float_remaining_demand < float_big_m:
                    float_big_m = float_remaining_demand
                problem += dict_production[tuple_key] <= float_big_m * dict_setup[tuple_key]
                problem += dict_production[tuple_key] >= float_min_lot * dict_setup[tuple_key]

    str_solver_name = str(dict_settings['weekly_solver_name']).upper()
    int_time_limit = int(dict_settings['weekly_time_limit'])
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
    float_coverage_cost = 0.0

    for str_product in list_products:
        dict_targets[str_product] = {}
        float_margin = dict_scenario['margin'][str_product]
        float_unit_cost = dict_scenario['unit_cost'][str_product]
        for int_index in range(len(list_weeks)):
            timestamp_week = list_weeks[int_index]
            tuple_key = (str_product, timestamp_week)
            str_week = timestamp_week.strftime('%Y-%m-%d')

            float_inventory = resolve(dict_inventory[tuple_key])
            float_backlog = resolve(dict_backlog[tuple_key])
            float_lost = resolve(dict_lost[tuple_key])
            float_slack = resolve(dict_coverage_slack[tuple_key])
            dict_targets[str_product][str_week] = float_inventory

            if int_index == 0:
                float_previous_inventory = dict_scenario['initial_inventory'][str_product]
                float_previous_backlog = 0.0
            else:
                tuple_previous = (str_product, list_weeks[int_index - 1])
                float_previous_inventory = resolve(dict_inventory[tuple_previous])
                float_previous_backlog = resolve(dict_backlog[tuple_previous])

            float_orders = dict_scenario['orders'][str_product][timestamp_week]
            float_forecast = dict_scenario['forecast'][str_product][timestamp_week]

            list_inventory_rows.append({
                'week': str_week, 'product': str_product,
                'inventory': float_inventory,
                'target': dict_scenario['coverage_target'][str_product][timestamp_week],
                'slack': float_slack,
            })
            list_demand_rows.append({
                'week': str_week, 'product': str_product,
                'orders': float_orders, 'forecast': float_forecast,
                'delivered_orders': float_orders + float_previous_backlog - float_backlog,
                'backlog': float_backlog,
                'delivered_forecast': float_forecast - float_lost,
                'lost': float_lost,
            })

            float_backlog_cost += float_backlog_multiplier * float_margin * float_backlog
            float_lost_cost += float_margin * float_lost
            float_coverage_cost += float_coverage_weight * float_margin * float_slack
            float_holding_cost += ((float_holding_rate / 52.0) * float_unit_cost
                                   * 0.5 * (float_previous_inventory + float_inventory))

            for str_machine in dict_scenario['machines_of_product'][str_product]:
                tuple_production = (str_product, str_machine, timestamp_week)
                float_quantity = resolve(dict_production[tuple_production])
                float_active = resolve(dict_setup[tuple_production])
                if float_quantity > 1e-6:
                    float_rate = dict_scenario['productivity'][str_product][str_machine]
                    float_setup_time = dict_scenario['average_setup'][str_product] * float_active
                    list_production_rows.append({
                        'week': str_week, 'machine': str_machine, 'product': str_product,
                        'kg': float_quantity,
                        'hours': float_quantity / float_rate,
                        'setup_hours': float_setup_time,
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

    return {
        'status': str_status,
        'weeks': list_week_labels,
        'production': list_production_rows,
        'inventory': list_inventory_rows,
        'demand': list_demand_rows,
        'targets': dict_targets,
        'kpis': {
            'total_cost': (float_backlog_cost + float_lost_cost + float_coverage_cost
                           + float_setup_cost + float_holding_cost),
            'solver_objective': pulp.value(problem.objective),
            'backlog_cost': float_backlog_cost,
            'lost_sales_cost': float_lost_cost,
            'coverage_cost': float_coverage_cost,
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
