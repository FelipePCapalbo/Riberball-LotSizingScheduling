import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.data import load_instance, list_data_files, DATA_DIR
from processing.settings import load_settings
from optimization.weekly_model import build_weekly_scenario, solve_weekly_model
from optimization.daily_model import build_daily_scenario, solve_daily_model

list_failures = []


def check(bool_condition, str_message):
    if bool_condition:
        print(f'  ok   {str_message}')
    else:
        print(f'  FAIL {str_message}')
        list_failures.append(str_message)


print('== instancias: invariantes de dados ==')
for str_file in list_data_files():
    dict_instance = load_instance(os.path.join(DATA_DIR, str_file))
    bool_margin = True
    for str_product in dict_instance['products']:
        if dict_instance['margin'][str_product] <= 0:
            bool_margin = False
        if dict_instance['min_lot'][str_product] <= 0:
            bool_margin = False
    bool_pairs = True
    for str_a in dict_instance['products']:
        for str_b in dict_instance['products']:
            if (str_a, str_b) not in dict_instance['form_setup']:
                bool_pairs = False
    list_colors = []
    for tuple_pair in dict_instance['color_setup']:
        if tuple_pair[0] not in list_colors:
            list_colors.append(tuple_pair[0])
        if tuple_pair[1] not in list_colors:
            list_colors.append(tuple_pair[1])
    bool_connected = True
    for str_color in list_colors:
        list_reached = [str_color]
        int_cursor = 0
        while int_cursor < len(list_reached):
            str_current = list_reached[int_cursor]
            for tuple_pair in dict_instance['color_setup']:
                if tuple_pair[0] == str_current and tuple_pair[1] not in list_reached:
                    list_reached.append(tuple_pair[1])
            int_cursor += 1
        if len(list_reached) != len(list_colors):
            bool_connected = False
    check(bool_margin and bool_pairs and bool_connected,
          f'{str_file}: margem>0, lote>0, matriz de formas completa, cores fortemente conexas')


print('\n== modelo semanal: hierarquia de precos sob aperto de capacidade ==')
dict_instance = load_instance(os.path.join(DATA_DIR, 'instance_micro_P2_M3_T8.xlsx'))
dict_base = load_settings()
dict_base['start_week'] = '2024-01-01'
dict_base['weeks_in_plan'] = 8
dict_base['active_machines'] = dict_instance['machines']
dict_base['weekly_time_limit'] = 60

list_first_failure = []
for float_hours in [8.0, 4.0, 2.0, 1.0, 0.5]:
    dict_settings = dict(dict_base)
    dict_settings['hours_per_shift'] = float_hours
    dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
    dict_result = solve_weekly_model(dict_scenario, dict_settings)
    dict_kpis = dict_result['kpis']
    float_sum = (dict_kpis['backlog_cost'] + dict_kpis['lost_sales_cost']
                 + dict_kpis['coverage_cost'] + dict_kpis['setup_cost'] + dict_kpis['holding_cost'])
    check(abs(float_sum - dict_kpis['total_cost']) < 1e-6,
          f'h/turno={float_hours}: decomposicao de custo soma o total')

    float_coverage = 0.0
    for dict_row in dict_result['inventory']:
        float_coverage += dict_row['slack']
    float_lost = 0.0
    float_backlog = 0.0
    for dict_row in dict_result['demand']:
        float_lost += dict_row['lost']
        float_backlog += dict_row['backlog']
    list_first_failure.append((float_hours, float_coverage, float_lost, float_backlog))

    bool_balance = True
    for str_product in dict_scenario['products']:
        float_previous = dict_scenario['initial_inventory'][str_product]
        for str_week in dict_result['weeks']:
            dict_demand_row = None
            dict_inventory_row = None
            for dict_row in dict_result['demand']:
                if dict_row['product'] == str_product and dict_row['week'] == str_week:
                    dict_demand_row = dict_row
            for dict_row in dict_result['inventory']:
                if dict_row['product'] == str_product and dict_row['week'] == str_week:
                    dict_inventory_row = dict_row
            float_produced = 0.0
            for dict_row in dict_result['production']:
                if dict_row['product'] == str_product and dict_row['week'] == str_week:
                    float_produced += dict_row['kg']
            float_left = float_previous + float_produced
            float_right = (dict_inventory_row['inventory'] + dict_demand_row['delivered_orders']
                           + dict_demand_row['delivered_forecast'])
            if abs(float_left - float_right) > 1e-2 + 1e-6 * (abs(float_left) + abs(float_right)):
                bool_balance = False
            float_previous = dict_inventory_row['inventory']
    check(bool_balance, f'h/turno={float_hours}: balanco de estoque fecha em todo produto-semana')

    bool_capacity = True
    for str_machine in dict_scenario['machines']:
        for str_week in dict_result['weeks']:
            float_used = 0.0
            for dict_row in dict_result['production']:
                if dict_row['machine'] == str_machine and dict_row['week'] == str_week:
                    float_used += dict_row['hours'] + dict_row['setup_hours']
            float_limit = 0.0
            for timestamp_week in dict_scenario['capacity'][str_machine]:
                if timestamp_week.strftime('%Y-%m-%d') == str_week:
                    float_limit = dict_scenario['capacity'][str_machine][timestamp_week]
            if float_used > float_limit + 1e-3:
                bool_capacity = False
    check(bool_capacity, f'h/turno={float_hours}: capacidade semanal respeitada')

