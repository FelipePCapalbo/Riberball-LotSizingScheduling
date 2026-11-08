import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.data import load_instance, list_data_files, DATA_DIR
from processing.settings import load_settings
from optimization.weekly_model import build_weekly_scenario, solve_weekly_model, complete_setup_matrix
from optimization.daily_model import build_daily_scenario, solve_daily_model
from optimization.sequencing import evaluate_sequence, sequence_daily_plan

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
dict_base['weekly_time_limit'] = 60
dict_base['decomposition'] = None
for str_product in dict_instance['products']:
    dict_instance['mape'][str_product] = 0.0
    for str_color in dict_instance['colors_by_product'][str_product]:
        dict_instance['sku_is_mts'][f'{str_product}-{str_color}'] = False

list_first_failure = []
for float_hours in [8.0, 4.0, 2.0, 1.0, 0.5]:
    dict_settings = dict(dict_base)
    dict_settings['hours_per_shift'] = float_hours
    dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
    dict_result = solve_weekly_model(dict_scenario, dict_settings)
    dict_kpis = dict_result['kpis']
    float_sum = (dict_kpis['backlog_cost'] + dict_kpis['lost_sales_cost'] + dict_kpis['floor_slack_cost']
                 + dict_kpis['setup_cost'] + dict_kpis['holding_cost'])
    check(abs(float_sum - dict_kpis['total_cost']) < 1e-6,
          f'h/turno={float_hours}: decomposicao de custo soma o total')

    float_lost = 0.0
    float_backlog = 0.0
    for dict_row in dict_result['demand']:
        float_lost += dict_row['lost']
        float_backlog += dict_row['backlog']
    list_first_failure.append((float_hours, float_lost, float_backlog))

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

float_first_lost = None
float_first_backlog = None
for tuple_row in list_first_failure:
    if tuple_row[1] > 1 and float_first_lost is None:
        float_first_lost = tuple_row[0]
    if tuple_row[2] > 1 and float_first_backlog is None:
        float_first_backlog = tuple_row[0]
check(float_first_lost >= float_first_backlog,
      f'eq:obj_semanal: previsao cede em h={float_first_lost}, carteira em h={float_first_backlog}')


print('\n== modelo semanal: estoque minimo dos baloes MTS ==')
str_mts_product = dict_instance['products'][0]
for str_color in dict_instance['colors_by_product'][str_mts_product]:
    dict_instance['sku_is_mts'][f'{str_mts_product}-{str_color}'] = True
dict_instance['mape'][str_mts_product] = 20.0
dict_settings = dict(dict_base)
dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
float_average = 0.0
for timestamp_week in dict_scenario['weeks']:
    float_average += dict_instance['demand'][str_mts_product][timestamp_week]
float_average = float_average / len(dict_scenario['weeks'])
check(abs(dict_scenario['stock_minimum'][str_mts_product] - float_average * 1.2) < 1e-6,
      f'eq:estoque_minimo: previsao media do horizonte x (1 + 20%) = {float_average * 1.2:.1f} kg')
bool_mto_zero = True
for str_product in dict_scenario['products']:
    if str_product != str_mts_product:
        if dict_scenario['stock_minimum'][str_product] != 0.0:
            bool_mto_zero = False
check(bool_mto_zero, 'balao sem SKU MTS tem estoque minimo nulo')
dict_result = solve_weekly_model(dict_scenario, dict_settings)
list_stages = dict_result['stage_objectives']
check(len(list_stages) == 4, 'quatro estagios resolvidos (atraso, venda perdida, estoque minimo, custo)')
check(list_stages[2] < 1e-6, 'eq:piso_estoque: com capacidade folgada o estagio 3 zera a violacao do piso')
float_floor = dict_scenario['stock_minimum'][str_mts_product]
bool_floor = True
for dict_row in dict_result['inventory']:
    if dict_row['product'] == str_mts_product and dict_row['inventory'] < float_floor - 1e-4:
        bool_floor = False
check(bool_floor, f'estoque do balao MTS >= {float_floor:.1f} kg em toda semana')
check(dict_result['kpis']['backlog_cost'] <= list_stages[0] + 1e-6
      and dict_result['kpis']['lost_sales_cost'] <= list_stages[1] + 1e-6
      and dict_result['kpis']['floor_slack_cost'] <= list_stages[2] + 1e-6,
      'eq:trava: o estagio de custo nao cede atraso, venda perdida nem piso')
bool_reports = len(dict_result['stage_reports']) == 4
for dict_report in dict_result['stage_reports']:
    if dict_report['status'] not in ('Optimal', 'Feasible') or dict_report['gap'] is None:
        bool_reports = False
check(bool_reports, 'relatorio por estagio com status e gap')

bool_setup_rule = True
for str_product in dict_instance['products']:
    float_form = 0.0
    for str_other in dict_instance['products']:
        if str_other != str_product:
            float_form += dict_instance['form_setup'][(str_other, str_product)]
    float_color = 0.0
    for str_color in dict_instance['colors_by_product'][str_product]:
        float_worst = 0.0
        for str_other_color in dict_instance['colors_by_product'][str_product]:
            if (str_other_color, str_color) in dict_instance['color_setup']:
                if dict_instance['color_setup'][(str_other_color, str_color)] > float_worst:
                    float_worst = dict_instance['color_setup'][(str_other_color, str_color)]
        float_color += float_worst
    float_expected = float_form / len(dict_instance['products']) + float_color
    if abs(dict_scenario['average_setup'][str_product] - float_expected) > 1e-9:
        bool_setup_rule = False
check(bool_setup_rule, 'eq:setup_semanal: tau_i = troca media de forma sobre |I| + reserva de cor de cada SKU do balao')

print('\n== modelo semanal: capacidade do armazem ==')
float_initial_total = 0.0
for str_product in dict_instance['products']:
    float_initial_total += dict_instance['initial_inventory'][str_product]
dict_settings = dict(dict_base)
dict_settings['warehouse_capacity_kg'] = 0.0
dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
check(abs(dict_scenario['warehouse_capacity'] - float_initial_total) < 1e-6,
      f'Omega = max(capacidade, estoque inicial total) = {float_initial_total:.1f} kg')
dict_result_warehouse = solve_weekly_model(dict_scenario, dict_settings)
dict_week_total = {}
for dict_row in dict_result_warehouse['inventory']:
    if dict_row['week'] not in dict_week_total:
        dict_week_total[dict_row['week']] = 0.0
    dict_week_total[dict_row['week']] += dict_row['inventory']
bool_warehouse = True
for str_week in dict_week_total:
    if dict_week_total[str_week] > float_initial_total + 1e-4:
        bool_warehouse = False
check(bool_warehouse, 'eq:capacidade_armazem: estoque total <= Omega em toda semana')
float_peak_without_limit = 0.0
dict_free_total = {}
for dict_row in dict_result['inventory']:
    if dict_row['week'] not in dict_free_total:
        dict_free_total[dict_row['week']] = 0.0
    dict_free_total[dict_row['week']] += dict_row['inventory']
for str_week in dict_free_total:
    if dict_free_total[str_week] > float_peak_without_limit:
        float_peak_without_limit = dict_free_total[str_week]
check(float_peak_without_limit > float_initial_total + 1.0,
      f'sem limite o estoque total chega a {float_peak_without_limit:.1f} kg, acima de Omega: o limite corta')
