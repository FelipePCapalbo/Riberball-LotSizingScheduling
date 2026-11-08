import argparse
import copy
import csv
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime

import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from processing.data import load_instance
from processing.settings import DEFAULT_SETTINGS
from optimization.planner import run_weekly_plan, run_daily_plan

BASELINE_FILE = os.path.join(ROOT_DIR, 'data', 'input_asis_ajustado.xlsx')
DEFAULT_OUTPUT_ROOT = os.path.join(ROOT_DIR, 'experimentos', 'esforco_computacional')

SETTINGS_OVERRIDES = {
    'start_week': '2024-01-01',
    'weeks_in_plan': 13,
    'frozen_weeks': 1,
    'shifts_per_day': 3,
    'hours_per_shift': 8,
    'working_days_per_week': 7,
    'warehouse_capacity_kg': None,
    'annual_holding_rate': 0.25,
    'weekly_solver_name': 'GUROBI',
    'weekly_time_limit': 300,
    'daily_solver_name': 'GUROBI',
    'daily_time_limit': 600,
    'threads': 2,
    'solver_seed': 0,
}
QUICK_TIME_LIMIT = 30

FACTORS = [
    {'name': 'maquinas', 'levels': [1, 2, 4, 7, 10, 14, 20, 28], 'baseline': 28, 'draws': True},
    {'name': 'baloes', 'levels': [1, 2, 4, 6, 9, 12, 15, 17], 'baseline': 17, 'draws': True},
    {'name': 'cores', 'levels': [1, 2, 3, 4, 5, 7], 'baseline': 7, 'draws': False},
    {'name': 'flexibilidade', 'levels': [0.25, 0.5, 0.75, 1.0, 1.5, 2.0], 'baseline': 1.0, 'draws': True},
    {'name': 'demanda', 'levels': [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0], 'baseline': 1.0, 'draws': False},
    {'name': 'estoque', 'levels': [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0], 'baseline': 1.0, 'draws': False},
    {'name': 'capacidade', 'levels': [0.5, 0.75, 1.0, 1.25, 1.5], 'baseline': 1.0, 'draws': False},
    {'name': 'setup', 'levels': [0.0, 0.5, 1.0, 1.5, 2.0, 3.0], 'baseline': 1.0, 'draws': False},
    {'name': 'duas_cores', 'levels': [0.0, 0.25, 0.5, 0.75, 1.0], 'baseline': 0.25, 'draws': True},
    {'name': 'horizonte', 'levels': [4, 8, 13, 26, 52], 'baseline': 13, 'draws': False},
    {'name': 'congeladas', 'levels': [1, 2], 'baseline': 1, 'draws': False},
]
DRAW_FREE_LEVELS = [['duas_cores', 0.0], ['duas_cores', 1.0]]
DRAW_SEEDS = [1, 2, 3]
BASELINE_SOLVER_SEEDS = [0, 1, 2, 3, 4]
GRID_DRAW = 1
GRIDS = [
    [['maquinas', [4, 10, 20, 28]], ['demanda', [0.5, 1.0, 1.5, 2.0]]],
    [['cores', [1, 3, 5, 7]], ['setup', [0.5, 1.0, 2.0, 3.0]]],
    [['estoque', [0.0, 0.5, 1.0, 2.0]], ['demanda', [0.5, 1.0, 1.5, 2.0]]],
]

LEVEL_COLUMNS = ['status', 'segundos', 'work', 'nos', 'iteracoes', 'variaveis', 'binarias', 'restricoes',
                 'nao_zeros', 'gap_max', 'bateu_limite', 'objetivos', 'limitantes', 'gaps', 'custo_total']


def format_level(value_level):
    return f'{value_level:g}'.replace('.', 'p')


