import argparse
import csv
import json
import os
import platform
import sys
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_ROOT = os.path.join(ROOT_DIR, 'experimentos', 'esforco_computacional')
QUICK_TIME_LIMIT = 30

parser = argparse.ArgumentParser()
parser.add_argument('--codigo', default=ROOT_DIR)
parser.add_argument('--arquitetura', choices=['hierarquica', 'monolitica'], required=True)
parser.add_argument('--variante', required=True)
parser.add_argument('--tecnica', default='pura')
parser.add_argument('--saida', default=DEFAULT_OUTPUT_ROOT)
parser.add_argument('--pasta', default=None)
parser.add_argument('--rapido', action='store_true')
parser.add_argument('--threads', type=int, default=2)
dict_arguments = vars(parser.parse_args())

str_code_directory = os.path.abspath(dict_arguments['codigo'])
sys.path.insert(0, str_code_directory)

from processing.data import load_instance
from processing.settings import DEFAULT_SETTINGS
from experiment_common import (ARCHITECTURE_CASES, ARCHITECTURE_QUICK_CASES, ARCHITECTURE_SETTINGS, LEVEL_COLUMNS,
                               open_environment, summarize_level)


str_architecture = dict_arguments['arquitetura']
str_variant = dict_arguments['variante']
str_output_root = os.path.abspath(dict_arguments['saida'])
bool_quick = dict_arguments['rapido']
str_machine_label = os.environ.get('EXPERIMENT_MACHINE_LABEL', platform.node()).lower().replace(' ', '-')
if dict_arguments['pasta'] is not None:
    str_run_directory = os.path.abspath(dict_arguments['pasta'])
else:
    str_folder_name = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{str_machine_label}_arquitetura_{str_variant}"
    if bool_quick:
        str_folder_name = f'{str_folder_name}_rapido'
    str_run_directory = os.path.join(str_output_root, 'rodadas', str_folder_name)
str_runs_directory = os.path.join(str_run_directory, 'execucoes')
str_solutions_directory = os.path.join(str_run_directory, 'solucoes')
str_logs_directory = os.path.join(str_run_directory, 'logs')
os.makedirs(str_runs_directory, exist_ok=True)
os.makedirs(str_solutions_directory, exist_ok=True)
os.makedirs(str_logs_directory, exist_ok=True)

dict_base_settings = dict(DEFAULT_SETTINGS)
for str_key in ARCHITECTURE_SETTINGS:
    dict_base_settings[str_key] = ARCHITECTURE_SETTINGS[str_key]
dict_base_settings['threads'] = dict_arguments['threads']
if bool_quick:
    dict_base_settings['weekly_time_limit'] = QUICK_TIME_LIMIT
    dict_base_settings['daily_time_limit'] = QUICK_TIME_LIMIT
dict_base_settings['monolithic_technique'] = dict_arguments['tecnica']
dict_base_settings['monolithic_time_limit'] = (dict_base_settings['weekly_time_limit']
                                               + dict_base_settings['daily_time_limit'])

list_cases = []
for dict_case in ARCHITECTURE_CASES:
    if not bool_quick or dict_case['id'] in ARCHITECTURE_QUICK_CASES:
        list_cases.append(dict_case)

with open(os.path.join(str_run_directory, 'plano.json'), 'w', encoding='utf-8') as file_plan:
    json.dump({'bateria': 'arquitetura', 'arquitetura': str_architecture, 'tecnica': dict_arguments['tecnica'],
               'parametros': ARCHITECTURE_SETTINGS, 'casos': list_cases}, file_plan, indent=2, ensure_ascii=False)

str_environment_path = os.path.join(str_run_directory, 'ambiente.json')
dict_environment = open_environment(str_environment_path, str_code_directory, str_variant, bool_quick,
                                    str_machine_label, dict_base_settings)
dict_environment['bateria'] = 'arquitetura'
dict_environment['arquitetura'] = str_architecture
dict_environment['tecnica'] = dict_arguments['tecnica']
dict_environment['execucoes_planejadas'] = len(list_cases)
with open(str_environment_path, 'w', encoding='utf-8') as file_environment:
    json.dump(dict_environment, file_environment, indent=2, ensure_ascii=False)

if str_architecture == 'hierarquica':
    from optimization.planner import run_weekly_plan, run_daily_plan
else:
    from optimization.monolithic_model import run_monolithic_plan

str_battery_log = os.path.join(str_run_directory, 'bateria.log')
with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
    file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} inicio variante={str_variant} "
                       f"arquitetura={str_architecture} casos={len(list_cases)}\n")