check(dict_result_warehouse['stage_objectives'][0] <= list_stages[0] + 1e-6
      and dict_result_warehouse['stage_objectives'][1] <= list_stages[1] + 1e-6,
      'armazem limitado com capacidade folgada nao cria atraso nem venda perdida')
dict_settings['warehouse_capacity_kg'] = None
dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
check(dict_scenario['warehouse_capacity'] is None, 'sem capacidade informada a restricao nao entra')


print('\n== modelo diario: corrida de cor, reserva de troca e lote minimo ==')
list_shifts = []
for int_day in range(2):
    for int_shift in range(2):
        list_shifts.append({
            'index': len(list_shifts),
            'date': pd.Timestamp('2024-01-01') + pd.Timedelta(days=int_day),
            'shift_number': int_shift + 1, 'day_index': int_day,
            'week': pd.Timestamp('2024-01-01'),
        })
dict_settings = {'annual_holding_rate': 0.25, 'daily_solver_name': 'ORTOOLS',
                 'daily_time_limit': 60, 'threads': None, 'solver_seed': 0, 'solver_log_file': None,
                 'decomposition': None, 'daily_block_size': None, 'fo_time_share': None}
str_product = 'A-L'
list_skus = [f'{str_product}-X', f'{str_product}-Y', f'{str_product}-Z']
dict_color_setup = complete_setup_matrix({('X', 'Y'): 1.0, ('Y', 'X'): 2.0, ('Y', 'Z'): 1.0, ('Z', 'Y'): 1.0},
                                         ['X', 'Y', 'Z'])
dict_reservation = {f'{str_product}-X': 2.0, f'{str_product}-Y': 1.0, f'{str_product}-Z': 2.0}
dict_orders = {}
for str_sku in list_skus:
    for dict_shift in list_shifts:
        dict_orders[(str_sku, dict_shift['index'])] = 0.0
dict_orders[(f'{str_product}-X', 0)] = 400.0
dict_orders[(f'{str_product}-Y', 1)] = 400.0
dict_orders[(f'{str_product}-Z', 3)] = 10.0
dict_scenario = {
    'shifts': list_shifts, 'machines': ['1'], 'products': [str_product],
    'skus_of_product': {str_product: list_skus},
    'product_of_sku': {f'{str_product}-X': str_product, f'{str_product}-Y': str_product,
                       f'{str_product}-Z': str_product},
    'color_of_sku': {f'{str_product}-X': 'X', f'{str_product}-Y': 'Y', f'{str_product}-Z': 'Z'},
    'machines_of_product': {str_product: ['1']}, 'products_of_machine': {'1': [str_product]},
    'shift_capacity': {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0}, 'color_sides': {'1': 1},
    'productivity': {str_product: {'1': 100.0}},
    'form_setup': {(str_product, str_product): 0.0}, 'color_setup': dict_color_setup,
    'color_reservation': dict_reservation, 'initial_form': {'1': str_product}, 'initial_color': {},
    'orders': dict_orders,
    'initial_stock': {f'{str_product}-X': 0.0, f'{str_product}-Y': 0.0, f'{str_product}-Z': 0.0},
    'target': {(str_product, '2024-01-01'): 0.0}, 'min_lot': {str_product: 50.0},
    'unit_cost': {str_product: 5.0}, 'margin': {str_product: 10.0},
    'setup_hourly_cost': {'1': 100.0}, 'weeks': ['2024-01-01'], 'last_shift_of_week': {'2024-01-01': 3},
    'warehouse_capacity': None,
}
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(dict_result['status'] == 'Optimal', 'resolvido ate otimalidade')
check(dict_result['kpis']['order_service_level'] > 99.99, 'carteira atendida 100%')
bool_reservation = True
bool_min_lot = True
bool_one_run = True
dict_used = {}
list_seen_runs = []
for dict_row in dict_result['schedule']:
    if abs(dict_row['color_setup_hours'] - dict_reservation[dict_row['sku']]) > 1e-6:
        bool_reservation = False
    if dict_row['kg'] < 50.0 - 1e-6:
        bool_min_lot = False
    tuple_run = (dict_row['sku'], dict_row['machine'], dict_row['side'], dict_row['shift_index'])
    if tuple_run in list_seen_runs:
        bool_one_run = False
    list_seen_runs.append(tuple_run)
    int_shift = dict_row['shift_index']
    if int_shift not in dict_used:
        dict_used[int_shift] = 0.0
    dict_used[int_shift] += (dict_row['production_hours'] + dict_row['color_setup_hours']
                             + dict_row['form_setup_hours'])
bool_capacity = True
for int_shift in dict_used:
    if dict_used[int_shift] > 8.0 + 1e-6:
        bool_capacity = False
check(bool_reservation, 'eq:capacidade_turno: cada corrida reserva o pior tempo de entrada na cor')
check(bool_capacity, f'eq:capacidade_turno: producao + reserva + troca de forma cabem no turno de 8h: {dict_used}')
check(bool_min_lot, 'eq:lote_minimo_turno: toda corrida produz ao menos o lote minimo (pedido de 10 kg vira 50 kg)')
check(bool_one_run, 'uma corrida por SKU, maquina e turno')
check(abs(dict_result['kpis']['color_setup_hours'] - 5.0) < 1e-6,
      f"tres corridas reservam 2 + 1 + 2 h, X->Z ausente vale a limpeza de 2h (obtido "
      f"{dict_result['kpis']['color_setup_hours']})")
dict_reservation_scenario = dict_scenario
dict_reservation_mip = dict_result


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
    'shift_capacity': {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0}, 'color_sides': {'1': 1},
    'productivity': {str_a: {'1': 100.0}, str_b: {'1': 100.0}},
    'form_setup': {(str_a, str_a): 0.0, (str_b, str_b): 0.0, (str_a, str_b): 3.0, (str_b, str_a): 5.0},
    'color_setup': {}, 'color_reservation': {f'{str_a}-X': 0.0, f'{str_b}-X': 0.0}, 'initial_form': {'1': str_a},
    'initial_color': {},
    'orders': dict_orders,
    'initial_stock': {f'{str_a}-X': 0.0, f'{str_b}-X': 0.0},
    'target': {(str_a, '2024-01-01'): 0.0, (str_b, '2024-01-01'): 0.0}, 'min_lot': {str_a: 50.0, str_b: 50.0},
    'unit_cost': {str_a: 5.0, str_b: 5.0}, 'margin': {str_a: 10.0, str_b: 10.0},
    'setup_hourly_cost': {'1': 100.0}, 'weeks': ['2024-01-01'], 'last_shift_of_week': {'2024-01-01': 3},
    'warehouse_capacity': None,
}
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(abs(dict_result['kpis']['form_setup_hours'] - 3.0) < 1e-6,
      'eq:forma_saida + eq:forma_entrada: troca A->B cobrada 3h atraves de 2 turnos ociosos')
check(abs(dict_result['kpis']['setup_cost'] - 300.0) < 1e-6, 'custo de setup = 3h x R$100/h')

dict_orders_same = dict(dict_orders)
dict_orders_same[(f'{str_b}-X', 3)] = 0.0
dict_orders_same[(f'{str_a}-X', 3)] = 400.0
dict_scenario['orders'] = dict_orders_same
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(dict_result['kpis']['form_setup_hours'] == 0.0,
      'mesma forma atravessando ociosidade nao paga setup')