def summarize_level(dict_result):
    dict_summary = {}
    for str_column in LEVEL_COLUMNS:
        dict_summary[str_column] = None
    dict_summary['status'] = dict_result['status']
    float_seconds = 0.0
    float_work = 0.0
    float_nodes = 0.0
    float_iterations = 0.0
    float_max_gap = None
    list_objectives = []
    list_bounds = []
    list_gaps = []
    for dict_report in dict_result['stage_reports']:
        float_seconds += dict_report['seconds']
        if dict_report['work'] is not None:
            float_work += dict_report['work']
            float_nodes += dict_report['nodes']
            float_iterations += dict_report['simplex_iterations']
        if dict_report['gap'] is not None:
            if float_max_gap is None or dict_report['gap'] > float_max_gap:
                float_max_gap = dict_report['gap']
        list_objectives.append(str(dict_report['objective']))
        list_bounds.append(str(dict_report['bound']))
        list_gaps.append(str(dict_report['gap']))
    if len(dict_result['stage_reports']) > 0:
        dict_first_report = dict_result['stage_reports'][0]
        dict_summary['variaveis'] = dict_first_report['variables']
        dict_summary['binarias'] = dict_first_report['binaries']
        dict_summary['restricoes'] = dict_first_report['constraints']
        dict_summary['nao_zeros'] = dict_first_report['nonzeros']
    dict_summary['segundos'] = float_seconds
    dict_summary['work'] = float_work
    dict_summary['nos'] = float_nodes
    dict_summary['iteracoes'] = float_iterations
    dict_summary['gap_max'] = float_max_gap
    dict_summary['objetivos'] = '|'.join(list_objectives)
    dict_summary['limitantes'] = '|'.join(list_bounds)
    dict_summary['gaps'] = '|'.join(list_gaps)
    if 'hit_time_limit' in dict_result['kpis']:
        dict_summary['bateu_limite'] = dict_result['kpis']['hit_time_limit']
    if 'total_cost' in dict_result['kpis']:
        dict_summary['custo_total'] = dict_result['kpis']['total_cost']
    return dict_summary


parser = argparse.ArgumentParser()
parser.add_argument('--variante', required=True)
parser.add_argument('--saida', default=DEFAULT_OUTPUT_ROOT)
parser.add_argument('--pasta', default=None)
parser.add_argument('--rapido', action='store_true')
parser.add_argument('--threads', type=int, default=SETTINGS_OVERRIDES['threads'])
dict_arguments = vars(parser.parse_args())

str_variant = dict_arguments['variante']
str_output_root = os.path.abspath(dict_arguments['saida'])
bool_quick = dict_arguments['rapido']
str_machine_label = os.environ.get('EXPERIMENT_MACHINE_LABEL', platform.node()).lower().replace(' ', '-')
str_started_at = datetime.now().strftime('%Y-%m-%d_%H%M%S')
if dict_arguments['pasta'] is not None:
    str_variant_directory = os.path.abspath(dict_arguments['pasta'])
else:
    str_folder_name = f'{str_started_at}_{str_machine_label}_{str_variant}'
    if bool_quick:
        str_folder_name = f'{str_folder_name}_rapido'
    str_variant_directory = os.path.join(str_output_root, 'rodadas', str_folder_name)
str_runs_directory = os.path.join(str_variant_directory, 'execucoes')
str_logs_directory = os.path.join(str_variant_directory, 'logs')
os.makedirs(str_runs_directory, exist_ok=True)
os.makedirs(str_logs_directory, exist_ok=True)

dict_base_settings = dict(DEFAULT_SETTINGS)
for str_key in SETTINGS_OVERRIDES:
    dict_base_settings[str_key] = SETTINGS_OVERRIDES[str_key]
dict_base_settings['threads'] = dict_arguments['threads']
if bool_quick:
    dict_base_settings['weekly_time_limit'] = QUICK_TIME_LIMIT
    dict_base_settings['daily_time_limit'] = QUICK_TIME_LIMIT

dict_plan = {'instancia_base': os.path.relpath(BASELINE_FILE, ROOT_DIR), 'parametros': SETTINGS_OVERRIDES,
             'fatores': FACTORS, 'niveis_sem_sorteio': DRAW_FREE_LEVELS, 'sorteios': DRAW_SEEDS,
             'sementes_solver_base': BASELINE_SOLVER_SEEDS, 'sorteio_grades': GRID_DRAW, 'grades': GRIDS}
with open(os.path.join(str_output_root, 'plano.json'), 'w', encoding='utf-8') as file_plan:
    json.dump(dict_plan, file_plan, indent=2, ensure_ascii=False)
