import time

import pulp
import pandas as pd

from optimization.solver import solve_lexicographic
from optimization.weekly_model import complete_setup_matrix, build_color_reservation


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


def measure_daily_need(dict_scenario, str_product, str_week, dict_cumulative_orders, dict_produced):
    int_last_shift = dict_scenario['last_shift_of_week'][str_week]
    dict_sku_need = {}
    dict_sku_urgency = {}
    float_order_need = 0.0
    float_surplus = 0.0
    for str_sku in dict_scenario['skus_of_product'][str_product]:
        float_supply = dict_scenario['initial_stock'][str_sku] + dict_produced[str_sku]
        float_balance = float_supply - dict_cumulative_orders[(str_sku, int_last_shift)]
        dict_sku_need[str_sku] = 0.0
        dict_sku_urgency[str_sku] = None
        if float_balance < -1e-6:
            dict_sku_need[str_sku] = -float_balance
            float_order_need += -float_balance
            int_shift = int_last_shift
            while int_shift >= 0 and dict_cumulative_orders[(str_sku, int_shift)] > float_supply + 1e-6:
                dict_sku_urgency[str_sku] = int_shift
                int_shift -= 1
        elif float_balance > 0.0:
            float_surplus += float_balance
    float_target_need = dict_scenario['target'][(str_product, str_week)] - float_surplus
    if float_target_need < 1e-6:
        float_target_need = 0.0
    return dict_sku_need, dict_sku_urgency, float_order_need, float_target_need