dict_scenario['orders'] = dict_orders
dict_scenario['initial_form'] = {'1': str_b}
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(abs(dict_result['kpis']['form_setup_hours'] - 8.0) < 1e-6,
      'troca contra a forma inicial: B->A no 1o turno (5h) e A->B depois (3h)')


dict_completed = complete_setup_matrix({(str_a, str_b): 3.0, ('C', str_a): 5.0}, [str_a, str_b, 'C'])
check(dict_completed[(str_b, str_a)] == 5.0 and dict_completed[('0', 'C')] == 5.0
      and dict_completed[(str_a, str_a)] == 0.0 and dict_completed[(str_a, 'C')] == 5.0,
      'troca ausente e estado inicial ficticio 0 valem o maior tempo registrado da matriz (5h)')
dict_scenario['form_setup'] = complete_setup_matrix({(str_a, str_b): 3.0, (str_b, str_a): 5.0}, [str_a, str_b])
dict_scenario['initial_form'] = {}
dict_result = solve_daily_model(dict_scenario, dict_settings)
check(abs(dict_result['kpis']['form_setup_hours'] - 8.0) < 1e-6,
      'eq:forma_saida: sem forma inicial a maquina parte do balao ficticio 0 e paga 5h + A->B 3h')
dict_scenario['form_setup'] = {(str_a, str_a): 0.0, (str_b, str_b): 0.0, (str_a, str_b): 3.0, (str_b, str_a): 5.0}

dict_scenario['form_setup'] = {(str_a, str_a): 0.0, (str_b, str_b): 0.0, (str_a, str_b): 6.0, (str_b, str_a): 6.0}
dict_scenario['initial_form'] = {'1': str_a}
dict_scenario['shift_capacity'] = {('1', 0): 4.0, ('1', 1): 4.0, ('1', 2): 4.0, ('1', 3): 4.0}
dict_crossover_orders = {}
for tuple_key in dict_orders:
    dict_crossover_orders[tuple_key] = 0.0
dict_crossover_orders[(f'{str_b}-X', 3)] = 300.0
dict_scenario['orders'] = dict_crossover_orders
dict_result = solve_daily_model(dict_scenario, dict_settings)
dict_executed = {}
for dict_row in dict_result['schedule']:
    if dict_row['shift_index'] not in dict_executed:
        dict_executed[dict_row['shift_index']] = 0.0
    dict_executed[dict_row['shift_index']] += dict_row['form_setup_hours']
bool_no_run_while_pending = True
for dict_row in dict_result['schedule']:
    if dict_row['kg'] > 0.0 and dict_result['plan']['pending'][('1', dict_row['shift_index'])] > 1e-6:
        bool_no_run_while_pending = False
float_largest_executed = 0.0
for int_shift in dict_executed:
    if dict_executed[int_shift] > float_largest_executed:
        float_largest_executed = dict_executed[int_shift]
check(dict_result['status'] == 'Optimal' and dict_result['kpis']['backlog_cost'] < 1e-6
      and abs(dict_result['kpis']['form_setup_hours'] - 6.0) < 1e-6 and float_largest_executed <= 4.0 + 1e-6,
      f'eq:troca_pendente: troca A->B de 6h em turnos de 4h atravessa a fronteira (executado por turno {dict_executed})')
check(bool_no_run_while_pending, 'eq:troca_concluida: nenhuma corrida em turno com troca pendente')
dict_scenario['shift_capacity'] = {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0}
dict_scenario['orders'] = dict_orders

print('\n== modelo diario: estagios lexicograficos ==')
dict_scenario['initial_form'] = {'1': str_a}
dict_scenario['setup_hourly_cost'] = {'1': 1.0e6}
dict_result = solve_daily_model(dict_scenario, dict_settings)
list_stages = dict_result['stage_objectives']
check(len(list_stages) == 3, 'tres estagios resolvidos (atraso, meta, custo)')
check(dict_result['kpis']['backlog_cost'] < 1e-6,
      'eq:obj_turno: atraso vem antes do setup mesmo com setup a R$1e6/h')
check(dict_result['kpis']['backlog_cost'] <= list_stages[0] + 1e-6,
      'eq:trava: o estagio de custo nao piora o atraso alcancado no estagio 1')

dict_scenario['setup_hourly_cost'] = {'1': 100.0}
dict_scenario['target'] = {(str_a, '2024-01-01'): 0.0, (str_b, '2024-01-01'): 300.0}
dict_result = solve_daily_model(dict_scenario, dict_settings)
list_stages = dict_result['stage_objectives']
check(list_stages[1] < 1e-6, 'eq:meta_semana: o estagio 2 alcanca a meta de 300 kg de B ao fim da semana')
check(dict_result['kpis']['target_slack_cost'] <= list_stages[1] + 1e-6,
      'eq:trava: o estagio de custo nao cede a meta')
float_final_b = 0.0
for dict_row in dict_result['targets']:
    if dict_row['product'] == str_b:
        float_final_b = dict_row['final_stock']
check(float_final_b >= 300.0 - 1e-4, f'estoque final de B = {float_final_b:.2f} kg >= 300 kg')


print('\n== modelo diario: meta por semana detalhada e armazem por turno ==')
list_two_week_shifts = []
for int_week in range(2):
    for int_shift in range(2):
        list_two_week_shifts.append({
            'index': len(list_two_week_shifts),
            'date': pd.Timestamp('2024-01-01') + pd.Timedelta(days=7 * int_week),
            'shift_number': int_shift + 1, 'day_index': int_week,
            'week': pd.Timestamp('2024-01-01') + pd.Timedelta(days=7 * int_week),
        })
str_c = 'C-L'
dict_orders = {}
for int_shift in range(4):
    dict_orders[(f'{str_c}-X', int_shift)] = 0.0
dict_orders[(f'{str_c}-X', 2)] = 250.0
dict_scenario = {
    'shifts': list_two_week_shifts, 'machines': ['1'], 'products': [str_c],
    'skus_of_product': {str_c: [f'{str_c}-X']}, 'product_of_sku': {f'{str_c}-X': str_c},
    'color_of_sku': {f'{str_c}-X': 'X'},
    'machines_of_product': {str_c: ['1']}, 'products_of_machine': {'1': [str_c]},
    'shift_capacity': {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0}, 'color_sides': {'1': 1},
    'productivity': {str_c: {'1': 100.0}},
    'form_setup': {(str_c, str_c): 0.0}, 'color_setup': {}, 'color_reservation': {f'{str_c}-X': 0.0},
    'initial_form': {'1': str_c}, 'initial_color': {}, 'orders': dict_orders, 'initial_stock': {f'{str_c}-X': 0.0},
    'target': {(str_c, '2024-01-01'): 300.0, (str_c, '2024-01-08'): 100.0},
    'min_lot': {str_c: 50.0}, 'unit_cost': {str_c: 5.0}, 'margin': {str_c: 10.0},
    'setup_hourly_cost': {'1': 100.0}, 'weeks': ['2024-01-01', '2024-01-08'],
    'last_shift_of_week': {'2024-01-01': 1, '2024-01-08': 3}, 'warehouse_capacity': None,
}
dict_result = solve_daily_model(dict_scenario, dict_settings)
dict_week_stock = {}
for dict_row in dict_result['targets']:
    dict_week_stock[dict_row['week']] = dict_row['final_stock']
