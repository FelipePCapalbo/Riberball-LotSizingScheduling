import os
import resource
import time

import pandas as pd
import pulp

from optimization.daily_model import clean_name
from optimization.solver import compute_gap, solve_lexicographic
from optimization.weekly_model import complete_setup_matrix


def read_value(variable):
    float_value = variable.varValue
    if float_value is None:
        float_value = 0.0
    return float_value


def build_monolithic_scenario(dict_instance, dict_settings, int_weeks):
    timestamp_start = pd.Timestamp(dict_settings['start_week'])
    int_weeks_in_plan = int(dict_settings['weeks_in_plan'])
    int_shifts_per_day = int(dict_settings['shifts_per_day'])
    int_working_days = int(dict_settings['working_days_per_week'])
    float_hours_per_shift = float(dict_settings['hours_per_shift'])

    list_plan_weeks = []
    for timestamp_week in dict_instance['weeks']:
        if timestamp_week >= timestamp_start and len(list_plan_weeks) < int_weeks_in_plan:
            list_plan_weeks.append(timestamp_week)
    list_scenario_weeks = []
    for timestamp_week in list_plan_weeks:
        if len(list_scenario_weeks) < int_weeks:
            list_scenario_weeks.append(timestamp_week)

    list_shifts = []
    list_week_labels = []
    dict_last_shift_of_week = {}
    for int_week in range(len(list_scenario_weeks)):
        timestamp_week = list_scenario_weeks[int_week]
        str_week = timestamp_week.strftime('%Y-%m-%d')
        list_week_labels.append(str_week)
        for int_day in range(int_working_days):
            for int_shift in range(int_shifts_per_day):
                list_shifts.append({
                    'index': len(list_shifts),
                    'date': timestamp_week + pd.Timedelta(days=int_day),
                    'shift_number': int_shift + 1,
                    'day_index': len(list_shifts) // int_shifts_per_day,
                    'week': str_week,
                    'week_index': int_week,
                    'week_start': timestamp_week,
                })
                dict_last_shift_of_week[str_week] = list_shifts[-1]['index']

    dict_skus_of_product = {}
    dict_product_of_sku = {}
    dict_color_of_sku = {}
    list_colors = []
    for str_product in dict_instance['products']:
        dict_skus_of_product[str_product] = []
        for str_color in dict_instance['colors_by_product'][str_product]:
            str_sku = f'{str_product}-{str_color}'
            dict_skus_of_product[str_product].append(str_sku)
            dict_product_of_sku[str_sku] = str_product
            dict_color_of_sku[str_sku] = str_color
            if str_color not in list_colors:
                list_colors.append(str_color)
    for tuple_side in dict_instance['initial_color']:
        if dict_instance['initial_color'][tuple_side] not in list_colors:
            list_colors.append(dict_instance['initial_color'][tuple_side])
    dict_color_setup = complete_setup_matrix(dict_instance['color_setup'], list_colors)
    dict_form_setup = complete_setup_matrix(dict_instance['form_setup'], dict_instance['products'])

    dict_orders = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            for dict_shift in list_shifts:
                dict_orders[(str_sku, dict_shift['index'])] = 0.0
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
                if tuple_key in dict_orders:
                    dict_orders[tuple_key] += dict_item['quantity']

    dict_product_orders = {}
    for str_product in dict_instance['products']:
        dict_product_orders[str_product] = {}
        for timestamp_week in dict_instance['weeks']:
            dict_product_orders[str_product][timestamp_week] = 0.0
    for dict_order in dict_instance['orders']:
        timestamp_due_week = None
        for timestamp_week in dict_instance['weeks']:
            if timestamp_week <= dict_order['due_date']:
                timestamp_due_week = timestamp_week
        if timestamp_due_week is None:
            timestamp_due_week = dict_instance['weeks'][0]
        for dict_item in dict_order['items']:
            dict_product_orders[dict_item['product']][timestamp_due_week] += dict_item['quantity']

    dict_forecast = {}
    dict_color_share = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            str_color = dict_color_of_sku[str_sku]
            if str_color in dict_instance['color_mix'][str_product]:
                dict_color_share[str_sku] = dict_instance['color_mix'][str_product][str_color]
            else:
                dict_color_share[str_sku] = 0.0
        for timestamp_week in list_scenario_weeks:
            float_net = (dict_instance['demand'][str_product][timestamp_week]
                         - dict_product_orders[str_product][timestamp_week])
            if float_net < 0.0:
                float_net = 0.0
            for str_sku in dict_skus_of_product[str_product]:
                dict_forecast[(str_sku, timestamp_week.strftime('%Y-%m-%d'))] = dict_color_share[str_sku] * float_net

    dict_stock_minimum = {}
    for str_product in dict_instance['products']:
        float_mts_share = 0.0
        for str_color in dict_instance['colors_by_product'][str_product]:
            if dict_instance['sku_is_mts'][f'{str_product}-{str_color}']:
                if str_color in dict_instance['color_mix'][str_product]:
                    float_mts_share += dict_instance['color_mix'][str_product][str_color]
        float_average_demand = 0.0
        for timestamp_week in list_plan_weeks:
            float_average_demand += dict_instance['demand'][str_product][timestamp_week]
        float_average_demand = float_average_demand / len(list_plan_weeks)
        dict_stock_minimum[str_product] = (float_average_demand * float_mts_share
                                           * (1.0 + dict_instance['mape'][str_product] / 100.0))

    dict_machines_of_product = {}
    for str_product in dict_instance['products']:
        dict_machines_of_product[str_product] = []
        for str_machine in dict_instance['machines']:
            if str_machine in dict_instance['productivity'][str_product]:
                dict_machines_of_product[str_product].append(str_machine)

    dict_products_of_machine = {}
    list_machines = []
    dict_positions = {}
    for str_machine in dict_instance['machines']:
        dict_products_of_machine[str_machine] = []
        int_positions = 0
        for str_product in dict_instance['products']:
            if str_machine in dict_machines_of_product[str_product]:
                dict_products_of_machine[str_machine].append(str_product)
                if len(dict_skus_of_product[str_product]) > int_positions:
                    int_positions = len(dict_skus_of_product[str_product])
        dict_positions[str_machine] = int_positions
        if len(dict_products_of_machine[str_machine]) > 0:
            list_machines.append(str_machine)

    dict_shift_capacity = {}
    for str_machine in dict_instance['machines']:
        for dict_shift in list_shifts:
            float_availability = dict_instance['availability'][str_machine][dict_shift['week_start']]
            dict_shift_capacity[(str_machine, dict_shift['index'])] = float_hours_per_shift * float_availability

    dict_initial_stock = {}
    dict_initial_backlog = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            dict_initial_backlog[str_sku] = 0.0
            if str_sku in dict_instance['color_initial_stock']:
                dict_initial_stock[str_sku] = dict_instance['color_initial_stock'][str_sku]
            else:
                dict_initial_stock[str_sku] = 0.0

    dict_initial_form = {}
    dict_initial_pending = {}
    dict_initial_color = {}
    for str_machine in list_machines:
        dict_initial_pending[str_machine] = 0.0
        if str_machine in dict_instance['initial_form']:
            dict_initial_form[str_machine] = dict_instance['initial_form'][str_machine]
        else:
            dict_initial_form[str_machine] = '0'
        for int_side in range(1, dict_instance['color_sides'][str_machine] + 1):
            if dict_initial_form[str_machine] == '0':
                dict_initial_color[(str_machine, int_side)] = None
            elif (str_machine, int_side) in dict_instance['initial_color']:
                dict_initial_color[(str_machine, int_side)] = dict_instance['initial_color'][(str_machine, int_side)]
            else:
                dict_initial_color[(str_machine, int_side)] = '0'

    float_warehouse_capacity = dict_settings['warehouse_capacity_kg']
    if float_warehouse_capacity is not None:
        float_initial_total = 0.0
        for str_sku in dict_initial_stock:
            float_initial_total += dict_initial_stock[str_sku]
        float_warehouse_capacity = float(float_warehouse_capacity)
        if float_initial_total > float_warehouse_capacity:
            float_warehouse_capacity = float_initial_total

    dict_holding_per_shift = {}
    for str_product in dict_instance['products']:
        dict_holding_per_shift[str_product] = (float(dict_settings['annual_holding_rate'])
                                               * dict_instance['unit_cost'][str_product]
                                               / (52.0 * int_working_days * int_shifts_per_day))

    float_longest_form_change = 0.0
    for tuple_pair in dict_form_setup:
        if dict_form_setup[tuple_pair] > float_longest_form_change:
            float_longest_form_change = dict_form_setup[tuple_pair]
    float_longest_color_change = 0.0
    for tuple_pair in dict_color_setup:
        if dict_color_setup[tuple_pair] > float_longest_color_change:
            float_longest_color_change = dict_color_setup[tuple_pair]

    return {
        'weeks': list_week_labels,
        'shifts': list_shifts,
        'last_shift_of_week': dict_last_shift_of_week,
        'shift_offset': 0,
        'machines': list_machines,
        'products': dict_instance['products'],
        'skus_of_product': dict_skus_of_product,
        'product_of_sku': dict_product_of_sku,
        'color_of_sku': dict_color_of_sku,
        'color_share': dict_color_share,
        'machines_of_product': dict_machines_of_product,
        'products_of_machine': dict_products_of_machine,
        'positions': dict_positions,
        'color_sides': dict_instance['color_sides'],
        'shift_capacity': dict_shift_capacity,
        'productivity': dict_instance['productivity'],
        'form_setup': dict_form_setup,
        'color_setup': dict_color_setup,
        'longest_form_change': float_longest_form_change,
        'longest_color_change': float_longest_color_change,
        'orders': dict_orders,
        'forecast': dict_forecast,
        'stock_minimum': dict_stock_minimum,
        'min_lot': dict_instance['min_lot'],
        'unit_cost': dict_instance['unit_cost'],
        'margin': dict_instance['margin'],
        'holding_per_shift': dict_holding_per_shift,
        'setup_hourly_cost': dict_instance['setup_hourly_cost'],
        'warehouse_capacity': float_warehouse_capacity,
        'initial_stock': dict_initial_stock,
        'initial_backlog': dict_initial_backlog,
        'initial_form': dict_initial_form,
        'initial_pending': dict_initial_pending,
        'initial_color': dict_initial_color,
    }