float_first_coverage = None
float_first_lost = None
float_first_backlog = None
for tuple_row in list_first_failure:
    if tuple_row[1] > 1 and float_first_coverage is None:
        float_first_coverage = tuple_row[0]
    if tuple_row[2] > 1 and float_first_lost is None:
        float_first_lost = tuple_row[0]
    if tuple_row[3] > 1 and float_first_backlog is None:
        float_first_backlog = tuple_row[0]
check(float_first_coverage >= float_first_lost >= float_first_backlog,
      f'cobertura cede em h={float_first_coverage}, previsao em h={float_first_lost}, '
      f'carteira em h={float_first_backlog}')


print('\n== modelo diario: sequenciamento de cor com transicao proibida ==')
list_shifts = []
for int_day in range(2):
    for int_shift in range(2):
        list_shifts.append({
            'index': len(list_shifts),
            'date': pd.Timestamp('2024-01-01') + pd.Timedelta(days=int_day),
            'shift_number': int_shift + 1, 'day_index': int_day,
            'week': pd.Timestamp('2024-01-01'),
        })
str_product = 'A-L'
list_skus = [f'{str_product}-X', f'{str_product}-Y', f'{str_product}-Z']
dict_color_setup = {('X', 'Y'): 1.0, ('Y', 'X'): 2.0, ('Y', 'Z'): 1.0, ('Z', 'Y'): 1.0}
dict_orders = {}
for str_sku in list_skus:
    for dict_shift in list_shifts:
        dict_orders[(str_sku, dict_shift['index'])] = 0.0
dict_orders[(f'{str_product}-X', 0)] = 400.0
dict_orders[(f'{str_product}-Y', 1)] = 400.0
dict_orders[(f'{str_product}-Z', 3)] = 400.0
dict_scenario = {
    'shifts': list_shifts, 'machines': ['1'], 'products': [str_product],
    'skus_of_product': {str_product: list_skus},
    'product_of_sku': {f'{str_product}-X': str_product, f'{str_product}-Y': str_product,
                       f'{str_product}-Z': str_product},
    'color_of_sku': {f'{str_product}-X': 'X', f'{str_product}-Y': 'Y', f'{str_product}-Z': 'Z'},
    'machines_of_product': {str_product: ['1']}, 'products_of_machine': {'1': [str_product]},
    'shift_capacity': {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0},
    'productivity': {str_product: {'1': 100.0}},
    'form_setup': {(str_product, str_product): 0.0}, 'color_setup': dict_color_setup,
    'orders': dict_orders,
    'forecast': dict_orders.fromkeys(dict_orders, 0.0),
    'initial_stock': {f'{str_product}-X': 0.0, f'{str_product}-Y': 0.0, f'{str_product}-Z': 0.0},
    'target': {str_product: 0.0}, 'min_lot': {str_product: 50.0},
    'unit_cost': {str_product: 5.0}, 'margin': {str_product: 10.0},
    'setup_hourly_cost': {'1': 100.0}, 'positions': 2, 'shifts_per_week': 4,
}
dict_settings = {'annual_holding_rate': 0.25, 'order_backlog_multiplier': 2.0,
                 'coverage_weight': 0.25, 'daily_solver_name': 'CBC',
                 'daily_time_limit': 60, 'threads': None}
dict_result = solve_daily_model(dict_scenario, dict_settings)
list_rows = []
for dict_row in dict_result['schedule']:
    list_rows.append(dict_row)
for int_pass in range(len(list_rows)):
    for int_index in range(len(list_rows) - 1):
        tuple_left = (list_rows[int_index]['shift_index'], list_rows[int_index]['position'])
        tuple_right = (list_rows[int_index + 1]['shift_index'], list_rows[int_index + 1]['position'])
        if tuple_left > tuple_right:
            dict_swap = list_rows[int_index]
            list_rows[int_index] = list_rows[int_index + 1]
            list_rows[int_index + 1] = dict_swap
list_sequence = []
for dict_row in list_rows:
    list_sequence.append(dict_row['color'])
check(dict_result['status'] == 'Optimal', 'resolvido ate otimalidade')
bool_forbidden = False
for int_index in range(1, len(list_sequence)):
    if list_sequence[int_index - 1] == 'X' and list_sequence[int_index] == 'Z':
        bool_forbidden = True
    if list_sequence[int_index - 1] == 'Z' and list_sequence[int_index] == 'X':
        bool_forbidden = True