check(len(dict_result['targets']) == 2 and dict_result['stage_objectives'][1] < 1e-6,
      'eq:meta_semana: uma meta por semana detalhada, as duas alcancadas')
check(dict_week_stock['2024-01-01'] >= 300.0 - 1e-4 and dict_week_stock['2024-01-08'] >= 100.0 - 1e-4,
      f"estoque ao fim de cada semana: {dict_week_stock['2024-01-01']:.1f} kg >= 300 e "
      f"{dict_week_stock['2024-01-08']:.1f} kg >= 100")

dict_scenario['warehouse_capacity'] = 200.0
dict_result = solve_daily_model(dict_scenario, dict_settings)
bool_warehouse = True
for dict_row in dict_result['orders']:
    if dict_row['inventory'] > 200.0 + 1e-4:
        bool_warehouse = False
dict_week_slack = {}
for dict_row in dict_result['targets']:
    dict_week_slack[dict_row['week']] = dict_row['slack']
check(bool_warehouse, 'eq:capacidade_armazem_turno: estoque total <= 200 kg em todo turno')
check(dict_result['kpis']['backlog_cost'] < 1e-6 and abs(dict_week_slack['2024-01-01'] - 100.0) < 1e-4
      and dict_week_slack['2024-01-08'] < 1e-4,
      f"armazem corta a meta da semana 1 em 100 kg sem atrasar carteira (folgas {dict_week_slack})")

dict_settings_two_weeks = dict(dict_base)
dict_settings_two_weeks['frozen_weeks'] = 2
dict_weekly_two = solve_weekly_model(build_weekly_scenario(dict_instance, dict_settings_two_weeks),
                                     dict_settings_two_weeks)
dict_instance['initial_color'] = {}
dict_daily_two = build_daily_scenario(dict_instance, dict_settings_two_weeks, dict_weekly_two)
bool_targets = len(dict_daily_two['weeks']) == 2
for str_product in dict_instance['products']:
    for str_week in dict_daily_two['weeks']:
        float_expected = 0.0
        if str_product == str_mts_product:
            float_expected = dict_weekly_two['targets'][str_product][str_week]
        if abs(dict_daily_two['target'][(str_product, str_week)] - float_expected) > 1e-9:
            bool_targets = False
    if dict_daily_two['last_shift_of_week'][dict_daily_two['weeks'][0]] >= dict_daily_two['last_shift_of_week'][
            dict_daily_two['weeks'][1]]:
        bool_targets = False
check(bool_targets, 'build_daily_scenario: Ihat_it = I_it semanal no balao MTS e 0 nos demais, por semana detalhada')


print('\n== sequenciamento: avaliacao e heuristica ==')


def build_sequencing_case(dict_runs, dict_form_override, dict_form_change, dict_orders_by_run, dict_initial_form,
                          dict_initial_color, float_warehouse):
    list_case_shifts = []
    for int_shift in range(4):
        list_case_shifts.append({
            'index': int_shift, 'date': pd.Timestamp('2024-01-01') + pd.Timedelta(days=int_shift // 2),
            'shift_number': int_shift % 2 + 1, 'day_index': int_shift // 2, 'week': pd.Timestamp('2024-01-01'),
        })
    dict_skus = {'A': ['A-X', 'A-Y', 'A-Z'], 'B': ['B-X']}
    dict_case_orders = {}
    dict_case_stock = {}
    for str_case_product in dict_skus:
        for str_sku in dict_skus[str_case_product]:
            dict_case_stock[str_sku] = 0.0
            for int_shift in range(4):
                dict_case_orders[(str_sku, int_shift)] = 0.0
    for tuple_key in dict_orders_by_run:
        dict_case_orders[tuple_key] = dict_orders_by_run[tuple_key]
    dict_case_scenario = {
        'shifts': list_case_shifts, 'machines': ['1', '2'], 'products': ['A', 'B'],
        'skus_of_product': dict_skus,
        'product_of_sku': {'A-X': 'A', 'A-Y': 'A', 'A-Z': 'A', 'B-X': 'B'},
        'color_of_sku': {'A-X': 'X', 'A-Y': 'Y', 'A-Z': 'Z', 'B-X': 'X'},
        'machines_of_product': {'A': ['1', '2'], 'B': ['1', '2']},
        'products_of_machine': {'1': ['A', 'B'], '2': ['A', 'B']},
        'productivity': {'A': {'1': 100.0, '2': 100.0}, 'B': {'1': 100.0, '2': 100.0}},
        'color_setup': complete_setup_matrix({('X', 'Y'): 1.0, ('Y', 'X'): 2.0, ('Y', 'Z'): 1.0, ('Z', 'Y'): 1.0},
                                             ['X', 'Y', 'Z']),
        'form_setup': {('A', 'B'): 3.0, ('B', 'A'): 5.0},
        'color_reservation': {'A-X': 2.0, 'A-Y': 1.0, 'A-Z': 2.0, 'B-X': 0.0},
        'min_lot': {'A': 50.0, 'B': 50.0}, 'shift_capacity': {}, 'color_sides': {'1': 1, '2': 1},
        'setup_hourly_cost': {'1': 100.0, '2': 100.0},
        'initial_form': dict_initial_form, 'initial_color': dict_initial_color,
        'initial_stock': dict_case_stock, 'orders': dict_case_orders, 'warehouse_capacity': float_warehouse,
        'weeks': ['2024-01-01'], 'last_shift_of_week': {'2024-01-01': 3},
        'target': {('A', '2024-01-01'): 0.0, ('B', '2024-01-01'): 0.0},
        'margin': {'A': 10.0, 'B': 10.0}, 'unit_cost': {'A': 5.0, 'B': 5.0},
    }
    dict_case_plan = {'quantity': {}, 'sequence': {}, 'form': {}, 'form_change': dict_form_change,
                      'pending': {}, 'color_hours': {}, 'previous_color': {}}
    for str_machine in ['1', '2']:
        for int_shift in range(4):
            dict_case_scenario['shift_capacity'][(str_machine, int_shift)] = 8.0
            dict_case_plan['sequence'][(str_machine, 1, int_shift)] = []
            dict_case_plan['pending'][(str_machine, int_shift)] = 0.0
            if (str_machine, int_shift) in dict_form_override:
                dict_case_plan['form'][(str_machine, int_shift)] = dict_form_override[(str_machine, int_shift)]
            else:
                dict_case_plan['form'][(str_machine, int_shift)] = 'A'
    for tuple_run in dict_runs:
        dict_case_plan['quantity'][tuple_run] = dict_runs[tuple_run]
        dict_case_plan['sequence'][(tuple_run[1], tuple_run[2], tuple_run[3])].append(tuple_run[0])
        dict_case_plan['color_hours'][tuple_run] = dict_case_scenario['color_reservation'][tuple_run[0]]
        dict_case_plan['previous_color'][tuple_run] = '-'
    dict_case_mip = {'status': 'Optimal', 'stage_objectives': [], 'stage_reports': [],
                     'kpis': {'solve_seconds': 0.0, 'hit_time_limit': False}, 'plan': dict_case_plan}
    return dict_case_scenario, dict_case_mip


def collect_runs(dict_sequenced):
    dict_runs_found = {}
    for dict_row in dict_sequenced['schedule']:
        if dict_row['sku'] != '-':
            dict_runs_found[(dict_row['sku'], dict_row['machine'], dict_row['side'], dict_row['shift_index'])] = dict_row
    return dict_runs_found


dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-X', '1', 1, 0): 100.0, ('A-Y', '1', 1, 2): 100.0}, {}, {}, {}, {}, {}, None)
dict_case_state = {'quantity': dict_case_mip['plan']['quantity'], 'sequence': dict_case_mip['plan']['sequence']}
dict_evaluation = evaluate_sequence(dict_case_scenario, dict_case_mip['plan'], dict_case_state, ['1'], True)
check(abs(dict_evaluation['run_color_hours'][('A-Y', '1', 1, 2)] - 1.0) < 1e-9
      and dict_evaluation['run_previous_color'][('A-Y', '1', 1, 2)] == 'X',
      'eq:seq_entrada: a cor X do turno 0 entra no turno 2 atraves do turno 1 ocioso (X->Y = 1h)')
check(abs(dict_evaluation['run_color_hours'][('A-X', '1', 1, 0)] - 2.0) < 1e-9
      and dict_evaluation['run_previous_color'][('A-X', '1', 1, 0)] == '0',
      'eq:seq_entrada: sem cor inicial a entrada e o SKU ficticio 0, e a primeira corrida paga a limpeza (2h)')

dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-X', '1', 1, 0): 100.0, ('A-Y', '1', 1, 2): 100.0}, {('1', 1): 'B'},
    {('1', 1): ('A', 3.0), ('1', 2): ('B', 5.0)}, {}, {}, {}, None)
