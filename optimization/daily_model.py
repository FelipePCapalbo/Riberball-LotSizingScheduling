import time

import numpy as np
import pulp
import pandas as pd
from numba import njit

from optimization.solver import solve_lexicographic
from optimization.weekly_model import complete_setup_matrix, build_color_reservation


@njit(cache=True)
def bound_color_runs(array_cell_sku, array_cell_machine, array_cell_rate, array_cell_min_lot, array_cell_reservation,
                     array_cell_unknown_color, array_sku_product, array_orders, array_initial_stock, array_target,
                     array_last_shift, array_capacity, array_keep, array_upper):
    int_skus = array_orders.shape[0]
    int_shifts = array_orders.shape[1]
    array_order_total = np.zeros(int_skus)
    array_open_orders = np.zeros(int_skus)
    for int_sku in range(int_skus):
        for int_shift in range(int_shifts):
            array_order_total[int_sku] += array_orders[int_sku, int_shift]
        if array_order_total[int_sku] > array_initial_stock[int_sku]:
            array_open_orders[int_sku] = array_order_total[int_sku] - array_initial_stock[int_sku]

    array_target_ahead = np.zeros((array_target.shape[0], int_shifts))
    for int_product in range(array_target.shape[0]):
        for int_shift in range(int_shifts):
            for int_week in range(array_target.shape[1]):
                if array_last_shift[int_week] >= int_shift:
                    if array_target[int_product, int_week] > array_target_ahead[int_product, int_shift]:
                        array_target_ahead[int_product, int_shift] = array_target[int_product, int_week]

    for int_cell in range(array_keep.shape[0]):
        int_sku = array_cell_sku[int_cell]
        int_product = array_sku_product[int_sku]
        float_min_lot = array_cell_min_lot[int_cell]
        float_rate = array_cell_rate[int_cell]
        bool_idle_sku = False
        if array_order_total[int_sku] <= 0.0 and array_target_ahead[int_product, 0] <= 0.0:
            if not array_cell_unknown_color[int_cell]:
                bool_idle_sku = True
        for int_shift in range(int_shifts):
            float_capacity = array_capacity[array_cell_machine[int_cell], int_shift]
            float_upper = float_rate * float_capacity
            float_need = array_open_orders[int_sku] + array_target_ahead[int_product, int_shift]
            if float_need < float_upper:
                float_upper = float_need
            if float_upper < float_min_lot:
                float_upper = float_min_lot
            array_upper[int_cell, int_shift] = float_upper
            if bool_idle_sku:
                array_keep[int_cell, int_shift] = False
            elif float_min_lot / float_rate + array_cell_reservation[int_cell] > float_capacity + 1e-6:
                array_keep[int_cell, int_shift] = False
            else:
                array_keep[int_cell, int_shift] = True


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

    list_week_labels = []
    dict_last_shift_of_week = {}
    for timestamp_week in list_frozen_weeks:
        str_week = timestamp_week.strftime('%Y-%m-%d')
        list_week_labels.append(str_week)
        for dict_shift in list_shifts:
            if dict_shift['week'] == timestamp_week:
                dict_last_shift_of_week[str_week] = dict_shift['index']

    dict_target = {}
    for str_product in dict_instance['products']:
        bool_has_mts = False
        for str_sku in dict_skus_of_product[str_product]:
            if dict_instance['sku_is_mts'][str_sku]:
                bool_has_mts = True
        for str_week in list_week_labels:
            if bool_has_mts:
                dict_target[(str_product, str_week)] = dict_weekly_result['targets'][str_product][str_week]
            else:
                dict_target[(str_product, str_week)] = 0.0

    dict_machines_of_product = {}
    for str_product in dict_instance['products']:
        dict_machines_of_product[str_product] = []
        for str_machine in dict_instance['machines']:
            if str_machine in dict_instance['productivity'][str_product]:
                dict_machines_of_product[str_product].append(str_machine)

    dict_products_of_machine = {}
    list_machines = []
    for str_machine in dict_instance['machines']:
        dict_products_of_machine[str_machine] = []
        for str_product in dict_instance['products']:
            if str_machine in dict_machines_of_product[str_product]:
                dict_products_of_machine[str_machine].append(str_product)
        if len(dict_products_of_machine[str_machine]) > 0:
            list_machines.append(str_machine)

    dict_color_sides = {}
    for str_machine in dict_instance['machines']:
        dict_color_sides[str_machine] = dict_instance['color_sides'][str_machine]

    dict_shift_capacity = {}
    for str_machine in dict_instance['machines']:
        for dict_shift in list_shifts:
            float_availability = dict_instance['availability'][str_machine][dict_shift['week']]
            dict_shift_capacity[(str_machine, dict_shift['index'])] = float_hours_per_shift * float_availability

    dict_color_setup, dict_color_reservation = build_color_reservation(dict_instance)
    dict_form_setup = complete_setup_matrix(dict_instance['form_setup'], dict_instance['products'])

    dict_initial_stock = {}
    for str_product in dict_instance['products']:
        for str_sku in dict_skus_of_product[str_product]:
            if str_sku in dict_instance['color_initial_stock']:
                dict_initial_stock[str_sku] = dict_instance['color_initial_stock'][str_sku]
            else:
                dict_initial_stock[str_sku] = 0.0

    float_warehouse_capacity = dict_settings['warehouse_capacity_kg']
    if float_warehouse_capacity is not None:
        float_initial_total = 0.0
        for str_sku in dict_initial_stock:
            float_initial_total += dict_initial_stock[str_sku]
        float_warehouse_capacity = float(float_warehouse_capacity)
        if float_initial_total > float_warehouse_capacity:
            float_warehouse_capacity = float_initial_total

    return {
        'shifts': list_shifts,
        'machines': list_machines,
        'products': dict_instance['products'],
        'skus_of_product': dict_skus_of_product,
        'product_of_sku': dict_product_of_sku,
        'color_of_sku': dict_color_of_sku,
        'machines_of_product': dict_machines_of_product,
        'products_of_machine': dict_products_of_machine,
        'shift_capacity': dict_shift_capacity,
        'color_sides': dict_color_sides,
        'productivity': dict_instance['productivity'],
        'form_setup': dict_form_setup,
        'color_setup': dict_color_setup,
        'color_reservation': dict_color_reservation,
        'initial_form': dict_instance['initial_form'],
        'initial_color': dict_instance['initial_color'],
        'orders': dict_orders_by_sku_shift,
        'initial_stock': dict_initial_stock,
        'target': dict_target,
        'min_lot': dict_instance['min_lot'],
        'unit_cost': dict_instance['unit_cost'],
        'margin': dict_instance['margin'],
        'setup_hourly_cost': dict_instance['setup_hourly_cost'],
        'weeks': list_week_labels,
        'last_shift_of_week': dict_last_shift_of_week,
        'warehouse_capacity': float_warehouse_capacity,
    }


