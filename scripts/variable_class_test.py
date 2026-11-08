import argparse
import csv
import json
import os
import platform
import sys
import time
from datetime import datetime

import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from processing.data import load_instance
from processing.settings import DEFAULT_SETTINGS
from optimization.weekly_model import build_weekly_scenario, solve_weekly_model
from optimization.daily_model import build_daily_scenario, solve_daily_model
from experiment_common import open_environment

DEFAULT_OUTPUT_ROOT = os.path.join(ROOT_DIR, 'experimentos', 'esforco_computacional')
VARIANT_NAME = 'classes_variaveis'

SETTINGS_OVERRIDES = {
    'start_week': '2024-01-01',
    'weeks_in_plan': 13,
    'frozen_weeks': 1,
    'shifts_per_day': 3,
    'hours_per_shift': 8,
    'working_days_per_week': 6,
    'warehouse_capacity_kg': None,
    'annual_holding_rate': 0.25,
    'weekly_solver_name': 'GUROBI',
    'weekly_time_limit': 600,
    'daily_solver_name': 'GUROBI',
    'daily_time_limit': 600,
    'threads': 1,
    'solver_seed': 0,
}
QUICK_TIME_LIMIT = 30
INSTANCES = [
    {'id': 'pequeno', 'arquivo': 'instance_pequeno_P4_M6_T13.xlsx', 'semanas': 13},
    {'id': 'medio', 'arquivo': 'instance_medio_P8_M12_T13.xlsx', 'semanas': 13},
    {'id': 'ajustado', 'arquivo': 'input_asis_ajustado.xlsx', 'semanas': 13},
]
QUICK_INSTANCES = [
    {'id': 'micro', 'arquivo': 'instance_micro_P2_M3_T8.xlsx', 'semanas': 8},
    {'id': 'pequeno', 'arquivo': 'instance_pequeno_P4_M6_T13.xlsx', 'semanas': 13},
]
SOLVER_SEEDS = [0, 1, 2]
QUICK_SOLVER_SEEDS = [0]
FREE_PERCENTAGES = [0, 25, 50, 75, 100]
SIZE_HORIZONS = [4, 8]
FREE_SUBSET_SEED = 2026
DAILY_BINARY_PREFIX = 'z_'
METRICS = ['segundos', 'segundos_estagio1', 'segundos_solver', 'nos', 'nos_estagio1', 'iteracoes',
           'iteracoes_estagio1', 'work', 'work_estagio1']
REGRESSION_MEASURES = [['segundos', 'work'], ['segundos_estagio1', 'work_estagio1'], ['segundos_solver', 'work']]

parser = argparse.ArgumentParser()
parser.add_argument('--saida', default=DEFAULT_OUTPUT_ROOT)
parser.add_argument('--pasta', default=None)
parser.add_argument('--rapido', action='store_true')
parser.add_argument('--threads', type=int, default=SETTINGS_OVERRIDES['threads'])
dict_arguments = vars(parser.parse_args())

str_output_root = os.path.abspath(dict_arguments['saida'])
bool_quick = dict_arguments['rapido']
str_machine_label = os.environ.get('EXPERIMENT_MACHINE_LABEL', platform.node()).lower().replace(' ', '-')
if dict_arguments['pasta'] is not None:
    str_run_directory = os.path.abspath(dict_arguments['pasta'])
else:
    str_folder_name = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{str_machine_label}_{VARIANT_NAME}"
    if bool_quick:
        str_folder_name = f'{str_folder_name}_rapido'
    str_run_directory = os.path.join(str_output_root, 'rodadas', str_folder_name)
str_runs_directory = os.path.join(str_run_directory, 'execucoes')
str_solutions_directory = os.path.join(str_run_directory, 'solucoes_base')
str_logs_directory = os.path.join(str_run_directory, 'logs')
os.makedirs(str_runs_directory, exist_ok=True)
os.makedirs(str_solutions_directory, exist_ok=True)
os.makedirs(str_logs_directory, exist_ok=True)

dict_base_settings = dict(DEFAULT_SETTINGS)
for str_key in SETTINGS_OVERRIDES:
    dict_base_settings[str_key] = SETTINGS_OVERRIDES[str_key]
dict_base_settings['threads'] = dict_arguments['threads']
list_instances = INSTANCES
list_seeds = SOLVER_SEEDS
if bool_quick:
    dict_base_settings['weekly_time_limit'] = QUICK_TIME_LIMIT
    dict_base_settings['daily_time_limit'] = QUICK_TIME_LIMIT
    list_instances = QUICK_INSTANCES
    list_seeds = QUICK_SOLVER_SEEDS

