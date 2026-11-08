import argparse
import csv
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHART_DIRECTORY = os.path.join(ROOT_DIR, 'dissertacao', 'dados', 'esforco')
SIZE_CSV = os.path.join(CHART_DIRECTORY, 'tamanho_modelos.csv')

parser = argparse.ArgumentParser()
parser.add_argument('--arquitetura', choices=['hierarquica', 'monolitica'], default=None)
parser.add_argument('--codigo', default=ROOT_DIR)
dict_arguments = vars(parser.parse_args())

sys.path.insert(0, os.path.abspath(dict_arguments['codigo']))

import pandas as pd

from processing.data import load_instance
from processing.settings import DEFAULT_SETTINGS
from experiment_common import ARCHITECTURE_CASES, ARCHITECTURE_SETTINGS

dict_captured = {}


def capture_problem(problem, *list_arguments):
    int_binaries = 0
    int_continuous = 0
    for variable in problem.variables():
        if variable.cat == 'Integer':
            int_binaries += 1
        else:
            int_continuous += 1
    int_nonzeros = 0
    for str_name in problem.constraints:
        int_nonzeros += len(problem.constraints[str_name])
    dict_captured['size'] = {'binaries': int_binaries, 'continuous': int_continuous,
                             'constraints': len(problem.constraints), 'nonzeros': int_nonzeros}
    return 'Not Solved', False, [], []


dict_rows = {}
if os.path.exists(SIZE_CSV):
    with open(SIZE_CSV, encoding='utf-8') as file_csv:
        for dict_row in csv.DictReader(file_csv, delimiter=';'):
            dict_rows[dict_row['caso']] = dict_row

if dict_arguments['arquitetura'] is not None:
    if dict_arguments['arquitetura'] == 'hierarquica':
        import optimization.weekly_model as weekly_module
        import optimization.daily_model as daily_module
        weekly_module.solve_lexicographic = capture_problem
        daily_module.solve_lexicographic = capture_problem
    elif dict_arguments['arquitetura'] == 'monolitica':
        from optimization.monolithic_model import run_monolithic_plan

    for dict_case in ARCHITECTURE_CASES:
        dict_instance = load_instance(os.path.join(dict_arguments['codigo'], 'data', dict_case['arquivo']))
        dict_settings = dict(DEFAULT_SETTINGS)
        for str_key in ARCHITECTURE_SETTINGS:
            dict_settings[str_key] = ARCHITECTURE_SETTINGS[str_key]
        dict_settings['weeks_in_plan'] = dict_case['semanas']
        dict_settings['solver_log_file'] = None
        if dict_case['id'] not in dict_rows:
            dict_rows[dict_case['id']] = {'caso': dict_case['id']}
        dict_row = dict_rows[dict_case['id']]

        if dict_arguments['arquitetura'] == 'hierarquica':
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
            dict_row['instancia'] = dict_case['arquivo']
            dict_row['semanas'] = dict_case['semanas']
            dict_row['baloes'] = len(dict_instance['products'])
            dict_row['maquinas'] = len(dict_instance['machines'])
            dict_row['maquinas_duas_cores'] = int_two_color
            dict_row['skus'] = int_skus
            dict_row['pares'] = int_pairs
            dict_row['pedidos'] = len(dict_instance['orders'])

            weekly_module.solve_weekly_model(weekly_module.build_weekly_scenario(dict_instance, dict_settings),
                                             dict_settings)
            for str_key in dict_captured['size']:
                dict_row[f'semanal_{str_key}'] = dict_captured['size'][str_key]

            dict_targets = {}
            timestamp_start = pd.Timestamp(dict_settings['start_week'])
            for str_product in dict_instance['products']:
                dict_targets[str_product] = {}
                for timestamp_week in dict_instance['weeks']:
                    if timestamp_week >= timestamp_start:
                        dict_targets[str_product][timestamp_week.strftime('%Y-%m-%d')] = 0.0
            daily_module.solve_daily_model(
                daily_module.build_daily_scenario(dict_instance, dict_settings, {'targets': dict_targets}), dict_settings)
            for str_key in dict_captured['size']:
                dict_row[f'operacional_{str_key}'] = dict_captured['size'][str_key]
        else:
            dict_settings['monolithic_max_nonzeros'] = 0
            dict_size = run_monolithic_plan(dict_settings, dict_instance)['size']
            dict_row['monolitico_binaries'] = dict_size['analytic']['binaries']
            dict_row['monolitico_continuous'] = dict_size['analytic']['continuous']
            dict_row['monolitico_constraints'] = dict_size['analytic']['constraints']
            dict_row['monolitico_nonzeros'] = dict_size['analytic']['nonzeros']
            dict_row['monolitico_memoria_gb'] = round(dict_size['analytic']['estimated_memory_mb'] / 1024.0, 2)
        print(dict_case['id'], dict_row)

    list_columns = ['caso']
    for str_case in dict_rows:
        for str_column in dict_rows[str_case]:
            if str_column not in list_columns:
                list_columns.append(str_column)
    os.makedirs(CHART_DIRECTORY, exist_ok=True)
    with open(SIZE_CSV, 'w', encoding='utf-8', newline='') as file_csv:
        writer = csv.DictWriter(file_csv, fieldnames=list_columns, delimiter=';', restval='')
        writer.writeheader()
        for dict_case in ARCHITECTURE_CASES:
            writer.writerow(dict_rows[dict_case['id']])
    print(f'tamanhos em {SIZE_CSV}')