def solve_daily_model(dict_scenario, dict_settings):
    list_shifts = dict_scenario['shifts']
    list_machines = dict_scenario['machines']
    list_products = dict_scenario['products']
    list_weeks = dict_scenario['weeks']

    float_holding_rate = float(dict_settings['annual_holding_rate'])
    float_holding_fraction = len(list_weeks) / (52.0 * len(list_shifts))

    problem = pulp.LpProblem('DailyScheduling', pulp.LpMinimize)

    list_unknown_color_sides = []
    for str_machine in list_machines:
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            if (str_machine in dict_scenario['initial_form']
                    and (str_machine, int_side) not in dict_scenario['initial_color']):
                list_unknown_color_sides.append((str_machine, int_side))

    list_cells = []
    for str_machine in list_machines:
        for str_product in dict_scenario['products_of_machine'][str_machine]:
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                    list_cells.append((str_sku, str_machine, int_side))

    float_preprocessing_seconds = 0.0
    float_numba_seconds = 0.0
    float_numba_compile_seconds = 0.0
    int_removed_variables = 0
    int_removed_constraints = 0
    dict_keep = {}
    dict_upper = {}
    if dict_settings['preprocessing']:
        float_preprocessing_started_at = time.perf_counter()
        list_skus = []
        list_sku_products = []
        for int_product in range(len(list_products)):
            for str_sku in dict_scenario['skus_of_product'][list_products[int_product]]:
                list_skus.append(str_sku)
                list_sku_products.append(int_product)
        array_sku_product = np.array(list_sku_products, dtype=np.int64)
        array_orders = np.zeros((len(list_skus), len(list_shifts)))
        array_initial_stock = np.zeros(len(list_skus))
        for int_sku in range(len(list_skus)):
            array_initial_stock[int_sku] = dict_scenario['initial_stock'][list_skus[int_sku]]
            for int_shift in range(len(list_shifts)):
                array_orders[int_sku, int_shift] = dict_scenario['orders'][(list_skus[int_sku], int_shift)]
        array_target = np.zeros((len(list_products), len(list_weeks)))
        array_last_shift = np.zeros(len(list_weeks), dtype=np.int64)
        for int_week in range(len(list_weeks)):
            array_last_shift[int_week] = dict_scenario['last_shift_of_week'][list_weeks[int_week]]
            for int_product in range(len(list_products)):
                array_target[int_product, int_week] = dict_scenario['target'][(list_products[int_product],
                                                                               list_weeks[int_week])]
        array_capacity = np.zeros((len(list_machines), len(list_shifts)))
        for int_machine in range(len(list_machines)):
            for int_shift in range(len(list_shifts)):
                array_capacity[int_machine, int_shift] = dict_scenario['shift_capacity'][(list_machines[int_machine],
                                                                                         int_shift)]
        array_cell_sku = np.zeros(len(list_cells), dtype=np.int64)
        array_cell_machine = np.zeros(len(list_cells), dtype=np.int64)
        array_cell_rate = np.zeros(len(list_cells))
        array_cell_min_lot = np.zeros(len(list_cells))
        array_cell_reservation = np.zeros(len(list_cells))
        array_cell_unknown_color = np.zeros(len(list_cells), dtype=np.bool_)
        for int_cell in range(len(list_cells)):
            str_sku, str_machine, int_side = list_cells[int_cell]
            str_product = dict_scenario['product_of_sku'][str_sku]
            array_cell_sku[int_cell] = list_skus.index(str_sku)
            array_cell_machine[int_cell] = list_machines.index(str_machine)
            array_cell_rate[int_cell] = dict_scenario['productivity'][str_product][str_machine]
            array_cell_min_lot[int_cell] = dict_scenario['min_lot'][str_product]
            array_cell_reservation[int_cell] = dict_scenario['color_reservation'][str_sku]
            array_cell_unknown_color[int_cell] = (str_machine, int_side) in list_unknown_color_sides
        array_keep = np.zeros((len(list_cells), len(list_shifts)), dtype=np.bool_)
        array_upper = np.zeros((len(list_cells), len(list_shifts)))

        float_compile_started_at = time.perf_counter()
        if len(bound_color_runs.signatures) == 0:
            bound_color_runs.compile('(int64[::1], int64[::1], float64[::1], float64[::1], float64[::1], '
                                     'boolean[::1], int64[::1], float64[:, ::1], float64[::1], float64[:, ::1], '
                                     'int64[::1], float64[:, ::1], boolean[:, ::1], float64[:, ::1])')
        float_numba_compile_seconds = time.perf_counter() - float_compile_started_at
        float_kernel_started_at = time.perf_counter()
        bound_color_runs(array_cell_sku, array_cell_machine, array_cell_rate, array_cell_min_lot,
                         array_cell_reservation, array_cell_unknown_color, array_sku_product, array_orders,
                         array_initial_stock, array_target, array_last_shift, array_capacity, array_keep,
                         array_upper)
        float_numba_seconds = time.perf_counter() - float_kernel_started_at

        for int_cell in range(len(list_cells)):
            str_sku, str_machine, int_side = list_cells[int_cell]
            for int_shift in range(len(list_shifts)):
                dict_keep[(str_sku, str_machine, int_side, int_shift)] = bool(array_keep[int_cell, int_shift])
                dict_upper[(str_sku, str_machine, int_side, int_shift)] = float(array_upper[int_cell, int_shift])
        float_preprocessing_seconds = time.perf_counter() - float_preprocessing_started_at
    else:
        for tuple_cell in list_cells:
            str_sku, str_machine, int_side = tuple_cell
            float_rate = dict_scenario['productivity'][dict_scenario['product_of_sku'][str_sku]][str_machine]
            for int_shift in range(len(list_shifts)):
                dict_keep[(str_sku, str_machine, int_side, int_shift)] = True
                dict_upper[(str_sku, str_machine, int_side, int_shift)] = (
                    float_rate * dict_scenario['shift_capacity'][(str_machine, int_shift)])

    dict_form = {}
    dict_run = {}
    dict_quantity = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                str_label = f'{clean_name(str_product)}_{str_machine}_{int_shift}'
                dict_form[(str_product, str_machine, int_shift)] = pulp.LpVariable(f'y_{str_label}', cat='Binary')
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        tuple_key = (str_sku, str_machine, int_side, int_shift)
                        if dict_keep[tuple_key]:
                            str_label = f'{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}'
                            dict_run[tuple_key] = pulp.LpVariable(f'yc_{str_label}', cat='Binary')
                            dict_quantity[tuple_key] = pulp.LpVariable(f'x_{str_label}', lowBound=0)
                        else:
                            int_removed_variables += 2
                            int_removed_constraints += 4
                            if (str_machine, int_side) in list_unknown_color_sides:
                                int_removed_constraints += 1

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
            elif str_machine in dict_scenario['initial_form']:
                list_previous_forms.append(dict_scenario['initial_form'][str_machine])
            else:
                list_previous_forms.append('0')
            dict_previous_forms[(str_machine, int_shift)] = list_previous_forms
            for str_from in list_previous_forms:
                for str_to in dict_scenario['products_of_machine'][str_machine]:
                    tuple_key = (str_from, str_to, str_machine, int_shift)
                    str_label = f'{clean_name(str_from)}_{clean_name(str_to)}_{str_machine}_{int_shift}'
                    dict_form_change[tuple_key] = pulp.LpVariable(f'z_{str_label}', lowBound=0, upBound=1)
                    dict_form_hours[tuple_key] = dict_scenario['form_setup'][(str_from, str_to)]

    float_longest_form_change = 0.0
    for tuple_pair in dict_scenario['form_setup']:
        if dict_scenario['form_setup'][tuple_pair] > float_longest_form_change:
            float_longest_form_change = dict_scenario['form_setup'][tuple_pair]
    float_longest_color_change = 0.0
    for tuple_pair in dict_scenario['color_setup']:
        if dict_scenario['color_setup'][tuple_pair] > float_longest_color_change:
            float_longest_color_change = dict_scenario['color_setup'][tuple_pair]

    float_pending_bound = None
    if dict_settings['preprocessing']:
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

    dict_unknown_color = {}
    dict_entry_cleaning = {}
    for tuple_side in list_unknown_color_sides:
        str_machine, int_side = tuple_side
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            dict_unknown_color[(str_machine, int_side, int_shift)] = pulp.LpVariable(
                f'u_{str_machine}_{int_side}_{int_shift}', lowBound=0, upBound=1)
            dict_entry_cleaning[(str_machine, int_side, int_shift)] = pulp.LpVariable(
                f'e_{str_machine}_{int_side}_{int_shift}', lowBound=0)

    dict_inventory = {}
    dict_backlog = {}
    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                str_label = f'{clean_name(str_sku)}_{int_shift}'
                dict_inventory[(str_sku, int_shift)] = pulp.LpVariable(f'I_{str_label}', lowBound=0)
                dict_backlog[(str_sku, int_shift)] = pulp.LpVariable(f'b_{str_label}', lowBound=0)

    dict_target_slack = {}
    for str_product in list_products:
        for str_week in list_weeks:
            dict_target_slack[(str_product, str_week)] = pulp.LpVariable(
                f'g_{clean_name(str_product)}_{clean_name(str_week)}', lowBound=0)

    list_backlog_terms = []
    list_target_terms = []
    list_cost_terms = []
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        float_holding_per_shift = float_holding_rate * float_holding_fraction * dict_scenario['unit_cost'][str_product]
        for str_week in list_weeks:
            list_target_terms.append(float_margin * dict_target_slack[(str_product, str_week)])
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for int_shift in range(len(list_shifts)):
                list_backlog_terms.append(float_margin * dict_backlog[(str_sku, int_shift)])
                list_cost_terms.append(float_holding_per_shift * dict_inventory[(str_sku, int_shift)])

    for tuple_key in dict_form_change:
        if dict_form_hours[tuple_key] > 0.0:
            list_cost_terms.append(dict_scenario['setup_hourly_cost'][tuple_key[2]] * dict_form_hours[tuple_key]
                                   * dict_form_change[tuple_key])

    for tuple_key in dict_run:
        str_sku, str_machine, int_side, int_shift = tuple_key
        float_hours = dict_scenario['color_reservation'][str_sku]
        list_cost_terms.append(dict_scenario['setup_hourly_cost'][str_machine] * float_hours * dict_run[tuple_key])

    for str_product in list_products:
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            for int_shift in range(len(list_shifts)):
                list_production_terms = []
                for str_machine in dict_scenario['machines_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        if (str_sku, str_machine, int_side, int_shift) in dict_quantity:
                            list_production_terms.append(dict_quantity[(str_sku, str_machine, int_side, int_shift)])
                if int_shift == 0:
                    expression_previous_stock = dict_scenario['initial_stock'][str_sku]
                    expression_previous_backlog = 0.0
                else:
                    expression_previous_stock = dict_inventory[(str_sku, int_shift - 1)]
                    expression_previous_backlog = dict_backlog[(str_sku, int_shift - 1)]
                problem += (expression_previous_stock + pulp.lpSum(list_production_terms)
                            + dict_backlog[(str_sku, int_shift)]
                            == dict_inventory[(str_sku, int_shift)] + dict_scenario['orders'][(str_sku, int_shift)]
                            + expression_previous_backlog,
                            f'balanco_turno_{clean_name(str_sku)}_{int_shift}')

    for str_product in list_products:
        for str_week in list_weeks:
            int_week_last_shift = dict_scenario['last_shift_of_week'][str_week]
            list_week_stock_terms = []
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                list_week_stock_terms.append(dict_inventory[(str_sku, int_week_last_shift)])
            problem += (pulp.lpSum(list_week_stock_terms) + dict_target_slack[(str_product, str_week)]
                        >= dict_scenario['target'][(str_product, str_week)],
                        f'meta_semana_{clean_name(str_product)}_{clean_name(str_week)}')

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
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                list_capacity_terms = []
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    float_rate = dict_scenario['productivity'][str_product][str_machine]
                    for str_sku in dict_scenario['skus_of_product'][str_product]:
                        tuple_key = (str_sku, str_machine, int_side, int_shift)
                        if tuple_key in dict_run:
                            list_capacity_terms.append(dict_quantity[tuple_key] / float_rate)
                            list_capacity_terms.append(dict_scenario['color_reservation'][str_sku]
                                                       * dict_run[tuple_key])
                if int_shift > 0:
                    list_capacity_terms.append(dict_pending[(str_machine, int_shift - 1)])
                list_capacity_terms.append(-1.0 * dict_pending[(str_machine, int_shift)])
                list_capacity_terms.append(dict_form_started[(str_machine, int_shift)])
                if (str_machine, int_side, int_shift) in dict_entry_cleaning:
                    list_capacity_terms.append(dict_entry_cleaning[(str_machine, int_side, int_shift)])
                problem += (pulp.lpSum(list_capacity_terms)
                            <= dict_scenario['shift_capacity'][(str_machine, int_shift)],
                            f'capacidade_turno_{str_machine}_{int_side}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            if int_shift > 0:
                expression_previous_pending = dict_pending[(str_machine, int_shift - 1)]
            else:
                expression_previous_pending = 0.0
            problem += (dict_pending[(str_machine, int_shift)]
                        <= expression_previous_pending + dict_form_started[(str_machine, int_shift)],
                        f'troca_pendente_{str_machine}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        tuple_key = (str_sku, str_machine, int_side, int_shift)
                        if tuple_key in dict_run:
                            problem += (dict_pending[(str_machine, int_shift)]
                                        <= float_longest_form_change * (1 - dict_run[tuple_key]),
                                        f'troca_concluida_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    for tuple_cell in dict_entry_cleaning:
        str_machine, int_side, int_shift = tuple_cell
        list_reset_terms = []
        if int_shift > 0:
            expression_previous_unknown = dict_unknown_color[(str_machine, int_side, int_shift - 1)]
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    if (str_sku, str_machine, int_side, int_shift - 1) in dict_run:
                        list_reset_terms.append(dict_run[(str_sku, str_machine, int_side, int_shift - 1)])
        else:
            expression_previous_unknown = 1.0
        for str_from in dict_previous_forms[(str_machine, int_shift)]:
            for str_to in dict_scenario['products_of_machine'][str_machine]:
                if str_from != str_to:
                    list_reset_terms.append(dict_form_change[(str_from, str_to, str_machine, int_shift)])
        problem += (dict_unknown_color[tuple_cell] >= expression_previous_unknown - pulp.lpSum(list_reset_terms),
                    f'cor_inicial_estado_{str_machine}_{int_side}_{int_shift}')
        for str_product in dict_scenario['products_of_machine'][str_machine]:
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                if (str_sku, str_machine, int_side, int_shift) in dict_run:
                    problem += (dict_entry_cleaning[tuple_cell]
                                >= float_longest_color_change * (dict_unknown_color[tuple_cell]
                                                                 + dict_run[(str_sku, str_machine, int_side, int_shift)]
                                                                 - 1),
                                f'cor_inicial_reserva_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                float_min_lot = dict_scenario['min_lot'][str_product]
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        tuple_key = (str_sku, str_machine, int_side, int_shift)
                        if tuple_key in dict_run:
                            str_label = f'{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}'
                            problem += (float_min_lot * dict_run[tuple_key] <= dict_quantity[tuple_key],
                                        f'lote_minimo_turno_inferior_{str_label}')
                            problem += (dict_quantity[tuple_key] <= dict_upper[tuple_key] * dict_run[tuple_key],
                                        f'lote_minimo_turno_superior_{str_label}')

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

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_to in dict_scenario['products_of_machine'][str_machine]:
                list_entry_terms = []
                for str_from in dict_previous_forms[(str_machine, int_shift)]:
                    list_entry_terms.append(dict_form_change[(str_from, str_to, str_machine, int_shift)])
                problem += (pulp.lpSum(list_entry_terms) == dict_form[(str_to, str_machine, int_shift)],
                            f'forma_entrada_{clean_name(str_to)}_{str_machine}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        if (str_sku, str_machine, int_side, int_shift) in dict_run:
                            problem += (dict_run[(str_sku, str_machine, int_side, int_shift)]
                                        <= dict_form[(str_product, str_machine, int_shift)],
                                        f'cor_da_forma_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    list_stage_expressions = [pulp.lpSum(list_backlog_terms), pulp.lpSum(list_target_terms),
                              pulp.lpSum(list_cost_terms)]
    float_started_at = time.perf_counter()
    str_status, bool_hit_time_limit, list_stage_values, list_stage_reports = solve_lexicographic(
        problem, list_stage_expressions, dict_settings['daily_solver_name'],
        float(dict_settings['daily_time_limit']) - float_preprocessing_seconds,
        dict_settings['threads'], int(dict_settings['solver_seed']), dict_settings['solver_log_file'])
    float_solve_seconds = time.perf_counter() - float_started_at
    for dict_report in list_stage_reports:
        dict_report['preprocessing_seconds'] = float_preprocessing_seconds
        dict_report['numba_seconds'] = float_numba_seconds
        dict_report['numba_compile_seconds'] = float_numba_compile_seconds
        dict_report['removed_variables'] = int_removed_variables
        dict_report['removed_constraints'] = int_removed_constraints

    if str_status not in ('Optimal', 'Feasible'):
        dict_result = {'status': str_status, 'stage_reports': list_stage_reports, 'kpis': {}}
    else:
        dict_plan = {'quantity': {}, 'sequence': {}, 'form': {}, 'form_change': {}, 'pending': {}, 'color_hours': {},
                     'previous_color': {}}
        for str_machine in list_machines:
            for dict_shift in list_shifts:
                int_shift = dict_shift['index']
                float_pending = dict_pending[(str_machine, int_shift)].varValue
                if float_pending is None or float_pending < 1e-6:
                    float_pending = 0.0
                dict_plan['pending'][(str_machine, int_shift)] = float_pending
                for str_product in dict_scenario['products_of_machine'][str_machine]:
                    if dict_form[(str_product, str_machine, int_shift)].varValue > 0.5:
                        dict_plan['form'][(str_machine, int_shift)] = str_product
                str_mounted_form = dict_plan['form'][(str_machine, int_shift)]
                for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                    dict_plan['sequence'][(str_machine, int_side, int_shift)] = []
                    for str_sku in dict_scenario['skus_of_product'][str_mounted_form]:
                        tuple_key = (str_sku, str_machine, int_side, int_shift)
                        if tuple_key in dict_run and dict_run[tuple_key].varValue > 0.5:
                            dict_plan['quantity'][tuple_key] = dict_quantity[tuple_key].varValue
                            dict_plan['sequence'][(str_machine, int_side, int_shift)].append(str_sku)
                            dict_plan['color_hours'][tuple_key] = dict_scenario['color_reservation'][str_sku]
                            dict_plan['previous_color'][tuple_key] = '-'
        for tuple_key in dict_form_change:
            if tuple_key[0] != tuple_key[1] and dict_form_change[tuple_key].varValue > 0.5:
                dict_plan['form_change'][(tuple_key[2], tuple_key[3])] = (tuple_key[0], dict_form_hours[tuple_key])

        dict_result = build_daily_result(dict_scenario, dict_settings, dict_plan)
        dict_result['status'] = str_status
        dict_result['stage_objectives'] = list_stage_values
        dict_result['stage_reports'] = list_stage_reports
        dict_result['kpis']['solve_seconds'] = float_solve_seconds
        dict_result['kpis']['hit_time_limit'] = bool_hit_time_limit
        dict_result['plan'] = dict_plan

    return dict_result


def build_daily_result(dict_scenario, dict_settings, dict_plan):
    list_shifts = dict_scenario['shifts']
    list_machines = dict_scenario['machines']
    list_products = dict_scenario['products']
    list_weeks = dict_scenario['weeks']
    float_holding_rate = float(dict_settings['annual_holding_rate'])
    float_holding_fraction = len(list_weeks) / (52.0 * len(list_shifts))

    list_schedule_rows = []
    float_form_setup_hours = 0.0
    float_color_setup_hours = 0.0
    float_setup_cost = 0.0
    dict_production = {}
    for str_machine in list_machines:
        float_hourly_cost = dict_scenario['setup_hourly_cost'][str_machine]
        float_previous_pending = 0.0
        str_previous_form = '-'
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            str_mounted_form = dict_plan['form'][(str_machine, int_shift)]

            float_started_hours = 0.0
            if (str_machine, int_shift) in dict_plan['form_change']:
                str_previous_form, float_started_hours = dict_plan['form_change'][(str_machine, int_shift)]
            float_pending = dict_plan['pending'][(str_machine, int_shift)]
            float_form_hours = float_previous_pending - float_pending + float_started_hours
            if float_form_hours < 1e-9:
                float_form_hours = 0.0
            float_previous_pending = float_pending
            bool_form_work = float_form_hours > 0.0 or (str_machine, int_shift) in dict_plan['form_change']
            float_form_setup_hours += float_form_hours
            float_setup_cost += float_hourly_cost * float_form_hours

            list_shift_rows = []
            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                int_position = 0
                for str_sku in dict_plan['sequence'][(str_machine, int_side, int_shift)]:
                    tuple_key = (str_sku, str_machine, int_side, int_shift)
                    str_product = dict_scenario['product_of_sku'][str_sku]
                    float_quantity = dict_plan['quantity'][tuple_key]
                    float_color_hours = dict_plan['color_hours'][tuple_key]
                    float_color_setup_hours += float_color_hours
                    float_setup_cost += float_hourly_cost * float_color_hours
                    if (str_sku, int_shift) not in dict_production:
                        dict_production[(str_sku, int_shift)] = 0.0
                    dict_production[(str_sku, int_shift)] += float_quantity
                    int_position += 1
                    list_shift_rows.append({
                        'date': dict_shift['date'].strftime('%Y-%m-%d'),
                        'shift': dict_shift['shift_number'],
                        'shift_index': int_shift,
                        'machine': str_machine,
                        'side': int_side,
                        'position': int_position,
                        'product': str_product,
                        'color': dict_scenario['color_of_sku'][str_sku],
                        'sku': str_sku,
                        'kg': float_quantity,
                        'production_hours': float_quantity / dict_scenario['productivity'][str_product][str_machine],
                        'form_setup_hours': 0.0,
                        'color_setup_hours': float_color_hours,
                        'previous_form': '-',
                        'previous_color': dict_plan['previous_color'][tuple_key],
                    })
            if bool_form_work and len(list_shift_rows) == 0:
                list_shift_rows.append({
                    'date': dict_shift['date'].strftime('%Y-%m-%d'),
                    'shift': dict_shift['shift_number'],
                    'shift_index': int_shift,
                    'machine': str_machine,
                    'side': 1,
                    'position': 1,
                    'product': str_mounted_form,
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
                list_shift_rows[0]['previous_form'] = str_previous_form
            for dict_row in list_shift_rows:
                list_schedule_rows.append(dict_row)

    list_order_rows = []
    dict_inventory = {}
    float_backlog_cost = 0.0
    float_holding_cost = 0.0
    float_total_orders = 0.0
    float_final_backlog = 0.0
    for str_product in list_products:
        float_margin = dict_scenario['margin'][str_product]
        float_holding_per_shift = float_holding_rate * float_holding_fraction * dict_scenario['unit_cost'][str_product]
        for str_sku in dict_scenario['skus_of_product'][str_product]:
            float_net_position = dict_scenario['initial_stock'][str_sku]
            float_previous_backlog = 0.0
            for int_shift in range(len(list_shifts)):
                float_orders = dict_scenario['orders'][(str_sku, int_shift)]
                float_net_position -= float_orders
                if (str_sku, int_shift) in dict_production:
                    float_net_position += dict_production[(str_sku, int_shift)]
                if float_net_position > 0.0:
                    float_inventory = float_net_position
                    float_backlog = 0.0
                else:
                    float_inventory = 0.0
                    float_backlog = -float_net_position
                dict_inventory[(str_sku, int_shift)] = float_inventory
                float_backlog_cost += float_margin * float_backlog
                float_holding_cost += float_holding_per_shift * float_inventory
                float_total_orders += float_orders
                list_order_rows.append({
                    'sku': str_sku,
                    'product': str_product,
                    'color': dict_scenario['color_of_sku'][str_sku],
                    'shift_index': int_shift,
                    'date': list_shifts[int_shift]['date'].strftime('%Y-%m-%d'),
                    'shift': list_shifts[int_shift]['shift_number'],
                    'orders': float_orders,
                    'delivered_orders': float_orders + float_previous_backlog - float_backlog,
                    'backlog': float_backlog,
                    'inventory': float_inventory,
                })
                float_previous_backlog = float_backlog
            float_final_backlog += float_previous_backlog

    list_target_rows = []
    float_target_slack_cost = 0.0
    for str_product in list_products:
        for str_week in list_weeks:
            int_week_last_shift = dict_scenario['last_shift_of_week'][str_week]
            float_final_stock = 0.0
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                float_final_stock += dict_inventory[(str_sku, int_week_last_shift)]
            float_slack = dict_scenario['target'][(str_product, str_week)] - float_final_stock
            if float_slack < 0.0:
                float_slack = 0.0
            float_target_slack_cost += dict_scenario['margin'][str_product] * float_slack
            list_target_rows.append({
                'product': str_product,
                'week': str_week,
                'target': dict_scenario['target'][(str_product, str_week)],
                'final_stock': float_final_stock,
                'slack': float_slack,
            })

    if float_total_orders > 0:
        float_order_service = (1.0 - float_final_backlog / float_total_orders) * 100.0
    else:
        float_order_service = 100.0

    return {
        'schedule': list_schedule_rows,
        'orders': list_order_rows,
        'targets': list_target_rows,
        'shifts': len(list_shifts),
        'kpis': {
            'total_cost': float_backlog_cost + float_target_slack_cost + float_setup_cost + float_holding_cost,
            'backlog_cost': float_backlog_cost,
            'target_slack_cost': float_target_slack_cost,
            'setup_cost': float_setup_cost,
            'holding_cost': float_holding_cost,
            'order_service_level': float_order_service,
            'form_setup_hours': float_form_setup_hours,
            'color_setup_hours': float_color_setup_hours,
            'total_setups': len(list_schedule_rows),
        },
    }