int_case_number = 0
for dict_case in list_cases:
    int_case_number += 1
    str_run_path = os.path.join(str_runs_directory, f"{dict_case['id']}.json")
    if os.path.exists(str_run_path):
        print(f"[{int_case_number}/{len(list_cases)}] {dict_case['id']}: ja executado")
    else:
        dict_instance = load_instance(os.path.join(str_code_directory, 'data', dict_case['arquivo']))
        dict_settings = dict(dict_base_settings)
        dict_settings['weeks_in_plan'] = dict_case['semanas']
        str_log_path = os.path.join(str_logs_directory, f"{dict_case['id']}.log")
        if os.path.exists(str_log_path):
            os.remove(str_log_path)
        dict_settings['solver_log_file'] = str_log_path

        int_pairs = 0
        int_skus = 0
        int_max_colors = 0
        for str_product in dict_instance['products']:
            int_skus += len(dict_instance['colors_by_product'][str_product])
            if len(dict_instance['colors_by_product'][str_product]) > int_max_colors:
                int_max_colors = len(dict_instance['colors_by_product'][str_product])
            for str_machine in dict_instance['machines']:
                if str_machine in dict_instance['productivity'][str_product]:
                    int_pairs += 1
        int_two_color = 0
        for str_machine in dict_instance['machines']:
            if dict_instance['color_sides'][str_machine] == 2:
                int_two_color += 1
        dict_size = {'baloes': len(dict_instance['products']), 'maquinas': len(dict_instance['machines']),
                     'maquinas_duas_cores': int_two_color, 'skus': int_skus, 'pares_balao_maquina': int_pairs,
                     'max_cores_balao': int_max_colors, 'semanas': dict_case['semanas'],
                     'semanas_congeladas': dict_settings['frozen_weeks'], 'pedidos': len(dict_instance['orders'])}
        print(f"[{int_case_number}/{len(list_cases)}] {dict_case['id']}: {dict_size}")

        dict_record = {'id': dict_case['id'], 'variante': str_variant, 'arquitetura': str_architecture,
                       'tecnica': dict_arguments['tecnica'], 'caso': dict_case, 'tamanho': dict_size,
                       'parametros': dict_settings}
        float_started_at = time.perf_counter()
        if str_architecture == 'hierarquica':
            dict_weekly = run_weekly_plan(dict_settings, dict_instance)
            float_weekly_seconds = time.perf_counter() - float_started_at
            dict_daily = None
            float_daily_seconds = None
            if dict_weekly['status'] in ('Optimal', 'Feasible'):
                float_daily_started_at = time.perf_counter()
                dict_daily = run_daily_plan(dict_settings, dict_instance, dict_weekly)
                float_daily_seconds = time.perf_counter() - float_daily_started_at
            dict_record['semanal'] = {'status': dict_weekly['status'], 'segundos_totais': float_weekly_seconds,
                                      'stage_reports': dict_weekly['stage_reports'], 'kpis': dict_weekly['kpis']}
            dict_record['diario'] = None
            if dict_daily is not None:
                dict_record['diario'] = {'status': dict_daily['status'], 'segundos_totais': float_daily_seconds,
                                         'stage_reports': dict_daily['stage_reports'], 'kpis': dict_daily['kpis']}
            with open(os.path.join(str_solutions_directory, f"{dict_case['id']}.json"), 'w',
                      encoding='utf-8') as file_solution:
                json.dump({'semanal': dict_weekly, 'diario': dict_daily}, file_solution, ensure_ascii=False,
                          default=str)
        else:
            dict_monolithic = run_monolithic_plan(dict_settings, dict_instance)
            dict_record['monolitico'] = {'status': dict_monolithic['status'],
                                         'segundos_totais': time.perf_counter() - float_started_at,
                                         'stage_reports': dict_monolithic['stage_reports'],
                                         'kpis': dict_monolithic['kpis'],
                                         'tamanho_modelo': dict_monolithic['size'],
                                         'avaliacao_semanas_detalhadas': dict_monolithic['detailed_evaluation']}
            with open(os.path.join(str_solutions_directory, f"{dict_case['id']}.json"), 'w',
                      encoding='utf-8') as file_solution:
                json.dump(dict_monolithic, file_solution, ensure_ascii=False, default=str)
        dict_record['concluida_em'] = datetime.now().isoformat(timespec='seconds')
        with open(str_run_path, 'w', encoding='utf-8') as file_run:
            json.dump(dict_record, file_run, indent=2, ensure_ascii=False, default=str)
        with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
            file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} {dict_case['id']} "
                               f"{time.perf_counter() - float_started_at:.1f}s\n")

    list_csv_rows = []
    for str_run_file in sorted(os.listdir(str_runs_directory)):
        with open(os.path.join(str_runs_directory, str_run_file), encoding='utf-8') as file_run:
            dict_saved = json.load(file_run)
        dict_row = {'id': dict_saved['id'], 'variante': dict_saved['variante'],
                    'arquitetura': dict_saved['arquitetura'], 'tecnica': dict_saved['tecnica']}
        for str_size_key in dict_saved['tamanho']:
            dict_row[str_size_key] = dict_saved['tamanho'][str_size_key]
        if dict_saved['arquitetura'] == 'hierarquica':
            list_levels = [['semanal', dict_saved['semanal']], ['diario', dict_saved['diario']]]
        else:
            list_levels = [['monolitico', dict_saved['monolitico']]]
        for list_level in list_levels:
            if list_level[1] is None:
                for str_column in LEVEL_COLUMNS:
                    dict_row[f'{list_level[0]}_{str_column}'] = None
                dict_row[f'{list_level[0]}_status'] = 'NaoExecutado'
            else:
                dict_summary = summarize_level(list_level[1])
                for str_column in LEVEL_COLUMNS:
                    dict_row[f'{list_level[0]}_{str_column}'] = dict_summary[str_column]
        list_csv_rows.append(dict_row)
    with open(os.path.join(str_run_directory, 'resultados.csv'), 'w', encoding='utf-8', newline='') as file_csv:
        writer = csv.DictWriter(file_csv, fieldnames=list(list_csv_rows[0].keys()), delimiter=';')
        writer.writeheader()
        for dict_row in list_csv_rows:
            writer.writerow(dict_row)

dict_environment['situacao'] = 'concluida'
dict_environment['fim'] = datetime.now().isoformat(timespec='seconds')
with open(str_environment_path, 'w', encoding='utf-8') as file_environment:
    json.dump(dict_environment, file_environment, indent=2, ensure_ascii=False)
print(f'resultados em {str_run_directory}')