def build_monolithic_model(dict_scenario, bool_preprocessing):
    list_shifts = dict_scenario['shifts']
    int_shift_count = len(list_shifts)
    list_machines = dict_scenario['machines']
    list_products = dict_scenario['products']
    list_weeks = dict_scenario['weeks']
    dict_color_setup = dict_scenario['color_setup']
    float_longest_form_change = dict_scenario['longest_form_change']

    problem = pulp.LpProblem('MonolithicPlanning', pulp.LpMinimize)

    dict_sku_active = {}
    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            dict_sku_active[str_sku] = True
    dict_open_orders = {}
    dict_forecast_ahead = {}
    dict_min_change = {}
    bool_triangle = None
    if bool_preprocessing:
        list_matrix_colors = []
        for tuple_pair in dict_color_setup:
            if tuple_pair[1] not in list_matrix_colors:
                list_matrix_colors.append(tuple_pair[1])
        bool_triangle = True
        for tuple_pair in dict_color_setup:
            for str_middle in list_matrix_colors:
                if (tuple_pair[0], str_middle) in dict_color_setup and (str_middle, tuple_pair[1]) in dict_color_setup:
                    if (dict_color_setup[tuple_pair] > dict_color_setup[(tuple_pair[0], str_middle)]
                            + dict_color_setup[(str_middle, tuple_pair[1])] + 1e-9):
                        bool_triangle = False
        for str_product in list_products:
            float_min_change = None
            for str_from in dict_scenario['skus_of_product'][str_product]:
                for str_to in dict_scenario['skus_of_product'][str_product]:
                    if str_from != str_to:
                        float_change = dict_color_setup[(dict_scenario['color_of_sku'][str_from],
                                                         dict_scenario['color_of_sku'][str_to])]
                        if float_min_change is None or float_change < float_min_change:
                            float_min_change = float_change
            if float_min_change is None:
                float_min_change = 0.0
            dict_min_change[str_product] = float_min_change
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                float_open = dict_scenario['initial_backlog'][str_sku] - dict_scenario['initial_stock'][str_sku]
                for dict_shift in list_shifts:
                    float_open += dict_scenario['orders'][(str_sku, dict_shift['index'])]
                if float_open < 0.0:
                    float_open = 0.0
                dict_open_orders[str_sku] = float_open
                float_ahead = 0.0
                int_week = len(list_weeks) - 1
                while int_week >= 0:
                    float_ahead += dict_scenario['forecast'][(str_sku, list_weeks[int_week])]
                    dict_forecast_ahead[(str_sku, int_week)] = float_ahead
                    int_week -= 1
                if (bool_triangle and dict_open_orders[str_sku] + float_ahead <= 1e-9
                        and dict_scenario['initial_backlog'][str_sku] <= 1e-9
                        and dict_scenario['stock_minimum'][str_product] <= 1e-9):
                    float_total_orders = 0.0
                    for dict_shift in list_shifts:
                        float_total_orders += dict_scenario['orders'][(str_sku, dict_shift['index'])]
                    if float_total_orders <= 1e-9:
                        dict_sku_active[str_sku] = False

    dict_sku_positions = {}
    dict_upper = {}
    for str_machine in list_machines:
        int_positions = dict_scenario['positions'][str_machine]
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            float_capacity = dict_scenario['shift_capacity'][(str_machine, int_shift)]
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                float_rate = dict_scenario['productivity'][str_product][str_machine]
                float_min_lot = dict_scenario['min_lot'][str_product]
                int_fit = int_positions
                if bool_preprocessing:
                    int_fit = 0
                    bool_fits = True
                    while (bool_fits and int_fit < int_positions
                           and int_fit < len(dict_scenario['skus_of_product'][str_product])):
                        if ((int_fit + 1) * float_min_lot / float_rate + int_fit * dict_min_change[str_product]
                                <= float_capacity + 1e-9):
                            int_fit += 1
                        else:
                            bool_fits = False
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    tuple_cell = (str_sku, str_machine, int_shift)
                    if dict_sku_active[str_sku]:
                        dict_sku_positions[tuple_cell] = int_fit
                    else:
                        dict_sku_positions[tuple_cell] = 0
                    float_upper = float_rate * float_capacity
                    if bool_preprocessing:
                        float_need = (dict_open_orders[str_sku]
                                      + dict_forecast_ahead[(str_sku, dict_shift['week_index'])]
                                      + dict_scenario['stock_minimum'][str_product])
                        if float_need < float_upper:
                            float_upper = float_need
                        if float_upper < float_min_lot:
                            float_upper = float_min_lot
                    dict_upper[tuple_cell] = float_upper

    dict_form = {}
    dict_position = {}
    dict_quantity = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                dict_form[(str_product, str_machine, int_shift)] = pulp.LpVariable(
                    f'y_{clean_name(str_product)}_{str_machine}_{int_shift}', cat='Binary')
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        for int_position in range(1, dict_sku_positions[(str_sku, str_machine, int_shift)] + 1):
                            tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                            str_label = f'{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}_{int_position}'
                            dict_position[tuple_key] = pulp.LpVariable(f'nu_{str_label}', cat='Binary')
                            dict_quantity[tuple_key] = pulp.LpVariable(f'x_{str_label}', lowBound=0)

    dict_previous_forms = {}
    dict_form_change = {}
    dict_form_hours = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            list_previous_forms = []
            if int_shift > 0:
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    list_previous_forms.append(str_product)
            else:
                list_previous_forms.append(dict_scenario['initial_form'][str_machine])
            dict_previous_forms[(str_machine, int_shift)] = list_previous_forms
            for str_from in list_previous_forms:
                for str_to in dict_scenario['products_of_machine'][str_machine]:
                    tuple_key = (str_from, str_to, str_machine, int_shift)
                    str_label = f'{clean_name(str_from)}_{clean_name(str_to)}_{str_machine}_{int_shift}'
                    dict_form_change[tuple_key] = pulp.LpVariable(f'z_{str_label}', lowBound=0, upBound=1)
                    dict_form_hours[tuple_key] = dict_scenario['form_setup'][(str_from, str_to)]

    float_pending_bound = None
    if bool_preprocessing:
        float_pending_bound = float_longest_form_change
    dict_pending = {}
    dict_form_started = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            dict_pending[(str_machine, int_shift)] = pulp.LpVariable(f'w_{str_machine}_{int_shift}', lowBound=0,
                                                                     upBound=float_pending_bound)
            list_started_terms = []
            for str_from in dict_previous_forms[(str_machine, int_shift)]:
                for str_to in dict_scenario['products_of_machine'][str_machine]:
                    tuple_key = (str_from, str_to, str_machine, int_shift)
                    if dict_form_hours[tuple_key] > 0.0:
                        list_started_terms.append(dict_form_hours[tuple_key] * dict_form_change[tuple_key])
            dict_form_started[(str_machine, int_shift)] = pulp.lpSum(list_started_terms)

    dict_transition = {}
    dict_last_color = {}
    dict_entry = {}
    dict_initial_state = {}
    list_initial_state_sides = []
    for str_machine in list_machines:
        int_positions = dict_scenario['positions'][str_machine]
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            bool_initial_state = (dict_scenario['initial_form'][str_machine]
                                  in dict_scenario['products_of_machine'][str_machine]
                                  and dict_scenario['initial_color'][(str_machine, int_side)] is not None)
            if bool_initial_state:
                list_initial_state_sides.append((str_machine, int_side))
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                if bool_initial_state:
                    dict_initial_state[(str_machine, int_side, int_shift)] = pulp.LpVariable(
                        f'u_{str_machine}_{int_side}_{int_shift}', lowBound=0, upBound=1)
                if int_shift > 0 or bool_initial_state:
                    dict_entry[(str_machine, int_side, int_shift)] = pulp.LpVariable(
                        f'e_{str_machine}_{int_side}_{int_shift}', lowBound=0)
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        if int_shift < int_shift_count - 1 and dict_sku_active[str_sku]:
                            dict_last_color[(str_sku, str_machine, int_side, int_shift)] = pulp.LpVariable(
                                f'q_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}', lowBound=0,
                                upBound=1)
                        for int_position in range(2, int_positions + 1):
                            for str_from in dict_scenario['skus_of_product'][str_product]:
                                if (str_from != str_sku
                                        and (str_from, str_machine, int_side, int_shift, int_position - 1)
                                        in dict_position
                                        and (str_sku, str_machine, int_side, int_shift, int_position) in dict_position):
                                    str_label = (f'{clean_name(str_sku)}_{clean_name(dict_scenario["color_of_sku"][str_from])}'
                                                 f'_{str_machine}_{int_side}_{int_shift}_{int_position}')
                                    dict_transition[(str_from, str_sku, str_machine, int_side, int_shift,
                                                     int_position)] = pulp.LpVariable(f'tr_{str_label}', lowBound=0)

    dict_inventory = {}
    dict_backlog = {}
    dict_lost = {}
    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                str_label = f'{clean_name(str_sku)}_{int_shift}'
                dict_inventory[(str_sku, int_shift)] = pulp.LpVariable(f'I_{str_label}', lowBound=0)
                dict_backlog[(str_sku, int_shift)] = pulp.LpVariable(f'b_{str_label}', lowBound=0)
            for str_week in list_weeks:
                dict_lost[(str_sku, str_week)] = pulp.LpVariable(f'l_{clean_name(str_sku)}_{clean_name(str_week)}',
                                                                 lowBound=0)
    dict_floor_slack = {}
    for str_product in list_products:
        for str_week in list_weeks:
            dict_floor_slack[(str_product, str_week)] = pulp.LpVariable(
                f'g_{clean_name(str_product)}_{clean_name(str_week)}', lowBound=0)

    list_backlog_terms = []
    list_lost_terms = []
    list_floor_terms = []
    list_cost_terms = []
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        for str_week in list_weeks:
            list_floor_terms.append(float_margin * dict_floor_slack[(str_product, str_week)])
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for str_week in list_weeks:
                list_lost_terms.append(float_margin * dict_lost[(str_sku, str_week)])
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                list_backlog_terms.append(float_margin * dict_backlog[(str_sku, int_shift)])
                list_cost_terms.append(dict_scenario['holding_per_shift'][str_product]
                                       * dict_inventory[(str_sku, int_shift)])
    for tuple_key in dict_form_change:
        if dict_form_hours[tuple_key] > 0.0:
            list_cost_terms.append(dict_scenario['setup_hourly_cost'][tuple_key[2]] * dict_form_hours[tuple_key]
                                   * dict_form_change[tuple_key])
    for tuple_key in dict_transition:
        float_hours = dict_color_setup[(dict_scenario['color_of_sku'][tuple_key[0]],
                                        dict_scenario['color_of_sku'][tuple_key[1]])]
        if float_hours > 0.0:
            list_cost_terms.append(dict_scenario['setup_hourly_cost'][tuple_key[2]] * float_hours
                                   * dict_transition[tuple_key])
    for tuple_key in dict_entry:
        list_cost_terms.append(dict_scenario['setup_hourly_cost'][tuple_key[0]] * dict_entry[tuple_key])

    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                list_production_terms = []
                for str_machine in dict_scenario['machines_of_product'][str_product]:
                    if str_machine in list_machines:
                        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                            for int_position in range(1, dict_scenario['positions'][str_machine] + 1):
                                tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                                if tuple_key in dict_quantity:
                                    list_production_terms.append(dict_quantity[tuple_key])
                if int_shift == 0:
                    expression_previous_stock = dict_scenario['initial_stock'][str_sku]
                    expression_previous_backlog = dict_scenario['initial_backlog'][str_sku]
                else:
                    expression_previous_stock = dict_inventory[(str_sku, int_shift - 1)]
                    expression_previous_backlog = dict_backlog[(str_sku, int_shift - 1)]
                expression_lost = 0.0
                float_forecast = 0.0
                if dict_scenario['last_shift_of_week'][dict_shift['week']] == int_shift:
                    expression_lost = dict_lost[(str_sku, dict_shift['week'])]
                    float_forecast = dict_scenario['forecast'][(str_sku, dict_shift['week'])]
                problem += (expression_previous_stock + pulp.lpSum(list_production_terms)
                            + dict_backlog[(str_sku, int_shift)] + expression_lost
                            == dict_inventory[(str_sku, int_shift)] + dict_scenario['orders'][(str_sku, int_shift)]
                            + float_forecast + expression_previous_backlog,
                            f'balanco_turno_{clean_name(str_sku)}_{int_shift}')

    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for str_week in list_weeks:
                problem += (dict_lost[(str_sku, str_week)] <= dict_scenario['forecast'][(str_sku, str_week)],
                            f'folga_limite_{clean_name(str_sku)}_{clean_name(str_week)}')

    for str_product in list_products:
        for str_week in list_weeks:
            int_week_last_shift = dict_scenario['last_shift_of_week'][str_week]
            list_week_stock_terms = []
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                list_week_stock_terms.append(dict_inventory[(str_sku, int_week_last_shift)])
            problem += (pulp.lpSum(list_week_stock_terms) + dict_floor_slack[(str_product, str_week)]
                        >= dict_scenario['stock_minimum'][str_product],
                        f'piso_estoque_{clean_name(str_product)}_{clean_name(str_week)}')

    if dict_scenario['warehouse_capacity'] is not None:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            list_stock_terms = []
            for str_product in list_products:
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    list_stock_terms.append(dict_inventory[(str_sku, int_shift)])
            problem += (pulp.lpSum(list_stock_terms) <= dict_scenario['warehouse_capacity'],
                        f'capacidade_armazem_turno_{int_shift}')

    for str_machine in list_machines:
        int_positions = dict_scenario['positions'][str_machine]
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                list_capacity_terms = []
                list_first_terms = []
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    float_rate = dict_scenario['productivity'][str_product][str_machine]
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        for int_position in range(1, int_positions + 1):
                            tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                            if tuple_key in dict_quantity:
                                list_capacity_terms.append(dict_quantity[tuple_key] / float_rate)
                                if int_position == 1:
                                    list_first_terms.append(dict_position[tuple_key])
                            for str_from in dict_scenario['skus_of_product'][str_product]:
                                tuple_transition = (str_from, str_sku, str_machine, int_side, int_shift, int_position)
                                if tuple_transition in dict_transition:
                                    float_hours = dict_color_setup[(dict_scenario['color_of_sku'][str_from],
                                                                    dict_scenario['color_of_sku'][str_sku])]
                                    if float_hours > 0.0:
                                        list_capacity_terms.append(float_hours * dict_transition[tuple_transition])
                if (str_machine, int_side, int_shift) in dict_entry:
                    list_capacity_terms.append(dict_entry[(str_machine, int_side, int_shift)])
                if int_shift > 0:
                    list_capacity_terms.append(dict_pending[(str_machine, int_shift - 1)])
                else:
                    list_capacity_terms.append(dict_scenario['initial_pending'][str_machine])
                list_capacity_terms.append(-1.0 * dict_pending[(str_machine, int_shift)])
                list_capacity_terms.append(dict_form_started[(str_machine, int_shift)])
                problem += (pulp.lpSum(list_capacity_terms)
                            <= dict_scenario['shift_capacity'][(str_machine, int_shift)],
                            f'capacidade_turno_{str_machine}_{int_side}_{int_shift}')
                problem += (dict_pending[(str_machine, int_shift)]
                            <= float_longest_form_change * (1 - pulp.lpSum(list_first_terms)),
                            f'troca_concluida_{str_machine}_{int_side}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            if int_shift > 0:
                expression_previous_pending = dict_pending[(str_machine, int_shift - 1)]
            else:
                expression_previous_pending = dict_scenario['initial_pending'][str_machine]
            problem += (dict_pending[(str_machine, int_shift)]
                        <= expression_previous_pending + dict_form_started[(str_machine, int_shift)],
                        f'troca_pendente_{str_machine}_{int_shift}')

    for tuple_side in list_initial_state_sides:
        str_machine, int_side = tuple_side
        str_initial_form = dict_scenario['initial_form'][str_machine]
        str_initial_color = dict_scenario['initial_color'][tuple_side]
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            tuple_cell = (str_machine, int_side, int_shift)
            expression_kept = dict_form_change[(str_initial_form, str_initial_form, str_machine, int_shift)]
            if int_shift > 0:
                list_reset_terms = []
                for str_sku in dict_scenario['skus_of_product'][str_initial_form]:
                    tuple_key = (str_sku, str_machine, int_side, int_shift - 1, 1)
                    if tuple_key in dict_position:
                        list_reset_terms.append(dict_position[tuple_key])
                problem += (dict_initial_state[tuple_cell]
                            >= dict_initial_state[(str_machine, int_side, int_shift - 1)]
                            - pulp.lpSum(list_reset_terms) - 1 + expression_kept,
                            f'cor_inicial_estado_{str_machine}_{int_side}_{int_shift}')
            else:
                problem += (dict_initial_state[tuple_cell] >= expression_kept,
                            f'cor_inicial_estado_{str_machine}_{int_side}_{int_shift}')
            for str_sku in dict_scenario['skus_of_product'][str_initial_form]:
                tuple_key = (str_sku, str_machine, int_side, int_shift, 1)
                float_hours = dict_color_setup[(str_initial_color, dict_scenario['color_of_sku'][str_sku])]
                if tuple_key in dict_position and float_hours > 0.0:
                    problem += (dict_entry[tuple_cell]
                                >= float_hours * (dict_initial_state[tuple_cell] + dict_position[tuple_key] - 1),
                                f'cor_inicial_troca_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    for str_machine in list_machines:
        int_positions = dict_scenario['positions'][str_machine]
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    list_product_skus = dict_scenario['skus_of_product'][str_product]
                    if int_shift > 0:
                        expression_kept = dict_form_change[(str_product, str_product, str_machine, int_shift)]
                        for str_from in list_product_skus:
                            for str_to in list_product_skus:
                                tuple_key = (str_to, str_machine, int_side, int_shift, 1)
                                tuple_state = (str_from, str_machine, int_side, int_shift - 1)
                                float_hours = dict_color_setup[(dict_scenario['color_of_sku'][str_from],
                                                                dict_scenario['color_of_sku'][str_to])]
                                if (str_from != str_to and float_hours > 0.0 and tuple_key in dict_position
                                        and tuple_state in dict_last_color):
                                    problem += (dict_entry[(str_machine, int_side, int_shift)]
                                                >= float_hours * (dict_last_color[tuple_state]
                                                                  + dict_position[tuple_key] + expression_kept - 2),
                                                f'cor_entrada_{clean_name(str_from)}_{clean_name(str_to)}_'
                                                f'{str_machine}_{int_side}_{int_shift}')
                    for str_sku in list_product_skus:
                        tuple_state = (str_sku, str_machine, int_side, int_shift)
                        if tuple_state in dict_last_color:
                            list_last_terms = []
                            for int_position in range(1, int_positions + 1):
                                tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                                if tuple_key in dict_position:
                                    list_last_terms.append(dict_position[tuple_key])
                                for str_to in list_product_skus:
                                    tuple_transition = (str_sku, str_to, str_machine, int_side, int_shift,
                                                        int_position)
                                    if tuple_transition in dict_transition:
                                        list_last_terms.append(-1.0 * dict_transition[tuple_transition])
                            if len(list_last_terms) > 0:
                                problem += (dict_last_color[tuple_state] >= pulp.lpSum(list_last_terms),
                                            f'cor_final_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')
                            if int_shift > 0:
                                list_first_terms = []
                                for str_other in list_product_skus:
                                    tuple_key = (str_other, str_machine, int_side, int_shift, 1)
                                    if tuple_key in dict_position:
                                        list_first_terms.append(dict_position[tuple_key])
                                problem += (dict_last_color[tuple_state]
                                            >= dict_last_color[(str_sku, str_machine, int_side, int_shift - 1)]
                                            - pulp.lpSum(list_first_terms) - 1
                                            + dict_form_change[(str_product, str_product, str_machine, int_shift)],
                                            f'cor_transportada_{clean_name(str_sku)}_{str_machine}_{int_side}_'
                                            f'{int_shift}')
                    for int_position in range(1, int_positions + 1):
                        list_form_terms = []
                        for str_sku in list_product_skus:
                            tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                            if tuple_key in dict_position:
                                list_form_terms.append(dict_position[tuple_key])
                                if int_position >= 2:
                                    list_incoming_terms = []
                                    for str_from in list_product_skus:
                                        tuple_transition = (str_from, str_sku, str_machine, int_side, int_shift,
                                                            int_position)
                                        if tuple_transition in dict_transition:
                                            list_incoming_terms.append(dict_transition[tuple_transition])
                                    problem += (pulp.lpSum(list_incoming_terms) == dict_position[tuple_key],
                                                f'troca_cor_entrada_{clean_name(str_sku)}_{str_machine}_{int_side}_'
                                                f'{int_shift}_{int_position}')
                            if int_position >= 2:
                                list_outgoing_terms = []
                                for str_to in list_product_skus:
                                    tuple_transition = (str_sku, str_to, str_machine, int_side, int_shift,
                                                        int_position)
                                    if tuple_transition in dict_transition:
                                        list_outgoing_terms.append(dict_transition[tuple_transition])
                                if len(list_outgoing_terms) > 0:
                                    problem += (pulp.lpSum(list_outgoing_terms)
                                                <= dict_position[(str_sku, str_machine, int_side, int_shift,
                                                                  int_position - 1)],
                                                f'troca_cor_saida_{clean_name(str_sku)}_{str_machine}_{int_side}_'
                                                f'{int_shift}_{int_position}')
                        if len(list_form_terms) > 0:
                            problem += (pulp.lpSum(list_form_terms)
                                        <= dict_form[(str_product, str_machine, int_shift)],
                                        f'cor_da_forma_{clean_name(str_product)}_{str_machine}_{int_side}_'
                                        f'{int_shift}_{int_position}')

    int_minimum_once_terms = 1
    if bool_preprocessing:
        int_minimum_once_terms = 2
    for str_machine in list_machines:
        int_positions = dict_scenario['positions'][str_machine]
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    float_min_lot = dict_scenario['min_lot'][str_product]
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        list_once_terms = []
                        for int_position in range(1, int_positions + 1):
                            tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                            if tuple_key in dict_position:
                                list_once_terms.append(dict_position[tuple_key])
                                str_label = f'{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}_{int_position}'
                                problem += (float_min_lot * dict_position[tuple_key] <= dict_quantity[tuple_key],
                                            f'lote_minimo_inferior_{str_label}')
                                problem += (dict_quantity[tuple_key]
                                            <= dict_upper[(str_sku, str_machine, int_shift)] * dict_position[tuple_key],
                                            f'lote_minimo_superior_{str_label}')
                        if len(list_once_terms) >= int_minimum_once_terms:
                            problem += (pulp.lpSum(list_once_terms) <= 1,
                                        f'corrida_unica_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_from in dict_previous_forms[(str_machine, int_shift)]:
                list_exit_terms = []
                for str_to in dict_scenario['products_of_machine'][str_machine]:
                    list_exit_terms.append(dict_form_change[(str_from, str_to, str_machine, int_shift)])
                if int_shift > 0:
                    expression_previous_form = dict_form[(str_from, str_machine, int_shift - 1)]
                else:
                    expression_previous_form = 1.0
                problem += (pulp.lpSum(list_exit_terms) == expression_previous_form,
                            f'forma_saida_{clean_name(str_from)}_{str_machine}_{int_shift}')
            for str_to in dict_scenario['products_of_machine'][str_machine]:
                list_entry_terms = []
                for str_from in dict_previous_forms[(str_machine, int_shift)]:
                    list_entry_terms.append(dict_form_change[(str_from, str_to, str_machine, int_shift)])
                problem += (pulp.lpSum(list_entry_terms) == dict_form[(str_to, str_machine, int_shift)],
                            f'forma_entrada_{clean_name(str_to)}_{str_machine}_{int_shift}')

    dict_product_demand = {}
    list_product_ranking = []
    for int_index in range(len(list_products)):
        str_product = list_products[int_index]
        float_demand = 0.0
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for dict_shift in list_shifts:
                float_demand += dict_scenario['orders'][(str_sku, dict_shift['index'])]
            for str_week in list_weeks:
                float_demand += dict_scenario['forecast'][(str_sku, str_week)]
        dict_product_demand[str_product] = float_demand
        list_product_ranking.append((-float_demand, int_index, str_product))
    list_product_ranking.sort()

    list_machine_ranking = []
    for int_index in range(len(list_machines)):
        str_machine = list_machines[int_index]
        float_demand_hours = 0.0
        for str_product in dict_scenario['products_of_machine'][str_machine]:
            float_demand_hours += ((dict_product_demand[str_product] + dict_scenario['stock_minimum'][str_product])
                                   / dict_scenario['productivity'][str_product][str_machine])
        float_capacity = 0.0
        for dict_shift in list_shifts:
            float_capacity += (dict_scenario['shift_capacity'][(str_machine, dict_shift['index'])]
                               * dict_scenario['color_sides'][str_machine])
        float_load = 0.0
        if float_capacity > 0.0:
            float_load = float_demand_hours / float_capacity
        list_machine_ranking.append((-float_load, int_index, str_machine))
    list_machine_ranking.sort()

    dict_week_unit = {}
    for str_week in list_weeks:
        dict_week_unit[str_week] = []
    dict_machine_unit = {}
    for tuple_ranked in list_machine_ranking:
        dict_machine_unit[tuple_ranked[2]] = []
    dict_product_unit = {}
    for tuple_ranked in list_product_ranking:
        dict_product_unit[tuple_ranked[2]] = []
    for tuple_key in dict_form:
        str_product, str_machine, int_shift = tuple_key
        dict_week_unit[list_shifts[int_shift]['week']].append(dict_form[tuple_key].name)
        dict_machine_unit[str_machine].append(dict_form[tuple_key].name)
        dict_product_unit[str_product].append(dict_form[tuple_key].name)
    for tuple_key in dict_position:
        str_sku, str_machine, int_side, int_shift, int_position = tuple_key
        dict_week_unit[list_shifts[int_shift]['week']].append(dict_position[tuple_key].name)
        dict_machine_unit[str_machine].append(dict_position[tuple_key].name)
        dict_product_unit[dict_scenario['product_of_sku'][str_sku]].append(dict_position[tuple_key].name)
    dict_partitions = {'tempo': [], 'maquina': [], 'produto': []}
    for str_decomposition, dict_unit in [('tempo', dict_week_unit), ('maquina', dict_machine_unit),
                                         ('produto', dict_product_unit)]:
        for value_key in dict_unit:
            if len(dict_unit[value_key]) > 0:
                dict_partitions[str_decomposition].append(dict_unit[value_key])

    float_total_volume = 0.0
    for tuple_ranked in list_product_ranking:
        float_total_volume += -tuple_ranked[0]
    dict_abc_class = {}
    float_cumulative = 0.0
    for tuple_ranked in list_product_ranking:
        if float_cumulative < 0.8 * float_total_volume:
            dict_abc_class[tuple_ranked[2]] = 'A'
        elif float_cumulative < 0.95 * float_total_volume:
            dict_abc_class[tuple_ranked[2]] = 'B'
        else:
            dict_abc_class[tuple_ranked[2]] = 'C'
        float_cumulative += -tuple_ranked[0]
    list_backlog_segments = [[], [], []]
    dict_lost_segments = {'A': [], 'B': [], 'C': []}
    dict_floor_segments = {'A': [], 'B': [], 'C': []}
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        str_class = dict_abc_class[str_product]
        for str_week in list_weeks:
            if dict_scenario['stock_minimum'][str_product] > 0.0:
                dict_floor_segments[str_class].append(float_margin * dict_floor_slack[(str_product, str_week)])
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for str_week in list_weeks:
                dict_lost_segments[str_class].append(float_margin * dict_lost[(str_sku, str_week)])
            for dict_shift in list_shifts:
                expression_term = float_margin * dict_backlog[(str_sku, dict_shift['index'])]
                if dict_shift['week_index'] < 2:
                    list_backlog_segments[0].append(expression_term)
                elif dict_shift['week_index'] < 6:
                    list_backlog_segments[1].append(expression_term)
                else:
                    list_backlog_segments[2].append(expression_term)
    list_stage_segments = [[], [], [], []]
    for list_segment_terms in list_backlog_segments:
        if len(list_segment_terms) > 0:
            list_stage_segments[0].append(pulp.lpSum(list_segment_terms))
    for str_class in ['A', 'B', 'C']:
        if len(dict_lost_segments[str_class]) > 0:
            list_stage_segments[1].append(pulp.lpSum(dict_lost_segments[str_class]))
        if len(dict_floor_segments[str_class]) > 0:
            list_stage_segments[2].append(pulp.lpSum(dict_floor_segments[str_class]))

    return {
        'problem': problem,
        'form': dict_form,
        'position': dict_position,
        'quantity': dict_quantity,
        'form_change': dict_form_change,
        'form_hours': dict_form_hours,
        'pending': dict_pending,
        'transition': dict_transition,
        'last_color': dict_last_color,
        'entry': dict_entry,
        'initial_state': dict_initial_state,
        'inventory': dict_inventory,
        'backlog': dict_backlog,
        'lost': dict_lost,
        'floor_slack': dict_floor_slack,
        'stage_expressions': [pulp.lpSum(list_backlog_terms), pulp.lpSum(list_lost_terms),
                              pulp.lpSum(list_floor_terms), pulp.lpSum(list_cost_terms)],
        'partitions': dict_partitions,
        'segments': list_stage_segments,
        'triangle_inequality': bool_triangle,
    }


def extract_monolithic_solution(dict_scenario, dict_model):
    list_shifts = dict_scenario['shifts']
    int_offset = dict_scenario['shift_offset']
    dict_color_setup = dict_scenario['color_setup']
    list_rows = []
    dict_end_state = {'form': {}, 'pending': {}, 'color': {}, 'stock': {}, 'backlog': {}}
    for str_machine in dict_scenario['machines']:
        float_previous_pending = dict_scenario['initial_pending'][str_machine]
        str_previous_form = dict_scenario['initial_form'][str_machine]
        dict_side_state = {}
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            dict_side_state[int_side] = dict_scenario['initial_color'][(str_machine, int_side)]
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            str_form = None
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                if read_value(dict_model['form'][(str_product, str_machine, int_shift)]) > 0.5:
                    str_form = str_product
            bool_changed = str_form != str_previous_form
            float_started_hours = 0.0
            if bool_changed:
                float_started_hours = dict_scenario['form_setup'][(str_previous_form, str_form)]
            float_pending = read_value(dict_model['pending'][(str_machine, int_shift)])
            if float_pending < 1e-6:
                float_pending = 0.0
            float_form_hours = float_previous_pending - float_pending + float_started_hours
            if float_form_hours < 1e-9:
                float_form_hours = 0.0
            float_previous_pending = float_pending
            list_shift_rows = []
            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                if bool_changed:
                    dict_side_state[int_side] = None
                int_position = 1
                while int_position <= dict_scenario['positions'][str_machine]:
                    for str_sku in dict_scenario['skus_of_product'][str_form]:
                        tuple_key = (str_sku, str_machine, int_side, int_shift, int_position)
                        if tuple_key in dict_model['position'] and read_value(dict_model['position'][tuple_key]) > 0.5:
                            str_color = dict_scenario['color_of_sku'][str_sku]
                            float_color_hours = 0.0
                            str_previous_color = '-'
                            if dict_side_state[int_side] is not None:
                                str_previous_color = dict_side_state[int_side]
                                float_color_hours = dict_color_setup[(dict_side_state[int_side], str_color)]
                            dict_side_state[int_side] = str_color
                            float_quantity = read_value(dict_model['quantity'][tuple_key])
                            list_shift_rows.append({
                                'week': dict_shift['week'],
                                'date': dict_shift['date'].strftime('%Y-%m-%d'),
                                'shift': dict_shift['shift_number'],
                                'shift_index': int_offset + int_shift,
                                'machine': str_machine,
                                'side': int_side,
                                'position': int_position,
                                'product': str_form,
                                'color': str_color,
                                'sku': str_sku,
                                'kg': float_quantity,
                                'production_hours': float_quantity / dict_scenario['productivity'][str_form][str_machine],
                                'form_setup_hours': 0.0,
                                'color_setup_hours': float_color_hours,
                                'previous_form': '-',
                                'previous_color': str_previous_color,
                            })
                    int_position += 1
            bool_form_work = bool_changed or float_form_hours > 0.0
            if bool_form_work and len(list_shift_rows) == 0:
                list_shift_rows.append({
                    'week': dict_shift['week'],
                    'date': dict_shift['date'].strftime('%Y-%m-%d'),
                    'shift': dict_shift['shift_number'],
                    'shift_index': int_offset + int_shift,
                    'machine': str_machine,
                    'side': 1,
                    'position': 1,
                    'product': str_form,
                    'color': '-',
                    'sku': '-',
                    'kg': 0.0,
                    'production_hours': 0.0,
                    'form_setup_hours': 0.0,
                    'color_setup_hours': 0.0,
                    'previous_form': '-',
                    'previous_color': '-',
                })
            if bool_form_work:
                list_shift_rows[0]['form_setup_hours'] = float_form_hours
                if bool_changed:
                    list_shift_rows[0]['previous_form'] = str_previous_form
            for dict_row in list_shift_rows:
                list_rows.append(dict_row)
            str_previous_form = str_form
        dict_end_state['form'][str_machine] = str_previous_form
        dict_end_state['pending'][str_machine] = float_previous_pending
        for int_side in dict_side_state:
            dict_end_state['color'][(str_machine, int_side)] = dict_side_state[int_side]

    dict_week_values = {}
    for str_week in dict_scenario['weeks']:
        dict_week_values[str_week] = {'backlog_cost': 0.0, 'lost_sales_cost': 0.0, 'floor_slack_cost': 0.0,
                                      'form_setup_cost': 0.0, 'color_setup_cost': 0.0, 'holding_cost': 0.0}
    int_last_shift = len(list_shifts) - 1
    for str_product in dict_scenario['products']:
        float_margin = dict_scenario['margin'][str_product]
        for str_week in dict_scenario['weeks']:
            dict_week_values[str_week]['floor_slack_cost'] += float_margin * read_value(
                dict_model['floor_slack'][(str_product, str_week)])
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for str_week in dict_scenario['weeks']:
                dict_week_values[str_week]['lost_sales_cost'] += float_margin * read_value(
                    dict_model['lost'][(str_sku, str_week)])
            for dict_shift in list_shifts:
                tuple_key = (str_sku, dict_shift['index'])
                dict_week_values[dict_shift['week']]['backlog_cost'] += float_margin * read_value(
                    dict_model['backlog'][tuple_key])
                dict_week_values[dict_shift['week']]['holding_cost'] += (dict_scenario['holding_per_shift'][str_product]
                                                                         * read_value(dict_model['inventory'][tuple_key]))
            dict_end_state['stock'][str_sku] = read_value(dict_model['inventory'][(str_sku, int_last_shift)])
            dict_end_state['backlog'][str_sku] = read_value(dict_model['backlog'][(str_sku, int_last_shift)])
    for tuple_key in dict_model['form_change']:
        if dict_model['form_hours'][tuple_key] > 0.0:
            dict_week_values[list_shifts[tuple_key[3]]['week']]['form_setup_cost'] += (
                dict_scenario['setup_hourly_cost'][tuple_key[2]] * dict_model['form_hours'][tuple_key]
                * read_value(dict_model['form_change'][tuple_key]))
    for tuple_key in dict_model['transition']:
        float_hours = dict_color_setup[(dict_scenario['color_of_sku'][tuple_key[0]],
                                        dict_scenario['color_of_sku'][tuple_key[1]])]
        dict_week_values[list_shifts[tuple_key[4]]['week']]['color_setup_cost'] += (
            dict_scenario['setup_hourly_cost'][tuple_key[2]] * float_hours
            * read_value(dict_model['transition'][tuple_key]))
    for tuple_key in dict_model['entry']:
        dict_week_values[list_shifts[tuple_key[2]]['week']]['color_setup_cost'] += (
            dict_scenario['setup_hourly_cost'][tuple_key[0]] * read_value(dict_model['entry'][tuple_key]))
    return {'schedule': list_rows, 'week_values': dict_week_values, 'end_state': dict_end_state}


def evaluate_monolithic_schedule(dict_instance, dict_settings, list_schedule_rows, int_weeks):
    dict_scenario = build_monolithic_scenario(dict_instance, dict_settings, int_weeks)
    list_shifts = dict_scenario['shifts']
    int_shift_count = len(list_shifts)
    dict_color_setup = dict_scenario['color_setup']

    dict_violations = {'capacidade_h': 0.0, 'lote_minimo_kg': 0.0, 'forma_kg': 0.0, 'troca_pendente_kg': 0.0,
                       'maquina_kg': 0.0, 'sku_repetido': 0, 'posicoes_excedentes': 0}
    dict_cell_rows = {}
    dict_row_form = {}
    dict_production = {}
    for dict_row in list_schedule_rows:
        int_shift = int(dict_row['shift_index'])
        str_machine = str(dict_row['machine'])
        if int_shift < int_shift_count:
            if str_machine not in dict_scenario['machines']:
                dict_violations['maquina_kg'] += float(dict_row['kg'])
            else:
                str_product = dict_row.get('product')
                if str_product is None or str_product == '-':
                    str_product = dict_scenario['product_of_sku'][dict_row['sku']]
                if (str_machine, int_shift) not in dict_row_form:
                    dict_row_form[(str_machine, int_shift)] = str_product
                if dict_row['sku'] != '-' and float(dict_row['kg']) > 1e-9:
                    tuple_cell = (str_machine, int(dict_row['side']), int_shift)
                    if tuple_cell not in dict_cell_rows:
                        dict_cell_rows[tuple_cell] = []
                    dict_cell_rows[tuple_cell].append((int(dict_row['position']), dict_row['sku'],
                                                       float(dict_row['kg'])))
                    tuple_production = (dict_row['sku'], int_shift)
                    if tuple_production not in dict_production:
                        dict_production[tuple_production] = 0.0
                    dict_production[tuple_production] += float(dict_row['kg'])

    float_form_setup_cost = 0.0
    float_color_setup_cost = 0.0
    float_form_setup_hours = 0.0
    float_color_setup_hours = 0.0
    int_form_changes = 0
    for str_machine in dict_scenario['machines']:
        float_hourly_cost = dict_scenario['setup_hourly_cost'][str_machine]
        str_previous_form = dict_scenario['initial_form'][str_machine]
        float_pending = dict_scenario['initial_pending'][str_machine]
        dict_side_state = {}
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            dict_side_state[int_side] = dict_scenario['initial_color'][(str_machine, int_side)]
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            float_capacity = dict_scenario['shift_capacity'][(str_machine, int_shift)]
            str_form = str_previous_form
            if (str_machine, int_shift) in dict_row_form:
                str_form = dict_row_form[(str_machine, int_shift)]
            bool_changed = str_form != str_previous_form
            float_started_hours = 0.0
            if bool_changed:
                int_form_changes += 1
                float_started_hours = dict_scenario['form_setup'][(str_previous_form, str_form)]
                float_form_setup_hours += float_started_hours
                float_form_setup_cost += float_hourly_cost * float_started_hours
            float_open_hours = float_pending + float_started_hours
            float_consumed_hours = float_open_hours
            if float_consumed_hours > float_capacity:
                float_consumed_hours = float_capacity
            float_pending = float_open_hours - float_consumed_hours
            if float_pending < 1e-9:
                float_pending = 0.0
            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                if bool_changed:
                    dict_side_state[int_side] = None
                list_runs = []
                if (str_machine, int_side, int_shift) in dict_cell_rows:
                    list_runs = list(dict_cell_rows[(str_machine, int_side, int_shift)])
                    list_runs.sort()
                float_used_hours = float_consumed_hours
                list_seen_skus = []
                for tuple_run in list_runs:
                    int_position, str_sku, float_quantity = tuple_run
                    str_product = dict_scenario['product_of_sku'][str_sku]
                    if str_sku in list_seen_skus:
                        dict_violations['sku_repetido'] += 1
                    list_seen_skus.append(str_sku)
                    if int_position > dict_scenario['positions'][str_machine]:
                        dict_violations['posicoes_excedentes'] += 1
                    if str_product != str_form:
                        dict_violations['forma_kg'] += float_quantity
                    if float_pending > 0.0:
                        dict_violations['troca_pendente_kg'] += float_quantity
                    if str_machine in dict_scenario['productivity'][str_product]:
                        float_used_hours += float_quantity / dict_scenario['productivity'][str_product][str_machine]
                    else:
                        dict_violations['maquina_kg'] += float_quantity
                    if dict_scenario['min_lot'][str_product] - float_quantity > 1e-4:
                        dict_violations['lote_minimo_kg'] += dict_scenario['min_lot'][str_product] - float_quantity
                    float_change = 0.0
                    if dict_side_state[int_side] is not None:
                        float_change = dict_color_setup[(dict_side_state[int_side],
                                                         dict_scenario['color_of_sku'][str_sku])]
                    dict_side_state[int_side] = dict_scenario['color_of_sku'][str_sku]
                    float_used_hours += float_change
                    float_color_setup_hours += float_change
                    float_color_setup_cost += float_hourly_cost * float_change
                if float_used_hours - float_capacity > 1e-4:
                    dict_violations['capacidade_h'] += float_used_hours - float_capacity
            str_previous_form = str_form

    float_backlog_cost = 0.0
    float_lost_cost = 0.0
    float_holding_cost = 0.0
    float_produced = 0.0
    dict_week_stock = {}
    for str_product in dict_scenario['products']:
        float_margin = dict_scenario['margin'][str_product]
        for str_week in dict_scenario['weeks']:
            dict_week_stock[(str_product, str_week)] = 0.0
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            float_net = dict_scenario['initial_stock'][str_sku] - dict_scenario['initial_backlog'][str_sku]
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                if (str_sku, int_shift) in dict_production:
                    float_net += dict_production[(str_sku, int_shift)]
                    float_produced += dict_production[(str_sku, int_shift)]
                float_net -= dict_scenario['orders'][(str_sku, int_shift)]
                if dict_scenario['last_shift_of_week'][dict_shift['week']] == int_shift:
                    float_forecast = dict_scenario['forecast'][(str_sku, dict_shift['week'])]
                    float_served = 0.0
                    if float_net > 0.0:
                        float_served = float_forecast
                        if float_served > float_net:
                            float_served = float_net
                    float_net -= float_served
                    float_lost_cost += float_margin * (float_forecast - float_served)
                if float_net > 0.0:
                    float_holding_cost += dict_scenario['holding_per_shift'][str_product] * float_net
                    if dict_scenario['last_shift_of_week'][dict_shift['week']] == int_shift:
                        dict_week_stock[(str_product, dict_shift['week'])] += float_net
                else:
                    float_backlog_cost += float_margin * (-float_net)

    float_floor_cost = 0.0
    for str_product in dict_scenario['products']:
        for str_week in dict_scenario['weeks']:
            float_slack = dict_scenario['stock_minimum'][str_product] - dict_week_stock[(str_product, str_week)]
            if float_slack > 0.0:
                float_floor_cost += dict_scenario['margin'][str_product] * float_slack

    float_setup_cost = float_form_setup_cost + float_color_setup_cost
    float_cost = float_setup_cost + float_holding_cost
    float_total_violation = 0.0
    for str_name in dict_violations:
        float_total_violation += dict_violations[str_name]
    return {
        'weeks': dict_scenario['weeks'],
        'shifts': int_shift_count,
        'stage_values': [float_backlog_cost, float_lost_cost, float_floor_cost, float_cost],
        'backlog_cost': float_backlog_cost,
        'lost_sales_cost': float_lost_cost,
        'floor_slack_cost': float_floor_cost,
        'form_setup_cost': float_form_setup_cost,
        'color_setup_cost': float_color_setup_cost,
        'setup_cost': float_setup_cost,
        'holding_cost': float_holding_cost,
        'total_cost': float_backlog_cost + float_lost_cost + float_floor_cost + float_cost,
        'form_setup_hours': float_form_setup_hours,
        'color_setup_hours': float_color_setup_hours,
        'form_changes': int_form_changes,
        'produced_kg': float_produced,
        'violations': dict_violations,
        'total_violation': float_total_violation,
    }


def run_monolithic_plan(dict_settings, dict_instance):
    str_technique = dict_settings['monolithic_technique']
    str_solver_name = dict_settings['daily_solver_name']
    int_time_limit = int(dict_settings['monolithic_time_limit'])
    int_weeks_in_plan = int(dict_settings['weeks_in_plan'])
    int_frozen_weeks = int(dict_settings['frozen_weeks'])
    dict_scenario = build_monolithic_scenario(dict_instance, dict_settings, int_weeks_in_plan)
    list_shifts = dict_scenario['shifts']
    int_shift_count = len(list_shifts)
    int_week_count = len(dict_scenario['weeks'])

    int_binaries = 0
    int_continuous = 0
    int_constraints = 0
    int_nonzeros = 0
    for str_machine in dict_scenario['machines']:
        list_machine_products = dict_scenario['products_of_machine'][str_machine]
        int_products = len(list_machine_products)
        int_positions = dict_scenario['positions'][str_machine]
        int_sides = dict_scenario['color_sides'][str_machine]
        int_machine_skus = 0
        int_ordered_pairs = 0
        int_squared_skus = 0
        int_multi_color_skus = 0
        int_squared_multi_color_skus = 0
        int_color_pairs = 0
        for str_product in list_machine_products:
            list_product_skus = dict_scenario['skus_of_product'][str_product]
            int_machine_skus += len(list_product_skus)
            int_ordered_pairs += len(list_product_skus) * (len(list_product_skus) - 1)
            int_squared_skus += len(list_product_skus) * len(list_product_skus)
            if len(list_product_skus) >= 2:
                int_multi_color_skus += len(list_product_skus)
                int_squared_multi_color_skus += len(list_product_skus) * len(list_product_skus)
            for str_from in list_product_skus:
                for str_to in list_product_skus:
                    if str_from != str_to and dict_scenario['color_setup'][(dict_scenario['color_of_sku'][str_from],
                                                                            dict_scenario['color_of_sku'][str_to])] > 0.0:
                        int_color_pairs += 1
        str_initial_form = dict_scenario['initial_form'][str_machine]
        int_started_first = 0
        for str_to in list_machine_products:
            if dict_scenario['form_setup'][(str_initial_form, str_to)] > 0.0:
                int_started_first += 1
        int_started_rest = 0
        for str_from in list_machine_products:
            for str_to in list_machine_products:
                if dict_scenario['form_setup'][(str_from, str_to)] > 0.0:
                    int_started_rest += 1
        int_initial_state_sides = 0
        int_initial_state_rows = 0
        int_initial_state_nonzeros = 0
        for int_side in range(1, int_sides + 1):
            str_initial_color = dict_scenario['initial_color'][(str_machine, int_side)]
            if str_initial_form in list_machine_products and str_initial_color is not None:
                int_initial_state_sides += 1
                int_entry_skus = 0
                for str_sku in dict_scenario['skus_of_product'][str_initial_form]:
                    if dict_scenario['color_setup'][(str_initial_color, dict_scenario['color_of_sku'][str_sku])] > 0.0:
                        int_entry_skus += 1
                int_initial_state_rows += int_shift_count + int_shift_count * int_entry_skus
                int_initial_state_nonzeros += (2 + (int_shift_count - 1)
                                               * (3 + len(dict_scenario['skus_of_product'][str_initial_form]))
                                               + 3 * int_shift_count * int_entry_skus)
        int_cells = int_sides * int_shift_count
        int_entries = int_sides * (int_shift_count - 1) + int_initial_state_sides
        int_last_shifts = int_shift_count - 1
        int_carry_shifts = int_shift_count - 2
        if int_carry_shifts < 0:
            int_carry_shifts = 0

        int_binaries += int_products * int_shift_count + int_cells * int_positions * int_machine_skus
        int_continuous += (int_products + int_products * int_products * (int_shift_count - 1) + int_shift_count
                           + int_cells * int_positions * int_machine_skus
                           + int_cells * (int_positions - 1) * int_ordered_pairs
                           + int_sides * int_machine_skus * int_last_shifts
                           + int_entries + int_initial_state_sides * int_shift_count)

        int_constraints += int_cells
        int_nonzeros += (int_cells * (int_machine_skus * int_positions + (int_positions - 1) * int_color_pairs + 1)
                         + int_sides * ((int_shift_count - 1) + int_started_first
                                        + (int_shift_count - 1) * int_started_rest)
                         + int_entries)
        int_constraints += int_shift_count
        int_nonzeros += (int_shift_count + (int_shift_count - 1) + int_started_first
                         + (int_shift_count - 1) * int_started_rest)
        int_constraints += int_cells
        if dict_scenario['longest_form_change'] > 0.0:
            int_nonzeros += int_cells * (1 + int_machine_skus)
        else:
            int_nonzeros += int_cells
        int_constraints += int_initial_state_rows
        int_nonzeros += int_initial_state_nonzeros
        int_constraints += int_sides * (int_shift_count - 1) * int_color_pairs
        int_nonzeros += 4 * int_sides * (int_shift_count - 1) * int_color_pairs
        int_constraints += int_sides * int_last_shifts * int_machine_skus
        int_nonzeros += int_sides * int_last_shifts * (int_machine_skus * (1 + int_positions)
                                                       + (int_positions - 1) * int_ordered_pairs)
        int_constraints += int_sides * int_carry_shifts * int_machine_skus
        int_nonzeros += int_sides * int_carry_shifts * (3 * int_machine_skus + int_squared_skus)
        int_constraints += int_cells * (int_positions - 1) * int_machine_skus
        int_nonzeros += int_cells * (int_positions - 1) * int_squared_skus
        int_constraints += int_cells * (int_positions - 1) * int_multi_color_skus
        int_nonzeros += int_cells * (int_positions - 1) * int_squared_multi_color_skus
        int_constraints += int_cells * int_positions * int_products
        int_nonzeros += int_cells * int_positions * (int_machine_skus + int_products)
        int_constraints += int_cells * int_machine_skus
        int_nonzeros += int_cells * int_machine_skus * int_positions
        int_constraints += 2 * int_cells * int_positions * int_machine_skus
        int_nonzeros += 2 * int_cells * int_positions * int_machine_skus
        for dict_shift in list_shifts:
            if dict_scenario['shift_capacity'][(str_machine, dict_shift['index'])] > 0.0:
                int_nonzeros += int_sides * int_positions * int_machine_skus * 2
            else:
                int_nonzeros += int_sides * int_positions * int_machine_skus
        int_constraints += 1 + int_products * (int_shift_count - 1)
        int_nonzeros += int_products + int_products * (int_products + 1) * (int_shift_count - 1)
        int_constraints += int_products * int_shift_count
        int_nonzeros += 2 * int_products + int_products * (int_products + 1) * (int_shift_count - 1)

    int_all_skus = 0
    for str_product in dict_scenario['products']:
        list_product_skus = dict_scenario['skus_of_product'][str_product]
        int_all_skus += len(list_product_skus)
        int_slots = 0
        for str_machine in dict_scenario['machines_of_product'][str_product]:
            if str_machine in dict_scenario['machines']:
                int_slots += dict_scenario['color_sides'][str_machine] * dict_scenario['positions'][str_machine]
        int_nonzeros += len(list_product_skus) * (2 * int_shift_count + 2 * (int_shift_count - 1)
                                                  + int_shift_count * int_slots + int_week_count)
        int_nonzeros += (len(list_product_skus) + 1) * int_week_count
    int_continuous += 2 * int_all_skus * int_shift_count + int_all_skus * int_week_count
    int_continuous += len(dict_scenario['products']) * int_week_count
    int_constraints += int_all_skus * int_shift_count + int_all_skus * int_week_count
    int_nonzeros += int_all_skus * int_week_count
    int_constraints += len(dict_scenario['products']) * int_week_count
    if dict_scenario['warehouse_capacity'] is not None:
        int_constraints += int_shift_count
        int_nonzeros += int_all_skus * int_shift_count

    float_memory_mb = 1.5 * (0.6 * (int_binaries + int_continuous) + 0.5 * int_constraints + 0.1 * int_nonzeros) / 1024.0
    float_machine_memory_mb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024.0 * 1024.0)
    dict_size = {
        'analytic': {'binaries': int_binaries, 'continuous': int_continuous,
                     'variables': int_binaries + int_continuous, 'constraints': int_constraints,
                     'nonzeros': int_nonzeros, 'estimated_memory_mb': float_memory_mb},
        'max_nonzeros': int(dict_settings['monolithic_max_nonzeros']),
        'machine_memory_mb': float_machine_memory_mb,
        'memory_limit_mb': float_machine_memory_mb / 3.0,
        'built': None,
        'build_seconds': None,
        'peak_rss_mb': None,
    }

    if int_nonzeros > int(dict_settings['monolithic_max_nonzeros']) or float_memory_mb > float_machine_memory_mb / 3.0:
        dict_result = {
            'status': 'NaoMontavel',
            'technique': str_technique,
            'stage_reports': [],
            'kpis': {'backlog_cost': None, 'lost_sales_cost': None, 'floor_slack_cost': None, 'setup_cost': None,
                     'holding_cost': None, 'total_cost': None, 'solve_seconds': 0.0, 'hit_time_limit': False},
            'size': dict_size,
            'detailed_evaluation': None,
            'schedule': [],
        }
    else:
        float_solve_started_at = time.perf_counter()
        dict_extra_report = {}
        if str_technique == 'desagregado':
            int_shifts_per_week = int_shift_count // int_week_count
            dict_state = {'stock': dict(dict_scenario['initial_stock']), 'backlog': dict(dict_scenario['initial_backlog']),
                          'form': dict(dict_scenario['initial_form']), 'pending': dict(dict_scenario['initial_pending']),
                          'color': dict(dict_scenario['initial_color'])}
            list_schedule = []
            dict_week_values = {}
            list_week_reports = []
            dict_built = {'binaries': 0, 'continuous': 0, 'variables': 0, 'constraints': 0, 'nonzeros': 0}
            float_build_seconds = 0.0
            str_status = 'Optimal'
            bool_hit_time_limit = False
            int_week = 0
            while int_week < int_week_count and str_status in ('Optimal', 'Feasible'):
                int_offset = int_week * int_shifts_per_week
                str_week = dict_scenario['weeks'][int_week]
                list_week_shifts = []
                dict_week_orders = {}
                dict_week_capacity = {}
                for int_local in range(int_shifts_per_week):
                    dict_week_shift = dict(list_shifts[int_offset + int_local])
                    dict_week_shift['index'] = int_local
                    dict_week_shift['week_index'] = 0
                    list_week_shifts.append(dict_week_shift)
                    for str_product in dict_scenario['products']:
                        for str_sku in dict_scenario['skus_of_product'][str_product]:
                            dict_week_orders[(str_sku, int_local)] = dict_scenario['orders'][(str_sku, int_offset + int_local)]
                    for str_machine in dict_scenario['machines']:
                        dict_week_capacity[(str_machine, int_local)] = dict_scenario['shift_capacity'][
                            (str_machine, int_offset + int_local)]
                dict_week_scenario = dict(dict_scenario)
                dict_week_scenario['weeks'] = [str_week]
                dict_week_scenario['shifts'] = list_week_shifts
                dict_week_scenario['last_shift_of_week'] = {str_week: int_shifts_per_week - 1}
                dict_week_scenario['shift_offset'] = int_offset
                dict_week_scenario['orders'] = dict_week_orders
                dict_week_scenario['shift_capacity'] = dict_week_capacity
                dict_week_scenario['initial_stock'] = dict_state['stock']
                dict_week_scenario['initial_backlog'] = dict_state['backlog']
                dict_week_scenario['initial_form'] = dict_state['form']
                dict_week_scenario['initial_pending'] = dict_state['pending']
                dict_week_scenario['initial_color'] = dict_state['color']

                float_build_started_at = time.perf_counter()
                dict_week_model = build_monolithic_model(dict_week_scenario, False)
                float_build_seconds += time.perf_counter() - float_build_started_at
                problem = dict_week_model['problem']
                for variable in problem.variables():
                    dict_built['variables'] += 1
                    if variable.cat == pulp.LpInteger:
                        dict_built['binaries'] += 1
                    else:
                        dict_built['continuous'] += 1
                dict_built['constraints'] += len(problem.constraints)
                for str_name in problem.constraints:
                    dict_built['nonzeros'] += len(problem.constraints[str_name])

                float_left = int_time_limit - (time.perf_counter() - float_solve_started_at)
                int_week_time_limit = int(float_left / (int_week_count - int_week))
                if int_week_time_limit < 4:
                    int_week_time_limit = 4
                str_week_status, bool_week_hit_time_limit, list_week_values, list_reports = solve_lexicographic(
                    problem, dict_week_model['stage_expressions'], str_solver_name, int_week_time_limit,
                    dict_settings['threads'], int(dict_settings['solver_seed']), dict_settings['solver_log_file'])
                if bool_week_hit_time_limit:
                    bool_hit_time_limit = True
                for dict_report in list_reports:
                    dict_report['week'] = str_week
                    list_week_reports.append(dict_report)
                if str_week_status in ('Optimal', 'Feasible'):
                    if str_week_status == 'Feasible':
                        str_status = 'Feasible'
                    dict_week_solution = extract_monolithic_solution(dict_week_scenario, dict_week_model)
                    for dict_row in dict_week_solution['schedule']:
                        list_schedule.append(dict_row)
                    dict_week_values[str_week] = dict_week_solution['week_values'][str_week]
                    dict_state = dict_week_solution['end_state']
                elif int_week == 0:
                    str_status = str_week_status
                else:
                    str_status = 'Incompleto'
                int_week += 1

            list_stage_reports = []
            for int_stage in range(4):
                dict_stage_report = {'stage': int_stage + 1, 'status': 'Optimal', 'objective': 0.0, 'bound': 0.0,
                                     'gap': None, 'hit_time_limit': False, 'seconds': 0.0, 'work': None, 'nodes': None,
                                     'simplex_iterations': None, 'variables': 0, 'binaries': 0, 'integers': 0,
                                     'constraints': 0, 'nonzeros': 0, 'weeks': []}
                for dict_report in list_week_reports:
                    if dict_report['stage'] == int_stage + 1:
                        dict_stage_report['weeks'].append(dict_report)
                        if dict_report['status'] != 'Optimal':
                            dict_stage_report['status'] = dict_report['status']
                        if dict_report['objective'] is None or dict_stage_report['objective'] is None:
                            dict_stage_report['objective'] = None
                        else:
                            dict_stage_report['objective'] += dict_report['objective']
                        if dict_report['bound'] is None or dict_stage_report['bound'] is None:
                            dict_stage_report['bound'] = None
                        else:
                            dict_stage_report['bound'] += dict_report['bound']
                        if dict_report['hit_time_limit']:
                            dict_stage_report['hit_time_limit'] = True
                        dict_stage_report['seconds'] += dict_report['seconds']
                        for str_key in ['work', 'nodes', 'simplex_iterations']:
                            if dict_report[str_key] is not None:
                                if dict_stage_report[str_key] is None:
                                    dict_stage_report[str_key] = dict_report[str_key]
                                else:
                                    dict_stage_report[str_key] += dict_report[str_key]
                        for str_key in ['variables', 'binaries', 'integers', 'constraints', 'nonzeros']:
                            if dict_report[str_key] is not None:
                                dict_stage_report[str_key] += dict_report[str_key]
                if len(dict_stage_report['weeks']) > 0:
                    dict_stage_report['gap'] = compute_gap(dict_stage_report['objective'], dict_stage_report['bound'])
                    list_stage_reports.append(dict_stage_report)
            dict_size['built'] = dict_built
            dict_size['build_seconds'] = float_build_seconds
            dict_size['peak_rss_mb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

        else:
            float_build_started_at = time.perf_counter()
            dict_model = build_monolithic_model(dict_scenario, str_technique == 'preprocessamento')
            float_build_seconds = time.perf_counter() - float_build_started_at
            problem = dict_model['problem']
            dict_built = {'binaries': 0, 'continuous': 0, 'variables': 0, 'constraints': len(problem.constraints),
                          'nonzeros': 0}
            for variable in problem.variables():
                dict_built['variables'] += 1
                if variable.cat == pulp.LpInteger:
                    dict_built['binaries'] += 1
                else:
                    dict_built['continuous'] += 1
            for str_name in problem.constraints:
                dict_built['nonzeros'] += len(problem.constraints[str_name])
            dict_size['built'] = dict_built
            dict_size['build_seconds'] = float_build_seconds
            dict_size['peak_rss_mb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
            float_solve_started_at = time.perf_counter()

            dict_decomposition = None
            dict_cascade = None
            float_spent_seconds = 0.0
            if str_technique == 'preprocessamento':
                float_spent_seconds = float_build_seconds
                dict_extra_report = {'preprocessing_seconds': float_build_seconds,
                                     'removed_variables': int_binaries + int_continuous - dict_built['variables'],
                                     'removed_binaries': int_binaries - dict_built['binaries'],
                                     'removed_constraints': int_constraints - dict_built['constraints'],
                                     'removed_nonzeros': int_nonzeros - dict_built['nonzeros'],
                                     'triangle_inequality': dict_model['triangle_inequality']}
            elif str_technique in ('rf_tempo', 'rf_maquina', 'rf_produto'):
                str_decomposition = str_technique[3:]
                dict_decomposition = {'partitions': dict_model['partitions'][str_decomposition],
                                      'block_size': int(dict_settings[f'monolithic_rf_{str_decomposition}_block_size']),
                                      'fo_time_share': float(dict_settings['monolithic_fo_time_share'])}
            elif str_technique == 'cascata':
                dict_cascade = {'segments': dict_model['segments'],
                                'time_share': float(dict_settings['monolithic_cascade_time_share']),
                                'tie_breaker': float(dict_settings['monolithic_cascade_tie_breaker'])}
            elif str_technique == 'warm_start':
                float_heuristic_started_at = time.perf_counter()
                dict_requirement = {}
                dict_supply = {}
                for str_product in dict_scenario['products']:
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        dict_supply[str_sku] = dict_scenario['initial_stock'][str_sku] - dict_scenario['initial_backlog'][
                            str_sku]
                        float_cumulative = 0.0
                        for int_index in range(int_week_count):
                            str_week = dict_scenario['weeks'][int_index]
                            for dict_shift in list_shifts:
                                if dict_shift['week_index'] == int_index:
                                    float_cumulative += dict_scenario['orders'][(str_sku, dict_shift['index'])]
                            float_cumulative += dict_scenario['forecast'][(str_sku, str_week)]
                            dict_requirement[(str_sku, int_index)] = (float_cumulative
                                                                      + dict_scenario['stock_minimum'][str_product]
                                                                      * dict_scenario['color_share'][str_sku])
                dict_mounted = dict(dict_scenario['initial_form'])
                dict_pending_hours = dict(dict_scenario['initial_pending'])
                dict_side_color = dict(dict_scenario['initial_color'])
                dict_form_value = {}
                dict_run_quantity = {}
                list_heuristic_rows = []
                for dict_shift in list_shifts:
                    int_shift = dict_shift['index']
                    int_week_index = dict_shift['week_index']
                    list_look_weeks = [int_week_index]
                    if int_week_index + 1 < int_week_count:
                        list_look_weeks.append(int_week_index + 1)
                    for str_machine in dict_scenario['machines']:
                        list_machine_products = dict_scenario['products_of_machine'][str_machine]
                        float_capacity = dict_scenario['shift_capacity'][(str_machine, int_shift)]
                        str_previous = dict_mounted[str_machine]
                        str_form = None
                        if dict_pending_hours[str_machine] > 1e-9 and str_previous in list_machine_products:
                            str_form = str_previous
                        for int_look in list_look_weeks:
                            if str_form is None:
                                float_best_score = 0.0
                                str_best = None
                                for str_product in list_machine_products:
                                    float_need = 0.0
                                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                                        if dict_requirement[(str_sku, int_look)] - dict_supply[str_sku] > 0.0:
                                            float_need += dict_requirement[(str_sku, int_look)] - dict_supply[str_sku]
                                    if float_need > 1e-6:
                                        if str_product == str_previous:
                                            str_form = str_product
                                        float_reach = (dict_scenario['productivity'][str_product][str_machine]
                                                       * dict_scenario['color_sides'][str_machine] * float_capacity)
                                        if float_need > float_reach:
                                            float_need = float_reach
                                        float_score = dict_scenario['margin'][str_product] * float_need
                                        if str_best is None or float_score > float_best_score:
                                            str_best = str_product
                                            float_best_score = float_score
                                if str_form is None and str_best is not None:
                                    str_form = str_best
                        if str_form is None:
                            if str_previous in list_machine_products:
                                str_form = str_previous
                            else:
                                str_form = list_machine_products[0]
                        float_started_hours = 0.0
                        if str_form != str_previous:
                            float_started_hours = dict_scenario['form_setup'][(str_previous, str_form)]
                            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                                dict_side_color[(str_machine, int_side)] = None
                        dict_mounted[str_machine] = str_form
                        dict_form_value[(str_machine, int_shift)] = str_form
                        float_open_hours = dict_pending_hours[str_machine] + float_started_hours
                        float_consumed_hours = float_open_hours
                        if float_consumed_hours > float_capacity:
                            float_consumed_hours = float_capacity
                        dict_pending_hours[str_machine] = float_open_hours - float_consumed_hours
                        if dict_pending_hours[str_machine] < 1e-9:
                            dict_pending_hours[str_machine] = 0.0
                        int_rows_before = len(list_heuristic_rows)
                        if dict_pending_hours[str_machine] == 0.0:
                            float_rate = dict_scenario['productivity'][str_form][str_machine]
                            float_min_lot = dict_scenario['min_lot'][str_form]
                            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                                float_free_hours = float_capacity - float_consumed_hours
                                list_side_skus = []
                                for int_look in list_look_weeks:
                                    list_candidates = []
                                    for str_sku in dict_scenario['skus_of_product'][str_form]:
                                        float_need = dict_requirement[(str_sku, int_look)] - dict_supply[str_sku]
                                        if float_need > 1e-6:
                                            list_candidates.append((-float_need, str_sku))
                                    list_candidates.sort()
                                    for tuple_candidate in list_candidates:
                                        str_sku = tuple_candidate[1]
                                        float_need = dict_requirement[(str_sku, int_look)] - dict_supply[str_sku]
                                        float_quantity = 0.0
                                        if str_sku in list_side_skus:
                                            int_position = list_side_skus.index(str_sku) + 1
                                            float_quantity = float_need
                                            if float_quantity > float_rate * float_free_hours:
                                                float_quantity = float_rate * float_free_hours
                                            if float_quantity > 1e-6:
                                                dict_run_quantity[(str_sku, str_machine, int_side, int_shift,
                                                                   int_position)] += float_quantity
                                                float_free_hours -= float_quantity / float_rate
                                        elif len(list_side_skus) < dict_scenario['positions'][str_machine]:
                                            float_change = 0.0
                                            if dict_side_color[(str_machine, int_side)] is not None:
                                                float_change = dict_scenario['color_setup'][
                                                    (dict_side_color[(str_machine, int_side)],
                                                     dict_scenario['color_of_sku'][str_sku])]
                                            float_available = float_free_hours - float_change
                                            float_quantity = float_need
                                            if float_quantity > float_rate * float_available:
                                                float_quantity = float_rate * float_available
                                            if float_quantity < float_min_lot:
                                                if float_rate * float_available >= float_min_lot - 1e-9:
                                                    float_quantity = float_min_lot
                                                else:
                                                    float_quantity = 0.0
                                            if float_quantity > 1e-6:
                                                list_side_skus.append(str_sku)
                                                dict_run_quantity[(str_sku, str_machine, int_side, int_shift,
                                                                   len(list_side_skus))] = float_quantity
                                                float_free_hours -= float_change + float_quantity / float_rate
                                                dict_side_color[(str_machine, int_side)] = dict_scenario['color_of_sku'][
                                                    str_sku]
                                        if float_quantity > 1e-6:
                                            dict_supply[str_sku] += float_quantity
                                for int_index in range(len(list_side_skus)):
                                    tuple_run = (list_side_skus[int_index], str_machine, int_side, int_shift,
                                                 int_index + 1)
                                    list_heuristic_rows.append({'shift_index': int_shift, 'machine': str_machine,
                                                                'side': int_side, 'position': int_index + 1,
                                                                'product': str_form, 'sku': list_side_skus[int_index],
                                                                'kg': dict_run_quantity[tuple_run]})
                        if str_form != str_previous and len(list_heuristic_rows) == int_rows_before:
                            list_heuristic_rows.append({'shift_index': int_shift, 'machine': str_machine, 'side': 1,
                                                        'position': 1, 'product': str_form, 'sku': '-', 'kg': 0.0})
                for tuple_key in dict_model['form']:
                    str_product, str_machine, int_shift = tuple_key
                    if dict_form_value[(str_machine, int_shift)] == str_product:
                        dict_model['form'][tuple_key].setInitialValue(1)
                    else:
                        dict_model['form'][tuple_key].setInitialValue(0)
                for tuple_key in dict_model['position']:
                    if tuple_key in dict_run_quantity:
                        dict_model['position'][tuple_key].setInitialValue(1)
                        dict_model['quantity'][tuple_key].setInitialValue(dict_run_quantity[tuple_key])
                    else:
                        dict_model['position'][tuple_key].setInitialValue(0)
                        dict_model['quantity'][tuple_key].setInitialValue(0.0)
                float_heuristic_seconds = time.perf_counter() - float_heuristic_started_at
                float_spent_seconds = float_heuristic_seconds
                dict_heuristic_evaluation = evaluate_monolithic_schedule(dict_instance, dict_settings,
                                                                         list_heuristic_rows, int_weeks_in_plan)
                dict_extra_report = {'heuristic_seconds': float_heuristic_seconds,
                                     'heuristic_stage_values': dict_heuristic_evaluation['stage_values'],
                                     'heuristic_violations': dict_heuristic_evaluation['violations']}

            int_solve_limit = int(int_time_limit - float_spent_seconds)
            if int_solve_limit < 4:
                int_solve_limit = 4
            str_status, bool_hit_time_limit, list_stage_values, list_stage_reports = solve_lexicographic(
                problem, dict_model['stage_expressions'], str_solver_name, int_solve_limit, dict_settings['threads'],
                int(dict_settings['solver_seed']), dict_settings['solver_log_file'], dict_decomposition, dict_cascade)
            if len(list_stage_reports) > 0:
                for str_key in dict_extra_report:
                    list_stage_reports[0][str_key] = dict_extra_report[str_key]
            list_schedule = []
            dict_week_values = {}
            if str_status in ('Optimal', 'Feasible'):
                dict_solution = extract_monolithic_solution(dict_scenario, dict_model)
                list_schedule = dict_solution['schedule']
                dict_week_values = dict_solution['week_values']
        float_solve_seconds = time.perf_counter() - float_solve_started_at
        dict_size['peak_rss_mb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

        dict_kpis = {'backlog_cost': None, 'lost_sales_cost': None, 'floor_slack_cost': None, 'setup_cost': None,
                     'holding_cost': None, 'total_cost': None, 'solve_seconds': float_solve_seconds,
                     'hit_time_limit': bool_hit_time_limit}
        dict_detailed_evaluation = None
        if len(dict_week_values) > 0:
            dict_totals = {'backlog_cost': 0.0, 'lost_sales_cost': 0.0, 'floor_slack_cost': 0.0, 'form_setup_cost': 0.0,
                           'color_setup_cost': 0.0, 'holding_cost': 0.0}
            dict_detailed_totals = dict(dict_totals)
            for int_index in range(int_week_count):
                str_week = dict_scenario['weeks'][int_index]
                if str_week in dict_week_values:
                    for str_key in dict_totals:
                        dict_totals[str_key] += dict_week_values[str_week][str_key]
                        if int_index < int_frozen_weeks:
                            dict_detailed_totals[str_key] += dict_week_values[str_week][str_key]
            dict_kpis['backlog_cost'] = dict_totals['backlog_cost']
            dict_kpis['lost_sales_cost'] = dict_totals['lost_sales_cost']
            dict_kpis['floor_slack_cost'] = dict_totals['floor_slack_cost']
            dict_kpis['form_setup_cost'] = dict_totals['form_setup_cost']
            dict_kpis['color_setup_cost'] = dict_totals['color_setup_cost']
            dict_kpis['setup_cost'] = dict_totals['form_setup_cost'] + dict_totals['color_setup_cost']
            dict_kpis['holding_cost'] = dict_totals['holding_cost']
            dict_kpis['total_cost'] = (dict_kpis['backlog_cost'] + dict_kpis['lost_sales_cost']
                                       + dict_kpis['floor_slack_cost'] + dict_kpis['setup_cost']
                                       + dict_kpis['holding_cost'])
            dict_kpis['stage_values'] = [dict_kpis['backlog_cost'], dict_kpis['lost_sales_cost'],
                                         dict_kpis['floor_slack_cost'],
                                         dict_kpis['setup_cost'] + dict_kpis['holding_cost']]
            dict_horizon_evaluation = evaluate_monolithic_schedule(dict_instance, dict_settings, list_schedule,
                                                                   int_weeks_in_plan)
            dict_kpis['evaluated_stage_values'] = dict_horizon_evaluation['stage_values']
            dict_kpis['evaluated_total_cost'] = dict_horizon_evaluation['total_cost']
            dict_kpis['evaluated_violation'] = dict_horizon_evaluation['total_violation']
            dict_detailed_evaluation = evaluate_monolithic_schedule(dict_instance, dict_settings, list_schedule,
                                                                    int_frozen_weeks)
            dict_detailed_evaluation['model_stage_values'] = [
                dict_detailed_totals['backlog_cost'], dict_detailed_totals['lost_sales_cost'],
                dict_detailed_totals['floor_slack_cost'],
                dict_detailed_totals['form_setup_cost'] + dict_detailed_totals['color_setup_cost']
                + dict_detailed_totals['holding_cost']]

        dict_result = {
            'status': str_status,
            'technique': str_technique,
            'stage_reports': list_stage_reports,
            'kpis': dict_kpis,
            'size': dict_size,
            'detailed_evaluation': dict_detailed_evaluation,
            'schedule': list_schedule,
        }
    return dict_result