def solve_daily_model(dict_scenario, dict_settings):
    list_shifts = dict_scenario['shifts']
    list_machines = dict_scenario['machines']
    list_products = dict_scenario['products']
    list_weeks = dict_scenario['weeks']

    float_holding_rate = float(dict_settings['annual_holding_rate'])
    float_holding_fraction = len(list_weeks) / (52.0 * len(list_shifts))

    problem = pulp.LpProblem('DailyScheduling', pulp.LpMinimize)

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
                        str_label = f'{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}'
                        dict_run[tuple_key] = pulp.LpVariable(f'yc_{str_label}', cat='Binary')
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

    dict_pending = {}
    dict_form_started = {}
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            dict_pending[(str_machine, int_shift)] = pulp.LpVariable(f'w_{str_machine}_{int_shift}', lowBound=0)
            list_started_terms = []
            for str_from in dict_previous_forms[(str_machine, int_shift)]:
                for str_to in dict_scenario['products_of_machine'][str_machine]:
                    tuple_key = (str_from, str_to, str_machine, int_shift)
                    if dict_form_hours[tuple_key] > 0.0:
                        list_started_terms.append(dict_form_hours[tuple_key] * dict_form_change[tuple_key])
            dict_form_started[(str_machine, int_shift)] = pulp.lpSum(list_started_terms)

    dict_unknown_color = {}
    dict_entry_cleaning = {}
    for str_machine in list_machines:
        for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
            if (str_machine in dict_scenario['initial_form']
                    and (str_machine, int_side) not in dict_scenario['initial_color']):
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
                        list_capacity_terms.append(dict_quantity[tuple_key] / float_rate)
                        list_capacity_terms.append(dict_scenario['color_reservation'][str_sku] * dict_run[tuple_key])
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
                problem += (dict_entry_cleaning[tuple_cell]
                            >= float_longest_color_change * (dict_unknown_color[tuple_cell]
                                                             + dict_run[(str_sku, str_machine, int_side, int_shift)]
                                                             - 1),
                            f'cor_inicial_reserva_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    for str_machine in list_machines:
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            float_capacity = dict_scenario['shift_capacity'][(str_machine, int_shift)]
            for str_product in dict_scenario['products_of_machine'][str_machine]:
                float_rate = dict_scenario['productivity'][str_product][str_machine]
                float_min_lot = dict_scenario['min_lot'][str_product]
                for str_sku in dict_scenario['skus_of_product'][str_product]:
                    for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                        tuple_key = (str_sku, str_machine, int_side, int_shift)
                        str_label = f'{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}'
                        problem += (float_min_lot * dict_run[tuple_key] <= dict_quantity[tuple_key],
                                    f'lote_minimo_turno_inferior_{str_label}')
                        problem += (dict_quantity[tuple_key] <= float_rate * float_capacity * dict_run[tuple_key],
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
                        problem += (dict_run[(str_sku, str_machine, int_side, int_shift)]
                                    <= dict_form[(str_product, str_machine, int_shift)],
                                    f'cor_da_forma_{clean_name(str_sku)}_{str_machine}_{int_side}_{int_shift}')

    float_started_at = time.perf_counter()
    float_heuristic_seconds = None
    if dict_settings['warm_start_heuristic']:
        int_shift_count = len(list_shifts)
        float_warehouse_capacity = dict_scenario['warehouse_capacity']

        dict_cumulative_orders = {}
        dict_net = {}
        dict_produced = {}
        list_total_stock = []
        for int_shift in range(int_shift_count):
            list_total_stock.append(0.0)
        for str_product in list_products:
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                dict_produced[str_sku] = 0.0
                float_cumulative = 0.0
                for int_shift in range(int_shift_count):
                    float_cumulative += dict_scenario['orders'][(str_sku, int_shift)]
                    dict_cumulative_orders[(str_sku, int_shift)] = float_cumulative
                    dict_net[(str_sku, int_shift)] = dict_scenario['initial_stock'][str_sku] - float_cumulative
                    if dict_net[(str_sku, int_shift)] > 0.0:
                        list_total_stock[int_shift] += dict_net[(str_sku, int_shift)]

        dict_mounted = {}
        dict_pending_hours = {}
        dict_unknown = {}
        for str_machine in list_machines:
            dict_mounted[str_machine] = dict_previous_forms[(str_machine, 0)][0]
            dict_pending_hours[str_machine] = 0.0
            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                if (str_machine, int_side, 0) in dict_entry_cleaning:
                    dict_unknown[(str_machine, int_side)] = True

        int_shifts_per_day = 0
        for dict_shift in list_shifts:
            if dict_shift['day_index'] == list_shifts[0]['day_index']:
                int_shifts_per_day += 1

        dict_form_value = {}
        dict_previous_form_value = {}
        dict_pending_value = {}
        dict_run_quantity = {}
        dict_unknown_value = {}
        dict_entry_value = {}
        for dict_shift in list_shifts:
            int_shift = dict_shift['index']
            str_week = dict_shift['week'].strftime('%Y-%m-%d')
            list_handled = []
            for int_pass in range(2):
                for str_machine in list_machines:
                    if str_machine not in list_handled:
                        list_machine_products = dict_scenario['products_of_machine'][str_machine]
                        str_previous = dict_mounted[str_machine]
                        str_form = None
                        if int_pass == 0:
                            if dict_pending_hours[str_machine] > 0.0:
                                str_form = str_previous
                            elif str_previous in list_machine_products:
                                dict_sku_need, dict_sku_urgency, float_order_need, float_target_need = (
                                    measure_daily_need(dict_scenario, str_previous, str_week, dict_cumulative_orders,
                                                       dict_produced))
                                if float_order_need + float_target_need > 1e-6:
                                    str_form = str_previous
                        else:
                            float_horizon_hours = 0.0
                            for int_later in range(int_shift, int_shift_count):
                                float_horizon_hours += dict_scenario['shift_capacity'][(str_machine, int_later)]
                            float_day_hours = 0.0
                            for int_later in range(int_shift, int_shift + int_shifts_per_day):
                                if int_later < int_shift_count:
                                    float_day_hours += dict_scenario['shift_capacity'][(str_machine, int_later)]
                            int_week_last_shift = dict_scenario['last_shift_of_week'][str_week]
                            str_best = None
                            float_best_score = 0.0
                            bool_best_has_orders = False
                            for str_product in list_machine_products:
                                bool_candidate = False
                                if str_product != str_previous:
                                    if str_previous not in list_machine_products:
                                        bool_candidate = True
                                    elif dict_scenario['form_setup'][(str_previous, str_product)] < float_horizon_hours:
                                        bool_candidate = True
                                if bool_candidate:
                                    dict_sku_need, dict_sku_urgency, float_order_need, float_target_need = (
                                        measure_daily_need(dict_scenario, str_product, str_week,
                                                           dict_cumulative_orders, dict_produced))
                                    float_coverage = 0.0
                                    for str_other in dict_scenario['machines_of_product'][str_product]:
                                        if str_other != str_machine and dict_mounted[str_other] == str_product:
                                            float_other_hours = -dict_pending_hours[str_other]
                                            for int_later in range(int_shift + 1, int_week_last_shift + 1):
                                                float_other_hours += dict_scenario['shift_capacity'][
                                                    (str_other, int_later)]
                                            if float_other_hours > 0.0:
                                                float_coverage += (dict_scenario['productivity'][str_product][str_other]
                                                                   * dict_scenario['color_sides'][str_other]
                                                                   * float_other_hours)
                                    bool_has_orders = True
                                    float_gap = float_order_need - float_coverage
                                    if float_gap <= 1e-6:
                                        bool_has_orders = False
                                        float_gap = float_order_need + float_target_need - float_coverage
                                    float_reach = (dict_scenario['productivity'][str_product][str_machine]
                                                   * dict_scenario['color_sides'][str_machine] * float_day_hours)
                                    if float_gap > float_reach:
                                        float_gap = float_reach
                                    float_score = dict_scenario['margin'][str_product] * float_gap
                                    if float_gap > 1e-6:
                                        bool_better = False
                                        if str_best is None:
                                            bool_better = True
                                        elif bool_has_orders and not bool_best_has_orders:
                                            bool_better = True
                                        elif bool_has_orders == bool_best_has_orders and float_score > float_best_score:
                                            bool_better = True
                                        if bool_better:
                                            str_best = str_product
                                            float_best_score = float_score
                                            bool_best_has_orders = bool_has_orders
                            if str_best is not None:
                                str_form = str_best
                            elif str_previous in list_machine_products:
                                str_form = str_previous
                            else:
                                str_form = list_machine_products[0]

                        if str_form is not None:
                            list_handled.append(str_machine)
                            dict_previous_form_value[(str_machine, int_shift)] = str_previous
                            dict_form_value[(str_machine, int_shift)] = str_form
                            float_capacity = dict_scenario['shift_capacity'][(str_machine, int_shift)]
                            float_change_hours = 0.0
                            if str_form != str_previous:
                                float_change_hours = dict_scenario['form_setup'][(str_previous, str_form)]
                                for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                                    if (str_machine, int_side) in dict_unknown:
                                        dict_unknown[(str_machine, int_side)] = False
                            dict_mounted[str_machine] = str_form
                            float_open_hours = dict_pending_hours[str_machine] + float_change_hours
                            float_spent_hours = float_open_hours
                            if float_spent_hours > float_capacity:
                                float_spent_hours = float_capacity
                            float_left_hours = float_open_hours - float_spent_hours
                            if float_left_hours < 1e-9:
                                float_left_hours = 0.0
                            dict_pending_hours[str_machine] = float_left_hours
                            dict_pending_value[(str_machine, int_shift)] = float_left_hours

                            list_sides = []
                            dict_side_hours = {}
                            dict_side_runs = {}
                            for int_side in range(1, dict_scenario['color_sides'][str_machine] + 1):
                                list_sides.append(int_side)
                                float_side_hours = 0.0
                                if float_left_hours == 0.0:
                                    float_side_hours = float_capacity - float_spent_hours
                                if (str_machine, int_side) in dict_unknown and dict_unknown[(str_machine, int_side)]:
                                    float_side_hours -= float_longest_color_change
                                dict_side_hours[int_side] = float_side_hours
                                dict_side_runs[int_side] = []

                            float_rate = dict_scenario['productivity'][str_form][str_machine]
                            float_min_lot = dict_scenario['min_lot'][str_form]
                            bool_filling = True
                            while bool_filling:
                                dict_sku_need, dict_sku_urgency, float_order_need, float_target_need = (
                                    measure_daily_need(dict_scenario, str_form, str_week, dict_cumulative_orders,
                                                       dict_produced))
                                str_action_sku = None
                                int_action_side = None
                                float_action_quantity = 0.0
                                bool_action_new_run = True

                                list_waiting = []
                                for str_sku in dict_scenario['skus_of_product'][str_form]:
                                    if dict_sku_need[str_sku] > 1e-6:
                                        list_waiting.append(str_sku)
                                while str_action_sku is None and len(list_waiting) > 0:
                                    str_candidate = list_waiting[0]
                                    for str_sku in list_waiting:
                                        if dict_sku_urgency[str_sku] < dict_sku_urgency[str_candidate]:
                                            str_candidate = str_sku
                                    list_waiting.remove(str_candidate)
                                    float_reservation = dict_scenario['color_reservation'][str_candidate]
                                    for int_side in list_sides:
                                        float_free_hours = dict_side_hours[int_side] - float_reservation
                                        if (str_candidate not in dict_side_runs[int_side]
                                                and float_rate * float_free_hours >= float_min_lot - 1e-9
                                                and float_free_hours > 1e-6):
                                            if (int_action_side is None
                                                    or dict_side_hours[int_side] > dict_side_hours[int_action_side]):
                                                int_action_side = int_side
                                    if int_action_side is not None:
                                        str_action_sku = str_candidate
                                        float_free_hours = dict_side_hours[int_action_side] - float_reservation
                                        float_action_quantity = dict_sku_need[str_candidate]
                                        if float_action_quantity > float_rate * float_free_hours:
                                            float_action_quantity = float_rate * float_free_hours
                                        if float_action_quantity < float_min_lot:
                                            float_action_quantity = float_min_lot

                                if str_action_sku is None and float_target_need > 1e-6:
                                    for int_side in list_sides:
                                        if (str_action_sku is None and len(dict_side_runs[int_side]) > 0
                                                and dict_side_hours[int_side] > 1e-6):
                                            str_action_sku = dict_side_runs[int_side][-1]
                                            int_action_side = int_side
                                            bool_action_new_run = False
                                            float_action_quantity = float_target_need
                                            if float_action_quantity > float_rate * dict_side_hours[int_side]:
                                                float_action_quantity = float_rate * dict_side_hours[int_side]
                                    for int_side in list_sides:
                                        if str_action_sku is None and len(dict_side_runs[int_side]) == 0:
                                            for str_sku in dict_scenario['skus_of_product'][str_form]:
                                                float_free_hours = (dict_side_hours[int_side]
                                                                    - dict_scenario['color_reservation'][str_sku])
                                                if (float_rate * float_free_hours >= float_min_lot - 1e-9
                                                        and float_free_hours > 1e-6):
                                                    if (str_action_sku is None
                                                            or dict_scenario['color_reservation'][str_sku]
                                                            < dict_scenario['color_reservation'][str_action_sku]):
                                                        str_action_sku = str_sku
                                            if str_action_sku is not None:
                                                int_action_side = int_side
                                                float_free_hours = (dict_side_hours[int_side]
                                                                    - dict_scenario['color_reservation'][
                                                                        str_action_sku])
                                                float_action_quantity = float_target_need
                                                if float_action_quantity > float_rate * float_free_hours:
                                                    float_action_quantity = float_rate * float_free_hours
                                                if float_action_quantity < float_min_lot:
                                                    float_action_quantity = float_min_lot

                                if str_action_sku is not None and float_warehouse_capacity is not None:
                                    for int_later in range(int_shift, int_shift_count):
                                        float_room = float_warehouse_capacity - list_total_stock[int_later]
                                        if dict_net[(str_action_sku, int_later)] < 0.0:
                                            float_room -= dict_net[(str_action_sku, int_later)]
                                        if float_room < float_action_quantity:
                                            float_action_quantity = float_room

                                if str_action_sku is None:
                                    bool_filling = False
                                elif bool_action_new_run and float_action_quantity < float_min_lot - 1e-9:
                                    bool_filling = False
                                elif float_action_quantity <= 1e-6:
                                    bool_filling = False
                                else:
                                    tuple_run = (str_action_sku, str_machine, int_action_side, int_shift)
                                    if bool_action_new_run:
                                        dict_side_runs[int_action_side].append(str_action_sku)
                                        dict_side_hours[int_action_side] -= dict_scenario['color_reservation'][
                                            str_action_sku]
                                        dict_run_quantity[tuple_run] = 0.0
                                    dict_run_quantity[tuple_run] += float_action_quantity
                                    dict_side_hours[int_action_side] -= float_action_quantity / float_rate
                                    dict_produced[str_action_sku] += float_action_quantity
                                    for int_later in range(int_shift, int_shift_count):
                                        float_old_net = dict_net[(str_action_sku, int_later)]
                                        float_new_net = float_old_net + float_action_quantity
                                        if float_old_net > 0.0:
                                            list_total_stock[int_later] -= float_old_net
                                        if float_new_net > 0.0:
                                            list_total_stock[int_later] += float_new_net
                                        dict_net[(str_action_sku, int_later)] = float_new_net

                            for int_side in list_sides:
                                tuple_cell = (str_machine, int_side, int_shift)
                                if tuple_cell in dict_entry_cleaning:
                                    dict_unknown_value[tuple_cell] = 0.0
                                    dict_entry_value[tuple_cell] = 0.0
                                    if dict_unknown[(str_machine, int_side)]:
                                        dict_unknown_value[tuple_cell] = 1.0
                                        if len(dict_side_runs[int_side]) > 0:
                                            dict_entry_value[tuple_cell] = float_longest_color_change
                                            dict_unknown[(str_machine, int_side)] = False

        for tuple_key in dict_form:
            str_product, str_machine, int_shift = tuple_key
            if dict_form_value[(str_machine, int_shift)] == str_product:
                dict_form[tuple_key].setInitialValue(1)
            else:
                dict_form[tuple_key].setInitialValue(0)
        for tuple_key in dict_form_change:
            str_from, str_to, str_machine, int_shift = tuple_key
            if (dict_previous_form_value[(str_machine, int_shift)] == str_from
                    and dict_form_value[(str_machine, int_shift)] == str_to):
                dict_form_change[tuple_key].setInitialValue(1)
            else:
                dict_form_change[tuple_key].setInitialValue(0)
        for tuple_key in dict_pending:
            dict_pending[tuple_key].setInitialValue(dict_pending_value[tuple_key])
        for tuple_key in dict_run:
            if tuple_key in dict_run_quantity:
                dict_run[tuple_key].setInitialValue(1)
                dict_quantity[tuple_key].setInitialValue(dict_run_quantity[tuple_key])
            else:
                dict_run[tuple_key].setInitialValue(0)
                dict_quantity[tuple_key].setInitialValue(0.0)
        for tuple_key in dict_entry_cleaning:
            dict_unknown_color[tuple_key].setInitialValue(dict_unknown_value[tuple_key])
            dict_entry_cleaning[tuple_key].setInitialValue(dict_entry_value[tuple_key])
        for tuple_key in dict_inventory:
            if dict_net[tuple_key] > 0.0:
                dict_inventory[tuple_key].setInitialValue(dict_net[tuple_key])
                dict_backlog[tuple_key].setInitialValue(0.0)
            else:
                dict_inventory[tuple_key].setInitialValue(0.0)
                dict_backlog[tuple_key].setInitialValue(-dict_net[tuple_key])
        for tuple_key in dict_target_slack:
            str_product, str_week = tuple_key
            int_week_last_shift = dict_scenario['last_shift_of_week'][str_week]
            float_target_gap = dict_scenario['target'][tuple_key]
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                if dict_net[(str_sku, int_week_last_shift)] > 0.0:
                    float_target_gap -= dict_net[(str_sku, int_week_last_shift)]
            if float_target_gap < 0.0:
                float_target_gap = 0.0
            dict_target_slack[tuple_key].setInitialValue(float_target_gap)
        float_heuristic_seconds = time.perf_counter() - float_started_at

    list_stage_expressions = [pulp.lpSum(list_backlog_terms), pulp.lpSum(list_target_terms),
                              pulp.lpSum(list_cost_terms)]
    str_status, bool_hit_time_limit, list_stage_values, list_stage_reports = solve_lexicographic(
        problem, list_stage_expressions, dict_settings['daily_solver_name'], int(dict_settings['daily_time_limit']),
        dict_settings['threads'], int(dict_settings['solver_seed']), dict_settings['solver_log_file'],
        float_heuristic_seconds)
    float_solve_seconds = time.perf_counter() - float_started_at

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
                        if dict_run[tuple_key].varValue > 0.5:
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