dict_case_state = {'quantity': dict_case_mip['plan']['quantity'], 'sequence': dict_case_mip['plan']['sequence']}
dict_evaluation = evaluate_sequence(dict_case_scenario, dict_case_mip['plan'], dict_case_state, ['1'], True)
check(dict_evaluation['run_color_hours'][('A-Y', '1', 1, 2)] == 0.0
      and dict_evaluation['run_previous_color'][('A-Y', '1', 1, 2)] == '-',
      'eq:seq_entrada: depois de troca de forma a entrada e vazia e a primeira cor custa 0')

dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-X', '1', 1, 0): 100.0}, {}, {}, {}, {'1': 'A'}, {('1', 1): 'Y'}, None)
dict_case_state = {'quantity': dict_case_mip['plan']['quantity'], 'sequence': dict_case_mip['plan']['sequence']}
dict_evaluation = evaluate_sequence(dict_case_scenario, dict_case_mip['plan'], dict_case_state, ['1'], True)
check(abs(dict_evaluation['run_color_hours'][('A-X', '1', 1, 0)] - 2.0) < 1e-9,
      'eq:seq_entrada: no turno 0 a entrada e k0_j (cor inicial Y, Y->X = 2h)')

dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-Z', '1', 1, 0): 100.0, ('A-X', '1', 1, 0): 100.0, ('A-Y', '1', 1, 0): 100.0}, {}, {}, {}, {'1': 'A'}, {('1', 1): 'X'},
    None)
dict_case_state = {'quantity': dict_case_mip['plan']['quantity'], 'sequence': dict_case_mip['plan']['sequence']}
dict_evaluation = evaluate_sequence(dict_case_scenario, dict_case_mip['plan'], dict_case_state, ['1'], True)
check(abs(dict_evaluation['cells'][('1', 1, 0)]['color_setup_hours'] - 5.0) < 1e-9
      and dict_evaluation['violation']['seq_capacidade'] == 0.0,
      'eq:seq_capacidade: a ordem Z, X, Y do MIP paga X->Z 2h + Z->X 2h + X->Y 1h = 5h e cabe na reserva')
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
list_order = []
for dict_row in dict_sequenced['schedule']:
    if dict_row['shift_index'] == 0 and dict_row['machine'] == '1':
        list_order.append(dict_row['sku'])
check(dict_sequenced['sequencing_violations']['seq_capacidade'] == 0.0 and list_order == ['A-X', 'A-Y', 'A-Z'],
      f'eq:obj_sequenciamento: o sequenciamento ordena X, Y, Z (obtido {list_order})')
float_reserved = 0.0
for tuple_run in dict_case_mip['plan']['color_hours']:
    float_reserved += dict_case_mip['plan']['color_hours'][tuple_run]
check(abs(dict_sequenced['kpis']['color_setup_hours'] - 2.0) < 1e-9 and abs(float_reserved - 5.0) < 1e-9,
      'eq:obj_sequenciamento: troca real 2h contra reserva de 5h do MIP')
dict_cell = None
for dict_row in dict_sequenced['sequencing_report']:
    if dict_row['machine'] == '1' and dict_row['shift_index'] == 0:
        dict_cell = dict_row
check(abs(dict_cell['idle_hours'] - 3.0) < 1e-9 and dict_cell['seq_capacidade'] == 0.0,
      f"eq:seq_capacidade: 8h - 3h de producao - 2h de troca real = 3h ociosas (obtido {dict_cell['idle_hours']})")

dict_case_scenario, dict_case_mip = build_sequencing_case({('A-X', '1', 1, 0): 900.0}, {}, {}, {}, {'1': 'A'},
                                                          {('1', 1): 'X'}, None)
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
check(abs(dict_sequenced['sequencing_violations']['seq_capacidade'] - 1.0) < 1e-9,
      'eq:seq_capacidade: 900 kg em turno de 8h a 100 kg/h estoura 1h e e publicado')

dict_machine_two_b = {('2', 0): 'B', ('2', 1): 'B', ('2', 2): 'B', ('2', 3): 'B'}
dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-X', '1', 1, 0): 300.0, ('A-X', '1', 1, 2): 600.0}, dict_machine_two_b, {}, {('A-X', 3): 900.0}, {'1': 'A'}, {('1', 1): 'X'}, None)
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
dict_runs_found = collect_runs(dict_sequenced)
bool_expected = (('A-X', '1', 1, 0) in dict_runs_found and abs(dict_runs_found[('A-X', '1', 1, 0)]['kg'] - 800.0) < 1e-6
                 and ('A-X', '1', 1, 1) in dict_runs_found and abs(dict_runs_found[('A-X', '1', 1, 1)]['kg'] - 100.0) < 1e-6
                 and ('A-X', '1', 1, 2) not in dict_runs_found)
check(bool_expected, 'antecipacao: estende X no turno 0 ate encher (800 kg) e traz o resto para o turno 1 ocioso')
check(abs(dict_sequenced['kpis']['anticipated_kg'] - 600.0) < 1e-6
      and dict_sequenced['sequencing_violations']['seq_antecipacao'] == 0.0,
      'eq:seq_antecipacao: 600 kg antecipados, igualdade no ultimo turno preserva os 900 kg')
check(dict_sequenced['kpis']['backlog_cost'] == 0.0 and dict_sequenced['sequencing_violations']['seq_lote'] == 0.0,
      'eq:seq_lote: toda corrida resultante tem ao menos o lote minimo; carteira atendida')

dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-X', '1', 1, 0): 300.0, ('A-X', '1', 1, 2): 600.0}, dict_machine_two_b, {},
    {('A-X', 0): 300.0, ('A-X', 2): 600.0}, {'1': 'A'}, {('1', 1): 'X'}, None)
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
float_free_anticipated = dict_sequenced['kpis']['anticipated_kg']
dict_case_scenario['warehouse_capacity'] = 400.0
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
float_peak = 0.0
for dict_row in dict_sequenced['orders']:
    if dict_row['inventory'] > float_peak:
        float_peak = dict_row['inventory']
check(float_free_anticipated > 0.0 and dict_sequenced['sequencing_violations']['seq_armazem'] == 0.0
      and float_peak <= 400.0 + 1e-6 and dict_sequenced['kpis']['anticipated_kg'] == 0.0,
      f'eq:seq_armazem: sem limite antecipa {float_free_anticipated:.0f} kg; com Omega = 400 kg nada '
      f'que estoure o armazem e antecipado (pico {float_peak:.0f} kg)')

dict_form_gap = dict(dict_machine_two_b)
dict_form_gap[('1', 1)] = 'B'
dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('A-X', '1', 1, 0): 300.0, ('A-X', '1', 1, 2): 100.0, ('A-Y', '1', 1, 3): 100.0}, dict_form_gap,
    {('1', 1): ('A', 3.0), ('1', 2): ('B', 5.0)}, {}, {'1': 'A'}, {('1', 1): 'X'}, None)
dict_case_state = {'quantity': dict_case_mip['plan']['quantity'], 'sequence': dict_case_mip['plan']['sequence']}
float_initial_setup = evaluate_sequence(dict_case_scenario, dict_case_mip['plan'], dict_case_state,
                                        ['1', '2'], True)['setup_cost']
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
dict_runs_found = collect_runs(dict_sequenced)
check(('A-Y', '1', 1, 0) not in dict_runs_found and abs(float_initial_setup - 100.0) < 1e-6
      and dict_sequenced['kpis']['color_setup_hours'] == 0.0,
      'eq:obj_sequenciamento: X vai para o turno 0 e Y nao, porque pagaria X->Y; Y fica depois da '
      'troca de forma, sem custo de cor (R$100 -> R$0)')

dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('B-X', '2', 1, 2): 100.0, ('A-X', '2', 1, 3): 100.0}, {('2', 0): 'B', ('2', 1): 'B', ('2', 2): 'B'},
    {('2', 3): ('B', 5.0)}, {}, {'1': 'A'}, {('1', 1): 'X'}, None)
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
dict_runs_found = collect_runs(dict_sequenced)
bool_b_on_one = False
for tuple_run in dict_runs_found:
    if tuple_run[0] == 'B-X' and tuple_run[1] == '1':
        bool_b_on_one = True
check(not bool_b_on_one and dict_sequenced['sequencing_violations']['seq_forma'] == 0.0,
      'eq:seq_forma: B nao vai para a maquina 1, que tem a forma A montada')
check(('A-X', '1', 1, 0) in dict_runs_found and ('A-X', '2', 1, 3) not in dict_runs_found,
      'eq:seq_forma: A sai da maquina 2 no turno 3 para a maquina 1 no turno 0, com a forma A montada')

dict_case_scenario, dict_case_mip = build_sequencing_case(
    {('B-X', '1', 1, 3): 100.0}, {('1', 1): 'B', ('1', 2): 'B', ('1', 3): 'B'}, {('1', 1): ('A', 10.0)}, {},
    {'1': 'A'}, {('1', 1): 'X'}, None)
dict_case_mip['plan']['pending'][('1', 1)] = 2.0
dict_sequenced = sequence_daily_plan(dict_case_scenario, {'annual_holding_rate': 0.25}, dict_case_mip)
dict_runs_found = collect_runs(dict_sequenced)
dict_form_by_shift = {}
for dict_row in dict_sequenced['sequencing_report']:
    if dict_row['machine'] == '1':
        dict_form_by_shift[dict_row['shift_index']] = dict_row['form_setup_hours']
check(('B-X', '1', 1, 1) not in dict_runs_found and ('B-X', '1', 1, 2) in dict_runs_found
      and dict_sequenced['sequencing_violations']['seq_forma'] == 0.0
      and dict_sequenced['sequencing_violations']['seq_capacidade'] == 0.0,
      'eq:seq_forma: B nao vai para o turno 1, com troca pendente, e sim para o turno 2, onde a troca termina')
check(abs(dict_form_by_shift[1] - 8.0) < 1e-9 and abs(dict_form_by_shift[2] - 2.0) < 1e-9,
      'eq:seq_capacidade: a troca de 10h executa 8h no turno 1 e 2h no turno 2')

dict_sequenced = sequence_daily_plan(dict_reservation_scenario, dict_settings, dict_reservation_mip)
float_total_violation = 0.0
for str_name in dict_sequenced['sequencing_violations']:
    float_total_violation += dict_sequenced['sequencing_violations'][str_name]
check(float_total_violation < 1e-6, f"MIP + sequenciamento: nenhuma violacao ({dict_sequenced['sequencing_violations']})")
check(dict_sequenced['kpis']['color_setup_hours'] <= dict_reservation_mip['kpis']['color_setup_hours'] + 1e-9
      and dict_sequenced['kpis']['order_service_level'] >= dict_reservation_mip['kpis']['order_service_level'] - 1e-9,
      f"troca real {dict_sequenced['kpis']['color_setup_hours']:.1f}h <= reserva "
      f"{dict_reservation_mip['kpis']['color_setup_hours']:.1f}h, atendimento mantido")


print('\n== maquina de duas cores ==')
str_d = 'D-L'
list_two_color_skus = [f'{str_d}-X', f'{str_d}-Y']
dict_two_color_scenario = {
    'shifts': list_shifts, 'machines': ['1'], 'products': [str_d],
    'skus_of_product': {str_d: list_two_color_skus},
    'product_of_sku': {f'{str_d}-X': str_d, f'{str_d}-Y': str_d},
    'color_of_sku': {f'{str_d}-X': 'X', f'{str_d}-Y': 'Y'},
    'machines_of_product': {str_d: ['1']}, 'products_of_machine': {'1': [str_d]},
    'shift_capacity': {('1', 0): 8.0, ('1', 1): 8.0, ('1', 2): 8.0, ('1', 3): 8.0}, 'color_sides': {'1': 2},
    'productivity': {str_d: {'1': 100.0}},
    'form_setup': {(str_d, str_d): 0.0}, 'color_setup': complete_setup_matrix({('X', 'Y'): 1.0, ('Y', 'X'): 1.0},
                                                                              ['X', 'Y']),
    'color_reservation': {f'{str_d}-X': 1.0, f'{str_d}-Y': 1.0},
    'initial_form': {'1': str_d}, 'initial_color': {('1', 1): 'X', ('1', 2): 'Y'},
    'initial_stock': {f'{str_d}-X': 0.0, f'{str_d}-Y': 0.0},
    'target': {(str_d, '2024-01-01'): 0.0}, 'min_lot': {str_d: 50.0},
    'unit_cost': {str_d: 5.0}, 'margin': {str_d: 10.0},
    'setup_hourly_cost': {'1': 100.0}, 'weeks': ['2024-01-01'], 'last_shift_of_week': {'2024-01-01': 3},
    'warehouse_capacity': None,
}
dict_two_color_orders = {}
for str_sku in list_two_color_skus:
    for int_shift in range(4):
        dict_two_color_orders[(str_sku, int_shift)] = 0.0