list_configurations = []
for dict_instance_case in list_instances:
    for str_level in ['semanal', 'diario']:
        list_horizons = [dict_instance_case['semanas']]
        if str_level == 'semanal' and dict_instance_case['id'] == list_instances[-1]['id']:
            for int_horizon in SIZE_HORIZONS:
                list_horizons.append(int_horizon)
        for int_horizon in list_horizons:
            list_variants = [['base', None, 'base']]
            if int_horizon == dict_instance_case['semanas']:
                list_variants.append(['lp', None, 'lp'])
                for int_percentage in FREE_PERCENTAGES:
                    if int_percentage == 100:
                        list_variants.append([f'livre_{int_percentage}', int_percentage, 'base'])
                    else:
                        list_variants.append([f'livre_{int_percentage}', int_percentage, f'livre_{int_percentage}'])
                list_variants.append(['fixas_tamanho', 0, 'livre_0'])
                if str_level == 'diario':
                    list_variants.append(['z_binaria', None, 'z_binaria'])
            else:
                list_variants.append(['fixas_tamanho', 0, 'fixas_tamanho'])
            str_case = f"{str_level}_{dict_instance_case['id']}_h{int_horizon:02d}"
            for list_variant in list_variants:
                list_configurations.append({'caso': str_case, 'variante': list_variant[0], 'nivel': str_level,
                                            'instancia': dict_instance_case['id'],
                                            'arquivo': dict_instance_case['arquivo'], 'semanas': int_horizon,
                                            'percentual_livre': list_variant[1],
                                            'execucoes': f'{str_case}_{list_variant[2]}',
                                            'execucoes_proprias': list_variant[0] == list_variant[2]})

list_runs = []
for dict_configuration in list_configurations:
    if dict_configuration['execucoes_proprias']:
        for int_seed in list_seeds:
            dict_run = dict(dict_configuration)
            dict_run['id'] = f"{dict_configuration['execucoes']}_semente{int_seed}"
            dict_run['semente'] = int_seed
            list_runs.append(dict_run)

with open(os.path.join(str_run_directory, 'plano.json'), 'w', encoding='utf-8') as file_plan:
    json.dump({'bateria': 'classes', 'parametros': SETTINGS_OVERRIDES, 'limite_rapido': QUICK_TIME_LIMIT,
               'instancias': list_instances, 'sementes_solver': list_seeds, 'percentuais_livres': FREE_PERCENTAGES,
               'horizontes_tamanho': SIZE_HORIZONS, 'semente_subconjunto_livre': FREE_SUBSET_SEED,
               'prefixo_binario_diario': DAILY_BINARY_PREFIX, 'configuracoes': list_configurations},
              file_plan, indent=2, ensure_ascii=False)

str_environment_path = os.path.join(str_run_directory, 'ambiente.json')
dict_environment = open_environment(str_environment_path, ROOT_DIR, VARIANT_NAME, bool_quick, str_machine_label,
                                    dict_base_settings)
dict_environment['bateria'] = 'classes'
dict_environment['execucoes_planejadas'] = len(list_runs)
with open(str_environment_path, 'w', encoding='utf-8') as file_environment:
    json.dump(dict_environment, file_environment, indent=2, ensure_ascii=False)

str_battery_log = os.path.join(str_run_directory, 'bateria.log')
with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
    file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} inicio variante={VARIANT_NAME} "
                       f"configuracoes={len(list_configurations)} execucoes={len(list_runs)} "
                       f"commit={dict_environment['commit']}\n")