check(not bool_forbidden, f'nenhuma transicao proibida na sequencia {" -> ".join(list_sequence)}')
bool_times = True
for int_index in range(1, len(list_rows)):
    dict_previous = list_rows[int_index - 1]
    dict_current = list_rows[int_index]
    if dict_previous['color'] != dict_current['color']:
        float_expected = dict_color_setup[(dict_previous['color'], dict_current['color'])]
        if abs(dict_current['color_setup_hours'] - float_expected) > 1e-6:
            bool_times = False
    else:
        if dict_current['color_setup_hours'] != 0.0:
            bool_times = False
check(bool_times, 'tempo de troca cobrado == matriz DE-PARA; mesma cor nao paga (carryover)')
check(abs(dict_result['kpis']['color_setup_hours'] - 2.0) < 1e-6,
      'setup de cor total = 2h (X->Y e Y->Z atraves do turno ocioso)')
dict_used = {}
for dict_row in dict_result['schedule']:
    int_shift = dict_row['shift_index']
    if int_shift not in dict_used:
        dict_used[int_shift] = 0.0
    dict_used[int_shift] += (dict_row['production_hours'] + dict_row['color_setup_hours']
                             + dict_row['form_setup_hours'])
bool_capacity = True
for int_shift in dict_used:
    if dict_used[int_shift] > 8.0 + 1e-6:
        bool_capacity = False
check(bool_capacity, f'producao + setup cabem no turno de 8h: {dict_used}')
check(dict_result['kpis']['order_service_level'] > 99.99, 'carteira atendida 100%')
check(dict_result['kpis']['max_fractional_deviation'] < 1e-6,
      'w, u, z, zeta e phi saem inteiras sem serem declaradas binarias '
      f"(desvio maximo {dict_result['kpis']['max_fractional_deviation']:.2e})")


print('\n== modelo diario: estado de forma sobrevive a turnos ociosos ==')
str_a = 'A-L'
str_b = 'B-L'
dict_orders = {(f'{str_a}-X', 0): 400.0, (f'{str_b}-X', 3): 400.0}
for str_sku in [f'{str_a}-X', f'{str_b}-X']:
    for int_shift in range(4):
        if (str_sku, int_shift) not in dict_orders:
            dict_orders[(str_sku, int_shift)] = 0.0
dict_scenario = {
    'shifts': list_shifts, 'machines': ['1'], 'products': [str_a, str_b],
    'skus_of_product': {str_a: [f'{str_a}-X'], str_b: [f'{str_b}-X']},
    'product_of_sku': {f'{str_a}-X': str_a, f'{str_b}-X': str_b},
    'color_of_sku': {f'{str_a}-X': 'X', f'{str_b}-X': 'X'},
    'machines_of_product': {str_a: ['1'], str_b: ['1']}, 'products_of_machine': {'1': [str_a, str_b]},
    'shift_capacity': {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0},
    'productivity': {str_a: {'1': 100.0}, str_b: {'1': 100.0}},
    'form_setup': {(str_a, str_a): 0.0, (str_b, str_b): 0.0, (str_a, str_b): 3.0, (str_b, str_a): 5.0},
    'color_setup': {}, 'orders': dict_orders,
    'forecast': dict_orders.fromkeys(dict_orders, 0.0),
    'initial_stock': {f'{str_a}-X': 0.0, f'{str_b}-X': 0.0},
    'target': {str_a: 0.0, str_b: 0.0}, 'min_lot': {str_a: 50.0, str_b: 50.0},
    'unit_cost': {str_a: 5.0, str_b: 5.0}, 'margin': {str_a: 10.0, str_b: 10.0},
    'setup_hourly_cost': {'1': 100.0}, 'positions': 2, 'shifts_per_week': 4,
}
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(abs(dict_result['kpis']['form_setup_hours'] - 3.0) < 1e-6,
      'troca de forma A->B cobrada 3h atraves de 2 turnos ociosos')
check(abs(dict_result['kpis']['setup_cost'] - 300.0) < 1e-6, 'custo de setup = 3h x R$100/h')

dict_orders_same = dict(dict_orders)
dict_orders_same[(f'{str_b}-X', 3)] = 0.0
dict_orders_same[(f'{str_a}-X', 3)] = 400.0
dict_scenario['orders'] = dict_orders_same
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(dict_result['kpis']['form_setup_hours'] == 0.0,
      'mesma forma atravessando ociosidade nao paga setup')


print('\n' + '=' * 60)
if len(list_failures) == 0:
    print('TODOS OS TESTES PASSARAM')
else:
    print(f'{len(list_failures)} FALHA(S):')
    for str_message in list_failures:
        print(f'  - {str_message}')
    sys.exit(1)