dict_two_color_orders[(f'{str_d}-X', 0)] = 700.0
dict_two_color_orders[(f'{str_d}-Y', 0)] = 700.0
dict_two_color_scenario['orders'] = dict_two_color_orders
dict_result = solve_daily_model(dict_two_color_scenario, dict_settings)
dict_sides_used = {}
for dict_row in dict_result['schedule']:
    if dict_row['shift_index'] == 0 and dict_row['kg'] > 0.0:
        dict_sides_used[dict_row['side']] = dict_row['sku']
check(dict_result['status'] == 'Optimal' and dict_result['kpis']['backlog_cost'] < 1e-6
      and len(dict_sides_used) == 2 and dict_sides_used[1] != dict_sides_used[2],
      f'duas cores no mesmo turno, uma por lado, cada uma a 100 kg/h: 2 x 700 kg em 8h (lados {dict_sides_used})')
check(abs(dict_result['kpis']['color_setup_hours'] - 2.0) < 1e-6,
      'eq:capacidade_turno: a reserva de cor de 1h de cada lado consome so o seu lado (7h + 1h = 8h por lado)')

dict_two_color_scenario['color_sides'] = {'1': 1}
dict_two_color_scenario['initial_color'] = {('1', 1): 'X'}
dict_result_one_side = solve_daily_model(dict_two_color_scenario, dict_settings)
check(dict_result_one_side['kpis']['backlog_cost'] > 1.0,
      'a mesma carteira atrasa na maquina de uma cor, que tem um tanque so')

dict_two_color_scenario['color_sides'] = {'1': 2}
dict_two_color_scenario['initial_color'] = {('1', 1): 'X', ('1', 2): 'Y'}
dict_sequenced = sequence_daily_plan(dict_two_color_scenario, dict_settings, dict_result)
float_total_violation = 0.0
for str_name in dict_sequenced['sequencing_violations']:
    float_total_violation += dict_sequenced['sequencing_violations'][str_name]
check(float_total_violation < 1e-6 and dict_sequenced['kpis']['color_setup_hours'] <= 2.0 + 1e-6,
      f"sequenciamento por lado sem violacao, troca real {dict_sequenced['kpis']['color_setup_hours']:.1f}h "
      f"<= reserva de 2h")

str_e = 'E-L'
dict_two_color_scenario['products'] = [str_d, str_e]
dict_two_color_scenario['skus_of_product'] = {str_d: list_two_color_skus, str_e: [f'{str_e}-X']}
dict_two_color_scenario['product_of_sku'][f'{str_e}-X'] = str_e
dict_two_color_scenario['color_of_sku'][f'{str_e}-X'] = 'X'
dict_two_color_scenario['machines_of_product'] = {str_d: ['1'], str_e: ['1']}
dict_two_color_scenario['products_of_machine'] = {'1': [str_d, str_e]}
dict_two_color_scenario['productivity'][str_e] = {'1': 100.0}
dict_two_color_scenario['form_setup'] = {(str_d, str_d): 0.0, (str_e, str_e): 0.0, (str_e, str_d): 2.0,
                                         (str_d, str_e): 2.0}
dict_two_color_scenario['color_reservation'] = {f'{str_d}-X': 0.0, f'{str_d}-Y': 0.0, f'{str_e}-X': 0.0}
dict_two_color_scenario['initial_form'] = {'1': str_e}
dict_two_color_scenario['initial_stock'][f'{str_e}-X'] = 0.0
dict_two_color_scenario['target'][(str_e, '2024-01-01')] = 0.0
dict_two_color_scenario['min_lot'][str_e] = 50.0
dict_two_color_scenario['unit_cost'][str_e] = 5.0
dict_two_color_scenario['margin'][str_e] = 10.0
for int_shift in range(4):
    dict_two_color_orders[(f'{str_e}-X', int_shift)] = 0.0
dict_two_color_orders[(f'{str_d}-X', 0)] = 600.0
dict_two_color_orders[(f'{str_d}-Y', 0)] = 600.0
dict_result = solve_daily_model(dict_two_color_scenario, dict_settings)
check(dict_result['kpis']['backlog_cost'] < 1e-6 and abs(dict_result['kpis']['form_setup_hours'] - 2.0) < 1e-6,
      'troca de forma E->D de 2h uma vez para a maquina; 2h + 6h de producao cabem em cada lado')
dict_two_color_orders[(f'{str_d}-Y', 0)] = 800.0
dict_result = solve_daily_model(dict_two_color_scenario, dict_settings)
check(dict_result['kpis']['backlog_cost'] > 1.0,
      'eq:capacidade_turno: a troca de forma para os dois lados, e o lado Y nao faz 800 kg no turno 0')


print('\n== modelo semanal: maquina de duas cores ==')
dict_instance_two = load_instance(os.path.join(DATA_DIR, 'instance_micro_P2_M3_T8.xlsx'))
dict_settings = dict(dict_base)
dict_settings['hours_per_shift'] = 1.0
for str_machine in dict_instance_two['color_sides']:
    dict_instance_two['color_sides'][str_machine] = 1
dict_scenario = build_weekly_scenario(dict_instance_two, dict_settings)
dict_result_one = solve_weekly_model(dict_scenario, dict_settings)
for str_machine in dict_instance_two['color_sides']:
    dict_instance_two['color_sides'][str_machine] = 2
dict_scenario_two = build_weekly_scenario(dict_instance_two, dict_settings)
dict_result_two = solve_weekly_model(dict_scenario_two, dict_settings)
bool_double = True
for str_machine in dict_scenario['machines']:
    for timestamp_week in dict_scenario['weeks']:
        if abs(dict_scenario_two['capacity'][str_machine][timestamp_week]
               - 2.0 * dict_scenario['capacity'][str_machine][timestamp_week]) > 1e-9:
            bool_double = False
check(bool_double, 'eq:capacidade_semanal: dois lados dobram as horas-lado da maquina')
bool_form_twice = True
for tuple_pair in dict_scenario_two['side_setup']:
    str_product = tuple_pair[0]
    float_form = dict_scenario_two['side_setup'][tuple_pair] - dict_scenario['side_setup'][tuple_pair]
    float_expected = 0.0
    for str_other in dict_instance_two['products']:
        float_expected += dict_instance_two['form_setup'][(str_other, str_product)]
    float_expected = float_expected / len(dict_instance_two['products'])
    if abs(float_form - float_expected) > 1e-9:
        bool_form_twice = False
check(bool_form_twice, 'eq:capacidade_semanal: a troca de forma consome os dois lados, a de cor so um')
float_short_one = dict_result_one['kpis']['backlog_cost'] + dict_result_one['kpis']['lost_sales_cost']
float_short_two = dict_result_two['kpis']['backlog_cost'] + dict_result_two['kpis']['lost_sales_cost']
check(float_short_two < float_short_one,
      f'com 1 h/turno, duas cores reduzem atraso + venda perdida de {float_short_one:,.0f} para {float_short_two:,.0f}')