dict_instances = {}
int_run_number = 0
for dict_run in list_runs:
    int_run_number += 1
    str_run_path = os.path.join(str_runs_directory, f"{dict_run['id']}.json")
    if os.path.exists(str_run_path):
        print(f"[{int_run_number}/{len(list_runs)}] {dict_run['id']}: ja executada")
    else:
        print(f"[{int_run_number}/{len(list_runs)}] {dict_run['id']}")
        if dict_run['instancia'] not in dict_instances:
            dict_instances[dict_run['instancia']] = load_instance(os.path.join(ROOT_DIR, 'data', dict_run['arquivo']))
        dict_instance = dict_instances[dict_run['instancia']]
        dict_settings = dict(dict_base_settings)
        dict_settings['weeks_in_plan'] = dict_run['semanas']
        dict_settings['solver_seed'] = dict_run['semente']
        str_log_path = os.path.join(str_logs_directory, f"{dict_run['id']}.log")
        if os.path.exists(str_log_path):
            os.remove(str_log_path)
        dict_settings['solver_log_file'] = str_log_path
        str_solution_prefix = os.path.join(str_solutions_directory, dict_run['caso'])
        bool_saves_base = dict_run['variante'] == 'base' and dict_run['semente'] == list_seeds[0]

        int_fixed = 0
        if dict_run['variante'] == 'base':
            if bool_saves_base:
                dict_settings['variable_values_file'] = f'{str_solution_prefix}_valores.json'
        elif dict_run['variante'] == 'lp':
            dict_settings['relax_binaries'] = True
        elif dict_run['variante'] == 'z_binaria':
            dict_settings['binary_variable_prefix'] = DAILY_BINARY_PREFIX
        else:
            with open(f'{str_solution_prefix}_valores.json', encoding='utf-8') as file_values:
                dict_base_values = json.load(file_values)
            list_names = sorted(dict_base_values)
            dict_fixed_values = {}
            for str_name in list_names:
                dict_fixed_values[str_name] = float(round(dict_base_values[str_name]))
            rng = np.random.default_rng(FREE_SUBSET_SEED)
            array_order = rng.permutation(len(list_names))
            int_free = int(round(dict_run['percentual_livre'] * len(list_names) / 100.0))
            list_free_names = []
            for int_position in range(int_free):
                list_free_names.append(list_names[int(array_order[int_position])])
            dict_settings['fixed_variable_values'] = dict_fixed_values
            dict_settings['free_variable_names'] = list_free_names
            int_fixed = len(list_names) - int_free

        if dict_run['nivel'] == 'semanal':
            dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
            float_started_at = time.perf_counter()
            dict_result = solve_weekly_model(dict_scenario, dict_settings)
            float_level_seconds = time.perf_counter() - float_started_at
            if bool_saves_base:
                with open(f'{str_solution_prefix}_metas.json', 'w', encoding='utf-8') as file_targets:
                    json.dump(dict_result['targets'], file_targets)
        else:
            str_targets_path = os.path.join(str_solutions_directory,
                                            f"semanal_{dict_run['instancia']}_h{dict_run['semanas']:02d}_metas.json")
            with open(str_targets_path, encoding='utf-8') as file_targets:
                dict_targets = json.load(file_targets)
            dict_scenario = build_daily_scenario(dict_instance, dict_settings, {'targets': dict_targets})
            float_started_at = time.perf_counter()
            dict_result = solve_daily_model(dict_scenario, dict_settings)
            float_level_seconds = time.perf_counter() - float_started_at

        dict_parameters = dict(dict_settings)
        if dict_settings['fixed_variable_values'] is not None:
            dict_parameters['fixed_variable_values'] = len(dict_settings['fixed_variable_values'])
            dict_parameters['free_variable_names'] = len(dict_settings['free_variable_names'])
        dict_record = {'id': dict_run['id'], 'caso': dict_run['caso'], 'nivel': dict_run['nivel'],
                       'instancia': dict_run['instancia'], 'arquivo': dict_run['arquivo'],
                       'semanas': dict_run['semanas'], 'variante': dict_run['variante'],
                       'percentual_livre': dict_run['percentual_livre'], 'semente': dict_run['semente'],
                       'binarias_fixadas': int_fixed, 'parametros': dict_parameters,
                       'status': dict_result['status'], 'segundos_totais': float_level_seconds,
                       'stage_objectives': None, 'stage_reports': dict_result['stage_reports'],
                       'kpis': dict_result['kpis'], 'concluida_em': datetime.now().isoformat(timespec='seconds')}
        if 'stage_objectives' in dict_result:
            dict_record['stage_objectives'] = dict_result['stage_objectives']
        with open(str_run_path, 'w', encoding='utf-8') as file_run:
            json.dump(dict_record, file_run, indent=2, ensure_ascii=False, default=str)
        with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
            file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} {dict_run['id']} "
                               f"{dict_result['status']} {float_level_seconds:.1f}s\n")

    dict_executions = {}
    for str_run_file in sorted(os.listdir(str_runs_directory)):
        with open(os.path.join(str_runs_directory, str_run_file), encoding='utf-8') as file_run:
            dict_saved = json.load(file_run)
        dict_executions[dict_saved['id']] = dict_saved

    list_result_rows = []
    dict_level_points = {'semanal': [], 'diario': []}
    dict_level_executions = {'semanal': [], 'diario': []}
    for dict_configuration in list_configurations:
        list_saved = []
        for int_seed in list_seeds:
            str_execution_id = f"{dict_configuration['execucoes']}_semente{int_seed}"
            if str_execution_id in dict_executions:
                list_saved.append(dict_executions[str_execution_id])
        if len(list_saved) > 0:
            dict_series = {}
            for str_metric in METRICS:
                dict_series[str_metric] = []
            float_max_gap = None
            bool_hit_limit = False
            list_statuses = []
            float_max_difference = None
            for dict_saved in list_saved:
                dict_execution_metrics = {}
                for str_metric in METRICS:
                    dict_execution_metrics[str_metric] = 0.0
                for dict_report in dict_saved['stage_reports']:
                    dict_execution_metrics['segundos'] += dict_report['seconds']
                    dict_execution_metrics['segundos_solver'] += dict_report['solver_seconds']
                    dict_execution_metrics['nos'] += dict_report['nodes']
                    dict_execution_metrics['iteracoes'] += dict_report['simplex_iterations']
                    dict_execution_metrics['work'] += dict_report['work']
                    if dict_report['gap'] is not None:
                        if float_max_gap is None or dict_report['gap'] > float_max_gap:
                            float_max_gap = dict_report['gap']
                    if dict_report['hit_time_limit']:
                        bool_hit_limit = True
                dict_first_stage = dict_saved['stage_reports'][0]
                dict_execution_metrics['segundos_estagio1'] = dict_first_stage['seconds']
                dict_execution_metrics['nos_estagio1'] = dict_first_stage['nodes']
                dict_execution_metrics['iteracoes_estagio1'] = dict_first_stage['simplex_iterations']
                dict_execution_metrics['work_estagio1'] = dict_first_stage['work']
                for str_metric in METRICS:
                    dict_series[str_metric].append(dict_execution_metrics[str_metric])
                if dict_configuration['execucoes_proprias']:
                    dict_level_executions[dict_configuration['nivel']].append(dict_execution_metrics)
                if dict_saved['status'] not in list_statuses:
                    list_statuses.append(dict_saved['status'])

                str_base_id = f"{dict_configuration['caso']}_base_semente{dict_saved['semente']}"
                if dict_configuration['variante'] != 'base' and str_base_id in dict_executions:
                    list_base_values = dict_executions[str_base_id]['stage_objectives']
                    list_values = dict_saved['stage_objectives']
                    if list_base_values is not None and list_values is not None:
                        int_stages = min(len(list_base_values), len(list_values))
                        for int_stage in range(int_stages):
                            float_difference = (abs(list_values[int_stage] - list_base_values[int_stage])
                                                / max(1.0, abs(list_base_values[int_stage])))
                            if float_max_difference is None or float_difference > float_max_difference:
                                float_max_difference = float_difference

            dict_first_report = list_saved[0]['stage_reports'][0]
            int_fixed = list_saved[0]['binarias_fixadas']
            dict_row = {'variante': dict_configuration['variante'], 'nivel': dict_configuration['nivel'],
                        'instancia': dict_configuration['instancia'], 'semanas': dict_configuration['semanas'],
                        'percentual_livre': dict_configuration['percentual_livre'],
                        'execucoes': dict_configuration['execucoes'], 'sementes': len(list_saved),
                        'variaveis': dict_first_report['variables'],
                        'binarias_livres': dict_first_report['binaries'],
                        'binarias_fixadas': int_fixed,
                        'inteiras_gerais': dict_first_report['integers'] - dict_first_report['binaries'] - int_fixed,
                        'continuas': dict_first_report['variables'] - dict_first_report['integers'],
                        'restricoes': dict_first_report['constraints'],
                        'nao_zeros': dict_first_report['nonzeros'],
                        'segundos_min': float(np.min(dict_series['segundos'])),
                        'segundos_max': float(np.max(dict_series['segundos']))}
            for str_metric in METRICS:
                dict_row[f'{str_metric}_mediana'] = float(np.median(dict_series[str_metric]))
            dict_row['gap_max'] = float_max_gap
            dict_row['bateu_limite'] = bool_hit_limit
            dict_row['status'] = '|'.join(list_statuses)
            dict_row['dif_rel_max_estagios_vs_base'] = float_max_difference
            list_result_rows.append(dict_row)
            if dict_configuration['execucoes_proprias']:
                dict_level_points[dict_configuration['nivel']].append(dict_row)

    list_regression_rows = []
    for str_level in ['semanal', 'diario']:
        for list_measure in REGRESSION_MEASURES:
            str_seconds_metric = list_measure[0]
            str_work_metric = list_measure[1]
            list_log_seconds = []
            list_log_free = []
            list_log_continuous = []
            list_log_integers = []
            int_hit_limit = 0
            for dict_row in dict_level_points[str_level]:
                list_log_seconds.append(np.log(dict_row[f'{str_seconds_metric}_mediana']))
                list_log_free.append(np.log(1.0 + dict_row['binarias_livres']))
                list_log_continuous.append(np.log(dict_row['continuas']))
                list_log_integers.append(np.log(1.0 + dict_row['inteiras_gerais']))
                if dict_row['bateu_limite']:
                    int_hit_limit += 1
            list_regressors = [np.ones(len(list_log_seconds)), list_log_free, list_log_continuous]
            bool_integers_vary = len(list_log_integers) > 0 and max(list_log_integers) > min(list_log_integers)
            if bool_integers_vary:
                list_regressors.append(list_log_integers)
            dict_regression_row = {'nivel': str_level, 'medida': str_seconds_metric, 'n': len(list_log_seconds),
                                   'n_bateu_limite': int_hit_limit, 'r2': None, 'intercepto': None,
                                   'elasticidade_binarias_livres': None, 'elasticidade_continuas': None,
                                   'elasticidade_inteiras_gerais': None, 'inteiras_gerais_variam': bool_integers_vary,
                                   'correlacao_log_segundos_log_work': None, 'n_correlacao': 0}
            if len(list_log_seconds) > len(list_regressors):
                matrix_regressors = np.column_stack(list_regressors)
                array_log_seconds = np.array(list_log_seconds)
                array_coefficients = np.linalg.lstsq(matrix_regressors, array_log_seconds, rcond=None)[0]
                array_residuals = array_log_seconds - matrix_regressors @ array_coefficients
                float_total_variation = float(np.sum((array_log_seconds - np.mean(array_log_seconds)) ** 2))
                dict_regression_row['r2'] = 1.0 - float(np.sum(array_residuals ** 2)) / float_total_variation
                dict_regression_row['intercepto'] = float(array_coefficients[0])
                dict_regression_row['elasticidade_binarias_livres'] = float(array_coefficients[1])
                dict_regression_row['elasticidade_continuas'] = float(array_coefficients[2])
                if bool_integers_vary:
                    dict_regression_row['elasticidade_inteiras_gerais'] = float(array_coefficients[3])

            list_correlation_seconds = []
            list_correlation_work = []
            for dict_execution_metrics in dict_level_executions[str_level]:
                if dict_execution_metrics[str_seconds_metric] > 0.0 and dict_execution_metrics[str_work_metric] > 0.0:
                    list_correlation_seconds.append(np.log(dict_execution_metrics[str_seconds_metric]))
                    list_correlation_work.append(np.log(dict_execution_metrics[str_work_metric]))
            dict_regression_row['n_correlacao'] = len(list_correlation_seconds)
            if len(list_correlation_seconds) > 2:
                dict_regression_row['correlacao_log_segundos_log_work'] = float(
                    np.corrcoef(list_correlation_seconds, list_correlation_work)[0, 1])
            list_regression_rows.append(dict_regression_row)

    if len(list_result_rows) > 0:
        with open(os.path.join(str_run_directory, 'resultados.csv'), 'w', encoding='utf-8', newline='') as file_csv:
            writer = csv.DictWriter(file_csv, fieldnames=list(list_result_rows[0].keys()), delimiter=';')
            writer.writeheader()
            for dict_row in list_result_rows:
                writer.writerow(dict_row)
        with open(os.path.join(str_run_directory, 'regressao.csv'), 'w', encoding='utf-8', newline='') as file_csv:
            writer = csv.DictWriter(file_csv, fieldnames=list(list_regression_rows[0].keys()), delimiter=';')
            writer.writeheader()
            for dict_row in list_regression_rows:
                writer.writerow(dict_row)

int_max_general_integers = 0
for dict_row in list_result_rows:
    if dict_row['inteiras_gerais'] > int_max_general_integers:
        int_max_general_integers = dict_row['inteiras_gerais']
if int_max_general_integers == 0:
    str_integer_note = 'o modelo nao tem inteiras gerais: so binarias e continuas'
else:
    str_integer_note = f'inteiras gerais presentes (maximo {int_max_general_integers})'
with open(str_battery_log, 'a', encoding='utf-8') as file_battery:
    file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} {str_integer_note}\n")
    file_battery.write(f"{datetime.now().isoformat(timespec='seconds')} fim variante={VARIANT_NAME}\n")
dict_environment['situacao'] = 'concluida'
dict_environment['fim'] = datetime.now().isoformat(timespec='seconds')
with open(str_environment_path, 'w', encoding='utf-8') as file_environment:
    json.dump(dict_environment, file_environment, indent=2, ensure_ascii=False)
print(str_integer_note)
print(f'resultados em {str_run_directory}')