with open(os.path.join(str_variant_directory, 'plano.json'), 'w', encoding='utf-8') as file_plan:
    json.dump(dict_plan, file_plan, indent=2, ensure_ascii=False)

str_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT_DIR, capture_output=True,
                            text=True).stdout.strip()
str_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT_DIR, capture_output=True,
                            text=True).stdout.strip()
str_dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT_DIR,
                           capture_output=True, text=True).stdout.strip()
str_cpu = platform.processor()
if os.path.exists('/proc/cpuinfo'):
    with open('/proc/cpuinfo', encoding='utf-8') as file_cpu:
        for str_line in file_cpu:
            if str_line.startswith('model name'):
                str_cpu = str_line.split(':', 1)[1].strip()
float_memory_gb = None
if os.path.exists('/proc/meminfo'):
    with open('/proc/meminfo', encoding='utf-8') as file_memory:
        for str_line in file_memory:
            if str_line.startswith('MemTotal'):
                float_memory_gb = round(float(str_line.split()[1]) / 1024.0 / 1024.0, 1)
dict_packages = {}
for str_package in ['numpy', 'pandas', 'pulp', 'ortools', 'gurobipy', 'numba']:
    dict_packages[str_package] = None
    for distribution in importlib.metadata.distributions():
        if distribution.metadata['Name'] is not None and distribution.metadata['Name'].lower() == str_package:
            dict_packages[str_package] = distribution.version

str_environment_path = os.path.join(str_variant_directory, 'ambiente.json')
dict_environment = {}
if os.path.exists(str_environment_path):
    with open(str_environment_path, encoding='utf-8') as file_environment:
        dict_environment = json.load(file_environment)
if 'inicio' not in dict_environment:
    dict_environment = {
        'variante': str_variant,
        'rapido': bool_quick,
        'maquina': str_machine_label,
        'hostname': platform.node(),
        'cpu': str_cpu,
        'nucleos': os.cpu_count(),
        'memoria_gb': float_memory_gb,
        'sistema': platform.platform(),
        'python': platform.python_version(),
        'pacotes': dict_packages,
        'pasta_codigo': ROOT_DIR,
        'branch': str_branch,
        'commit': str_commit,
        'alteracoes_nao_commitadas': str_dirty,
        'threads': dict_base_settings['threads'],
        'limite_semanal': dict_base_settings['weekly_time_limit'],
        'limite_diario': dict_base_settings['daily_time_limit'],
        'inicio': datetime.now().isoformat(timespec='seconds'),
        'retomadas': [],
    }
else:
    dict_environment['retomadas'].append({'inicio': datetime.now().isoformat(timespec='seconds'),
                                          'commit': str_commit, 'alteracoes_nao_commitadas': str_dirty})
dict_environment['pid'] = os.getpid()
dict_environment['situacao'] = 'em_execucao'

list_runs = []
for int_solver_seed in BASELINE_SOLVER_SEEDS:
    list_runs.append({'id': f'base_semente{int_solver_seed}', 'phase': 'base', 'changes': [], 'draw': 0,
                      'solver_seed': int_solver_seed})
for dict_factor in FACTORS:
    for value_level in dict_factor['levels']:
        if value_level != dict_factor['baseline']:
            bool_draw_free = [dict_factor['name'], value_level] in DRAW_FREE_LEVELS
            if dict_factor['draws'] and not bool_draw_free:
                for int_draw in DRAW_SEEDS:
                    list_runs.append({'id': f"ofat_{dict_factor['name']}_{format_level(value_level)}_s{int_draw}",
                                      'phase': 'ofat', 'changes': [[dict_factor['name'], value_level]],
                                      'draw': int_draw, 'solver_seed': 0})
            else:
                list_runs.append({'id': f"ofat_{dict_factor['name']}_{format_level(value_level)}",
                                  'phase': 'ofat', 'changes': [[dict_factor['name'], value_level]],
                                  'draw': 1, 'solver_seed': 0})