def format_integer(str_value):
    return f'{int(float(str_value)):,}'.replace(',', '.')

def build_instance_label(dict_case, dict_row):
    if dict_case['id'].startswith('ajustado'):
        return 'Fábrica'
    else:
        return f"I{dict_row['baloes']}-K{dict_row['skus']}-J{dict_row['maquinas']}-T{dict_row['semanas']}"



bool_complete = True
for dict_case in ARCHITECTURE_CASES:
    if 'monolitico_binaries' not in dict_rows[dict_case['id']] or 'semanal_binaries' not in dict_rows[dict_case['id']]:
        bool_complete = False
    elif dict_rows[dict_case['id']]['monolitico_binaries'] == '' or dict_rows[dict_case['id']]['semanal_binaries'] == '':
        bool_complete = False

if bool_complete:
    list_instance_lines = ['\\begin{tabular}{@{}lrrrrrr@{}}', '\\toprule',
                           ' & & & \\multicolumn{2}{c}{Máquinas} & & \\\\', '\\cmidrule(lr){4-5}',
                           'Instância & Balões & SKU & Total & Duas cores & Pares & Pedidos \\\\', '\\midrule']
    list_seen_files = []
    for dict_case in ARCHITECTURE_CASES:
        dict_row = dict_rows[dict_case['id']]
        if dict_case['arquivo'] not in list_seen_files:
            list_seen_files.append(dict_case['arquivo'])
            str_label = build_instance_label(dict_case, dict_row)
            list_instance_lines.append(f"{str_label} & {dict_row['baloes']} & {dict_row['skus']} & "
                                       f"{dict_row['maquinas']} & {dict_row['maquinas_duas_cores']} & "
                                       f"{dict_row['pares']} & {format_integer(dict_row['pedidos'])} \\\\")
            if str_label == 'Fábrica':
                list_instance_lines.append('\\midrule')
    list_instance_lines.append('\\bottomrule')
    list_instance_lines.append('\\end{tabular}')
    with open(os.path.join(CHART_DIRECTORY, 'tabela_instancias.tex'), 'w', encoding='utf-8') as file_table:
        file_table.write('\n'.join(list_instance_lines) + '\n')

    dict_factory = dict_rows['ajustado_h13']
    list_factory_lines = ['\\begin{tabular}{@{}lrrrr@{}}', '\\toprule',
                          'Modelo & Binárias & Contínuas & Restrições & Não nulos \\\\', '\\midrule']
    for str_prefix, str_label in [('semanal', 'Nível semanal'), ('operacional', 'Nível operacional'),
                                  ('monolitico', 'Modelo integrado')]:
        list_factory_lines.append(f"{str_label} & {format_integer(dict_factory[str_prefix + '_binaries'])} & "
                                  f"{format_integer(dict_factory[str_prefix + '_continuous'])} & "
                                  f"{format_integer(dict_factory[str_prefix + '_constraints'])} & "
                                  f"{format_integer(dict_factory[str_prefix + '_nonzeros'])} \\\\")
    list_factory_lines.append('\\bottomrule')
    list_factory_lines.append('\\end{tabular}')
    with open(os.path.join(CHART_DIRECTORY, 'tabela_tamanho_fabrica.tex'), 'w', encoding='utf-8') as file_table:
        file_table.write('\n'.join(list_factory_lines) + '\n')

    list_synthetic_lines = ['\\begin{tabular}{@{}lrrr@{}}', '\\toprule',
                            'Instância & Nível semanal & Nível operacional & Modelo integrado \\\\',
                            '\\midrule']
    for dict_case in ARCHITECTURE_CASES:
        if not dict_case['id'].startswith('ajustado'):
            dict_row = dict_rows[dict_case['id']]
            str_label = build_instance_label(dict_case, dict_row)
            list_synthetic_lines.append(f"{str_label} & "
                                        f"{format_integer(dict_row['semanal_binaries'])} & "
                                        f"{format_integer(dict_row['operacional_binaries'])} & "
                                        f"{format_integer(dict_row['monolitico_binaries'])} \\\\")
    list_synthetic_lines.append('\\bottomrule')
    list_synthetic_lines.append('\\end{tabular}')
    with open(os.path.join(CHART_DIRECTORY, 'tabela_tamanho_sinteticas.tex'), 'w', encoding='utf-8') as file_table:
        file_table.write('\n'.join(list_synthetic_lines) + '\n')
    print('tabelas gravadas')