print('\n== relax-and-fix + fix-and-optimize: tempo, maquina e produto ==')
dict_instance_rf = load_instance(os.path.join(DATA_DIR, 'instance_micro_P2_M3_T8.xlsx'))
dict_settings_pure = dict(dict_base)
dict_settings_pure['hours_per_shift'] = 1.0
dict_settings_pure['weekly_solver_name'] = 'GUROBI'
dict_settings_pure['daily_solver_name'] = 'GUROBI'
dict_settings_pure['weekly_time_limit'] = 60
dict_settings_pure['daily_time_limit'] = 60
dict_settings_pure['threads'] = 2
dict_settings_pure['decomposition'] = None
dict_settings_pure['weekly_block_size'] = 1
dict_settings_pure['daily_block_size'] = 1
dict_settings_pure['fo_time_share'] = 0.3
dict_weekly_scenario_rf = build_weekly_scenario(dict_instance_rf, dict_settings_pure)
dict_weekly_pure = solve_weekly_model(dict_weekly_scenario_rf, dict_settings_pure)
for str_decomposition in ['tempo', 'maquina', 'produto']:
    dict_settings = dict(dict_settings_pure)
    dict_settings['decomposition'] = str_decomposition
    dict_result = solve_weekly_model(dict_weekly_scenario_rf, dict_settings)
    dict_kpis = dict_result['kpis']
    list_stages = dict_result['stage_objectives']
    check(dict_result['status'] in ('Optimal', 'Feasible') and len(list_stages) == 4,
          f'{str_decomposition} semanal: quatro estagios com solucao ({dict_result["status"]})')
    float_sum = (dict_kpis['backlog_cost'] + dict_kpis['lost_sales_cost'] + dict_kpis['floor_slack_cost']
                 + dict_kpis['setup_cost'] + dict_kpis['holding_cost'])
    check(abs(float_sum - dict_kpis['total_cost']) < 1e-6
          and dict_kpis['backlog_cost'] <= list_stages[0] + 1e-6
          and dict_kpis['lost_sales_cost'] <= list_stages[1] + 1e-6
          and dict_kpis['floor_slack_cost'] <= list_stages[2] + 1e-6,
          f'{str_decomposition} semanal: KPIs somam o total e respeitam as travas dos estagios')
    check(list_stages[0] >= dict_weekly_pure['stage_objectives'][0] - 1e-6,
          f'{str_decomposition} semanal: estagio 1 nao fica abaixo do otimo da formulacao '
          f'({list_stages[0]:,.1f} >= {dict_weekly_pure["stage_objectives"][0]:,.1f})')
    bool_reports = True
    for dict_report in dict_result['stage_reports']:
        if dict_report['bound'] > dict_report['objective'] + 1e-6 * (1.0 + abs(dict_report['objective'])):
            bool_reports = False
        if 'subproblems' not in dict_report or dict_report['rf_seconds'] < 0.0 or dict_report['fo_seconds'] < 0.0:
            bool_reports = False
        if dict_report['binaries'] != dict_weekly_pure['stage_reports'][0]['binaries']:
            bool_reports = False
    check(bool_reports, f'{str_decomposition} semanal: limitante da relaxacao <= objetivo, binarias do modelo cheio')

    bool_balance = True
    for str_product in dict_weekly_scenario_rf['products']:
        float_previous = dict_weekly_scenario_rf['initial_inventory'][str_product]
        for str_week in dict_result['weeks']:
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
    bool_capacity = True
    for str_machine in dict_weekly_scenario_rf['machines']:
        for timestamp_week in dict_weekly_scenario_rf['weeks']:
            float_used = 0.0
            for dict_row in dict_result['production']:
                if dict_row['machine'] == str_machine and dict_row['week'] == timestamp_week.strftime('%Y-%m-%d'):
                    float_used += dict_row['hours'] + dict_row['setup_hours']
            if float_used > dict_weekly_scenario_rf['capacity'][str_machine][timestamp_week] + 1e-3:
                bool_capacity = False
    bool_lots = True
    for dict_row in dict_result['production']:
        if dict_row['kg'] < dict_weekly_scenario_rf['min_lot'][dict_row['product']] - 1e-4:
            bool_lots = False
        if abs(dict_row['setup_hours']
               - dict_weekly_scenario_rf['side_setup'][(dict_row['product'], dict_row['machine'])]) > 1e-6:
            bool_lots = False
    check(bool_balance and bool_capacity and bool_lots,
          f'{str_decomposition} semanal: balanco, capacidade, lote minimo e setup inteiro no plano final')

    dict_daily_scenario_rf = build_daily_scenario(dict_instance_rf, dict_settings, dict_result)
    dict_daily_pure = solve_daily_model(dict_daily_scenario_rf, dict_settings_pure)
    dict_daily = solve_daily_model(dict_daily_scenario_rf, dict_settings)
    dict_kpis = dict_daily['kpis']
    list_stages = dict_daily['stage_objectives']
    check(dict_daily['status'] in ('Optimal', 'Feasible') and len(list_stages) == 3,
          f'{str_decomposition} diario: tres estagios com solucao ({dict_daily["status"]})')
    check(abs(dict_kpis['backlog_cost'] + dict_kpis['target_slack_cost'] + dict_kpis['setup_cost']
              + dict_kpis['holding_cost'] - dict_kpis['total_cost']) < 1e-6
          and dict_kpis['backlog_cost'] <= list_stages[0] + 1e-4
          and dict_kpis['target_slack_cost'] <= list_stages[1] + 1e-4
          and list_stages[0] >= dict_daily_pure['stage_objectives'][0] - 1e-6,
          f'{str_decomposition} diario: KPIs somam o total, respeitam as travas e o estagio 1 nao bate o otimo')
    bool_capacity = True
    bool_lots = True
    dict_used = {}
    for dict_row in dict_daily['schedule']:
        tuple_cell = (dict_row['machine'], dict_row['side'], dict_row['shift_index'])
        if tuple_cell not in dict_used:
            dict_used[tuple_cell] = 0.0
        dict_used[tuple_cell] += (dict_row['production_hours'] + dict_row['color_setup_hours']
                                  + dict_row['form_setup_hours'])
        if dict_row['sku'] != '-' and dict_row['kg'] < dict_daily_scenario_rf['min_lot'][dict_row['product']] - 1e-4:
            bool_lots = False
    for tuple_cell in dict_used:
        if dict_used[tuple_cell] > dict_daily_scenario_rf['shift_capacity'][(tuple_cell[0], tuple_cell[2])] + 1e-4:
            bool_capacity = False
    dict_sequenced = sequence_daily_plan(dict_daily_scenario_rf, dict_settings, dict_daily)
    float_total_violation = 0.0
    for str_name in dict_sequenced['sequencing_violations']:
        float_total_violation += dict_sequenced['sequencing_violations'][str_name]
    check(bool_capacity and bool_lots and float_total_violation < 1e-6,
          f'{str_decomposition} diario: capacidade por lado e turno, lote minimo e sequenciamento sem violacao')


print('\n' + '=' * 60)
if len(list_failures) == 0:
    print('TODOS OS TESTES PASSARAM')
else:
    print(f'{len(list_failures)} FALHA(S):')
    for str_message in list_failures:
        print(f'  - {str_message}')
    sys.exit(1)