for list_grid in GRIDS:
    str_factor_a = list_grid[0][0]
    str_factor_b = list_grid[1][0]
    for value_level_a in list_grid[0][1]:
        for value_level_b in list_grid[1][1]:
            list_runs.append({'id': f'grade_{str_factor_a}_{str_factor_b}_{format_level(value_level_a)}_'
                                    f'{format_level(value_level_b)}',
                              'phase': 'grade', 'changes': [[str_factor_a, value_level_a],
                                                            [str_factor_b, value_level_b]],
                              'draw': GRID_DRAW, 'solver_seed': 0})

if bool_quick:
    list_quick_runs = [list_runs[0]]
    list_seen_factors = []
    for dict_run in list_runs:
        if dict_run['phase'] == 'ofat' and dict_run['changes'][0][0] not in list_seen_factors:
            list_seen_factors.append(dict_run['changes'][0][0])
            list_quick_runs.append(dict_run)
    list_runs = list_quick_runs

dict_environment['execucoes_planejadas'] = len(list_runs)
with open(str_environment_path, 'w', encoding='utf-8') as file_environment:
    json.dump(dict_environment, file_environment, indent=2, ensure_ascii=False)

dict_baseline_instance = load_instance(BASELINE_FILE)
str_battery_log = os.path.join(str_variant_directory, 'bateria.log')
with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
    file_battery.write(f'{datetime.now().isoformat(timespec="seconds")} inicio variante={str_variant} '
                       f'execucoes={len(list_runs)} commit={str_commit}\n')

int_run_number = 0
for dict_run in list_runs:
    int_run_number += 1
    str_run_path = os.path.join(str_runs_directory, f"{dict_run['id']}.json")
    if os.path.exists(str_run_path):
        print(f"[{int_run_number}/{len(list_runs)}] {dict_run['id']}: ja executada")
    else:
        dict_instance = copy.deepcopy(dict_baseline_instance)
        dict_settings = dict(dict_base_settings)
        dict_settings['solver_seed'] = dict_run['solver_seed']
        str_log_path = os.path.join(str_logs_directory, f"{dict_run['id']}.log")
        if os.path.exists(str_log_path):
            os.remove(str_log_path)
        dict_settings['solver_log_file'] = str_log_path

        for list_change in dict_run['changes']:
            str_factor = list_change[0]
            value_level = list_change[1]
            rng = np.random.default_rng(1000 + dict_run['draw'])

            if str_factor == 'maquinas':
                array_order = rng.permutation(len(dict_instance['machines']))
                list_kept = []
                for int_position in range(value_level):
                    list_kept.append(dict_instance['machines'][int(array_order[int_position])])
                list_machines = []
                for str_machine in dict_instance['machines']:
                    if str_machine in list_kept:
                        list_machines.append(str_machine)
                dict_instance['machines'] = list_machines

            elif str_factor == 'baloes':
                array_order = rng.permutation(len(dict_instance['products']))
                list_kept = []
                for int_position in range(value_level):
                    list_kept.append(dict_instance['products'][int(array_order[int_position])])
                list_products = []
                for str_product in dict_instance['products']:
                    if str_product in list_kept:
                        list_products.append(str_product)
                dict_instance['products'] = list_products
                list_orders = []
                for dict_order in dict_instance['orders']:
                    list_items = []
                    for dict_item in dict_order['items']:
                        if dict_item['product'] in list_kept:
                            list_items.append(dict_item)
                    if len(list_items) > 0:
                        dict_order['items'] = list_items
                        list_orders.append(dict_order)
                dict_instance['orders'] = list_orders
                dict_form_setup = {}
                for tuple_pair in dict_instance['form_setup']:
                    if tuple_pair[0] in list_kept and tuple_pair[1] in list_kept:
                        dict_form_setup[tuple_pair] = dict_instance['form_setup'][tuple_pair]
                dict_instance['form_setup'] = dict_form_setup
                dict_initial_form = {}
                for str_machine in dict_instance['initial_form']:
                    if dict_instance['initial_form'][str_machine] in list_kept:
                        dict_initial_form[str_machine] = dict_instance['initial_form'][str_machine]
                dict_instance['initial_form'] = dict_initial_form

            elif str_factor == 'cores':
                for str_product in dict_instance['products']:
                    dict_share = {}
                    for str_color in dict_instance['colors_by_product'][str_product]:
                        dict_share[str_color] = 0.0
                        if str_color in dict_instance['color_mix'][str_product]:
                            dict_share[str_color] = dict_instance['color_mix'][str_product][str_color]
                    list_ranked = []
                    list_remaining = list(dict_instance['colors_by_product'][str_product])
                    while len(list_remaining) > 0:
                        str_best = list_remaining[0]
                        for str_color in list_remaining:
                            if dict_share[str_color] > dict_share[str_best]:
                                str_best = str_color
                        list_ranked.append(str_best)
                        list_remaining.remove(str_best)
                    list_kept = list_ranked[:value_level]
                    str_main_color = list_ranked[0]
                    str_main_sku = f'{str_product}-{str_main_color}'
                    float_kept_share = 0.0
                    for str_color in list_kept:
                        float_kept_share += dict_share[str_color]
                    dict_mix = {}
                    for str_color in list_kept:
                        dict_mix[str_color] = dict_share[str_color] / float_kept_share
                    for str_color in list_ranked:
                        if str_color not in list_kept:
                            str_sku = f'{str_product}-{str_color}'
                            if str_sku in dict_instance['color_initial_stock']:
                                if str_main_sku not in dict_instance['color_initial_stock']:
                                    dict_instance['color_initial_stock'][str_main_sku] = 0.0
                                dict_instance['color_initial_stock'][str_main_sku] += (
                                    dict_instance['color_initial_stock'][str_sku])
                                del dict_instance['color_initial_stock'][str_sku]
                            del dict_instance['sku_is_mts'][str_sku]
                    for dict_order in dict_instance['orders']:
                        for dict_item in dict_order['items']:
                            if dict_item['product'] == str_product and dict_item['color'] not in list_kept:
                                dict_item['color'] = str_main_color
                                dict_item['sku'] = str_main_sku
                    for tuple_side in dict_instance['initial_color']:
                        if (dict_instance['initial_form'][tuple_side[0]] == str_product
                                and dict_instance['initial_color'][tuple_side] not in list_kept):
                            dict_instance['initial_color'][tuple_side] = str_main_color
                    dict_instance['colors_by_product'][str_product] = list_kept
                    dict_instance['color_mix'][str_product] = dict_mix

            elif str_factor == 'flexibilidade':
                list_pairs = []
                list_mandatory = []
                list_missing = []
                for str_product in dict_instance['products']:
                    str_fastest = None
                    for str_machine in dict_instance['machines']:
                        if str_machine in dict_instance['productivity'][str_product]:
                            list_pairs.append([str_product, str_machine])
                            if (str_fastest is None or dict_instance['productivity'][str_product][str_machine]
                                    > dict_instance['productivity'][str_product][str_fastest]):
                                str_fastest = str_machine
                        else:
                            list_missing.append([str_product, str_machine])
                    if str_fastest is not None:
                        list_mandatory.append([str_product, str_fastest])
                int_target = int(round(value_level * len(list_pairs)))
                if value_level < 1.0:
                    list_optional = []
                    for list_pair in list_pairs:
                        if list_pair not in list_mandatory:
                            list_optional.append(list_pair)
                    array_order = rng.permutation(len(list_optional))
                    list_kept = list(list_mandatory)
                    int_position = 0
                    while len(list_kept) < int_target and int_position < len(list_optional):
                        list_kept.append(list_optional[int(array_order[int_position])])
                        int_position += 1
                    for list_pair in list_pairs:
                        if list_pair not in list_kept:
                            del dict_instance['productivity'][list_pair[0]][list_pair[1]]
                else:
                    dict_average_rate = {}
                    for str_product in dict_instance['products']:
                        float_total = 0.0
                        int_count = 0
                        for str_machine in dict_instance['productivity'][str_product]:
                            float_total += dict_instance['productivity'][str_product][str_machine]
                            int_count += 1
                        dict_average_rate[str_product] = float_total / int_count
                    array_order = rng.permutation(len(list_missing))
                    int_added = 0
                    int_position = 0
                    while len(list_pairs) + int_added < int_target and int_position < len(list_missing):
                        list_pair = list_missing[int(array_order[int_position])]
                        dict_instance['productivity'][list_pair[0]][list_pair[1]] = dict_average_rate[list_pair[0]]
                        int_added += 1
                        int_position += 1

            elif str_factor == 'demanda':
                for str_product in dict_instance['demand']:
                    for timestamp_week in dict_instance['demand'][str_product]:
                        dict_instance['demand'][str_product][timestamp_week] = (
                            dict_instance['demand'][str_product][timestamp_week] * value_level)
                for dict_order in dict_instance['orders']:
                    for dict_item in dict_order['items']:
                        dict_item['quantity'] = dict_item['quantity'] * value_level

            elif str_factor == 'estoque':
                for str_product in dict_instance['initial_inventory']:
                    dict_instance['initial_inventory'][str_product] = (
                        dict_instance['initial_inventory'][str_product] * value_level)
                for str_sku in dict_instance['color_initial_stock']:
                    dict_instance['color_initial_stock'][str_sku] = (
                        dict_instance['color_initial_stock'][str_sku] * value_level)

            elif str_factor == 'capacidade':
                for str_machine in dict_instance['availability']:
                    for timestamp_week in dict_instance['availability'][str_machine]:
                        dict_instance['availability'][str_machine][timestamp_week] = (
                            dict_instance['availability'][str_machine][timestamp_week] * value_level)

            elif str_factor == 'setup':
                for tuple_pair in dict_instance['form_setup']:
                    dict_instance['form_setup'][tuple_pair] = dict_instance['form_setup'][tuple_pair] * value_level
                for tuple_pair in dict_instance['color_setup']:
                    dict_instance['color_setup'][tuple_pair] = dict_instance['color_setup'][tuple_pair] * value_level

            elif str_factor == 'duas_cores':
                list_two_color = []
                list_one_color = []
                for str_machine in dict_instance['machines']:
                    if dict_instance['color_sides'][str_machine] == 2:
                        list_two_color.append(str_machine)
                    else:
                        list_one_color.append(str_machine)
                array_order_two = rng.permutation(len(list_two_color))
                array_order_one = rng.permutation(len(list_one_color))
                list_order = []
                for int_index in array_order_two:
                    list_order.append(list_two_color[int(int_index)])
                for int_index in array_order_one:
                    list_order.append(list_one_color[int(int_index)])
                int_target = int(round(value_level * len(dict_instance['machines'])))
                for int_position in range(len(list_order)):
                    if int_position < int_target:
                        dict_instance['color_sides'][list_order[int_position]] = 2
                    else:
                        dict_instance['color_sides'][list_order[int_position]] = 1

            elif str_factor == 'horizonte':
                dict_settings['weeks_in_plan'] = value_level

            elif str_factor == 'congeladas':
                dict_settings['frozen_weeks'] = value_level

        int_pairs = 0
        int_skus = 0
        for str_product in dict_instance['products']:
            int_skus += len(dict_instance['colors_by_product'][str_product])
            for str_machine in dict_instance['machines']:
                if str_machine in dict_instance['productivity'][str_product]:
                    int_pairs += 1
        int_two_color = 0
        for str_machine in dict_instance['machines']:
            if dict_instance['color_sides'][str_machine] == 2:
                int_two_color += 1
        dict_size = {'baloes': len(dict_instance['products']), 'maquinas': len(dict_instance['machines']),
                     'maquinas_duas_cores': int_two_color, 'skus': int_skus, 'pares_balao_maquina': int_pairs,
                     'semanas': dict_settings['weeks_in_plan'], 'semanas_congeladas': dict_settings['frozen_weeks'],
                     'pedidos': len(dict_instance['orders'])}

        print(f"[{int_run_number}/{len(list_runs)}] {dict_run['id']}: {dict_size}")
        float_started_at = time.perf_counter()
        dict_weekly = run_weekly_plan(dict_settings, dict_instance)
        float_weekly_seconds = time.perf_counter() - float_started_at
        dict_daily = None
        float_daily_seconds = None
        if dict_weekly['status'] in ('Optimal', 'Feasible'):
            float_started_at = time.perf_counter()
            dict_daily = run_daily_plan(dict_settings, dict_instance, dict_weekly)
            float_daily_seconds = time.perf_counter() - float_started_at

        dict_record = {
            'id': dict_run['id'],
            'variante': str_variant,
            'fase': dict_run['phase'],
            'alteracoes': dict_run['changes'],
            'sorteio': dict_run['draw'],
            'semente_solver': dict_run['solver_seed'],
            'tamanho': dict_size,
            'parametros': dict_settings,
            'semanal': {'status': dict_weekly['status'], 'segundos_totais': float_weekly_seconds,
                        'stage_reports': dict_weekly['stage_reports'], 'kpis': dict_weekly['kpis']},
            'diario': None,
            'concluida_em': datetime.now().isoformat(timespec='seconds'),
        }
        if dict_daily is not None:
            dict_record['diario'] = {'status': dict_daily['status'], 'segundos_totais': float_daily_seconds,
                                     'stage_reports': dict_daily['stage_reports'], 'kpis': dict_daily['kpis']}
            if 'mip_kpis' in dict_daily:
                dict_record['diario']['mip_kpis'] = dict_daily['mip_kpis']
                dict_record['diario']['sequencing_violations'] = dict_daily['sequencing_violations']
        with open(str_run_path, 'w', encoding='utf-8') as file_run:
            json.dump(dict_record, file_run, indent=2, ensure_ascii=False)

        str_daily_status = '-'
        if dict_daily is not None:
            str_daily_status = f'{dict_daily["status"]} {float_daily_seconds:.1f}s'
        with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
            file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} {dict_run['id']} "
                               f"semanal={dict_weekly['status']} {float_weekly_seconds:.1f}s "
                               f"diario={str_daily_status}\n")

    list_csv_rows = []
    list_run_files = sorted(os.listdir(str_runs_directory))
    for str_run_file in list_run_files:
        with open(os.path.join(str_runs_directory, str_run_file), encoding='utf-8') as file_run:
            dict_saved = json.load(file_run)
        dict_row = {'id': dict_saved['id'], 'variante': dict_saved['variante'], 'fase': dict_saved['fase'],
                    'fator_a': None, 'nivel_a': None, 'fator_b': None, 'nivel_b': None,
                    'sorteio': dict_saved['sorteio'], 'semente_solver': dict_saved['semente_solver']}
        if len(dict_saved['alteracoes']) > 0:
            dict_row['fator_a'] = dict_saved['alteracoes'][0][0]
            dict_row['nivel_a'] = dict_saved['alteracoes'][0][1]
        if len(dict_saved['alteracoes']) > 1:
            dict_row['fator_b'] = dict_saved['alteracoes'][1][0]
            dict_row['nivel_b'] = dict_saved['alteracoes'][1][1]
        for str_size_key in dict_saved['tamanho']:
            dict_row[str_size_key] = dict_saved['tamanho'][str_size_key]
        dict_weekly_summary = summarize_level(dict_saved['semanal'])
        for str_column in LEVEL_COLUMNS:
            dict_row[f'semanal_{str_column}'] = dict_weekly_summary[str_column]
        if dict_saved['diario'] is not None:
            dict_daily_summary = summarize_level(dict_saved['diario'])
            for str_column in LEVEL_COLUMNS:
                dict_row[f'diario_{str_column}'] = dict_daily_summary[str_column]
        else:
            for str_column in LEVEL_COLUMNS:
                dict_row[f'diario_{str_column}'] = None
            dict_row['diario_status'] = 'NaoExecutado'
        list_csv_rows.append(dict_row)
    if len(list_csv_rows) > 0:
        with open(os.path.join(str_variant_directory, 'resultados.csv'), 'w', encoding='utf-8',
                  newline='') as file_csv:
            writer = csv.DictWriter(file_csv, fieldnames=list(list_csv_rows[0].keys()), delimiter=';')
            writer.writeheader()
            for dict_row in list_csv_rows:
                writer.writerow(dict_row)

with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
    file_battery.write(f'{datetime.now().isoformat(timespec="seconds")} fim variante={str_variant}\n')
dict_environment['situacao'] = 'concluida'
dict_environment['fim'] = datetime.now().isoformat(timespec='seconds')
with open(str_environment_path, 'w', encoding='utf-8') as file_environment:
    json.dump(dict_environment, file_environment, indent=2, ensure_ascii=False)
print(f'resultados em {str_variant_directory}')
