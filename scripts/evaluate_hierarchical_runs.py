import argparse
import csv
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from processing.data import load_instance
from processing.settings import DEFAULT_SETTINGS
from optimization.monolithic_model import evaluate_monolithic_schedule

parser = argparse.ArgumentParser()
parser.add_argument('--rodada', required=True)
dict_arguments = vars(parser.parse_args())

str_run_directory = os.path.abspath(dict_arguments['rodada'])
str_solutions_directory = os.path.join(str_run_directory, 'solucoes')
str_runs_directory = os.path.join(str_run_directory, 'execucoes')
str_output_directory = os.path.join(str_run_directory, 'avaliacao_monolitica')
os.makedirs(str_output_directory, exist_ok=True)

list_csv_rows = []
for str_solution_file in sorted(os.listdir(str_solutions_directory)):
    str_case = str_solution_file[:-len('.json')]
    with open(os.path.join(str_solutions_directory, str_solution_file), encoding='utf-8') as file_solution:
        dict_solution = json.load(file_solution)
    with open(os.path.join(str_runs_directory, str_solution_file), encoding='utf-8') as file_run:
        dict_run = json.load(file_run)
    dict_settings = dict(DEFAULT_SETTINGS)
    for str_key in dict_run['parametros']:
        dict_settings[str_key] = dict_run['parametros'][str_key]
    dict_instance = load_instance(os.path.join(ROOT_DIR, 'data', dict_run['caso']['arquivo']))

    dict_record = {'id': str_case, 'arquivo': dict_run['caso']['arquivo'], 'semanas': dict_settings['weeks_in_plan'],
                   'semanas_detalhadas': dict_settings['frozen_weeks'], 'status_semanal': None,
                   'status_diario': None, 'avaliacao': None}
    if dict_solution['semanal'] is not None:
        dict_record['status_semanal'] = dict_solution['semanal']['status']
    if dict_solution['diario'] is not None:
        dict_record['status_diario'] = dict_solution['diario']['status']
        if dict_solution['diario']['status'] in ('Optimal', 'Feasible'):
            dict_record['avaliacao'] = evaluate_monolithic_schedule(dict_instance, dict_settings,
                                                                    dict_solution['diario']['schedule'],
                                                                    int(dict_settings['frozen_weeks']))
            dict_record['kpis_diario'] = dict_solution['diario']['kpis']
    with open(os.path.join(str_output_directory, str_solution_file), 'w', encoding='utf-8') as file_output:
        json.dump(dict_record, file_output, indent=2, ensure_ascii=False, default=str)

    dict_row = {'id': str_case, 'status_semanal': dict_record['status_semanal'],
                'status_diario': dict_record['status_diario']}
    for str_column in ['backlog_cost', 'lost_sales_cost', 'floor_slack_cost', 'form_setup_cost', 'color_setup_cost',
                       'setup_cost', 'holding_cost', 'total_cost', 'form_setup_hours', 'color_setup_hours',
                       'produced_kg', 'total_violation']:
        dict_row[str_column] = None
        if dict_record['avaliacao'] is not None:
            dict_row[str_column] = dict_record['avaliacao'][str_column]
    dict_row['estagios'] = None
    if dict_record['avaliacao'] is not None:
        list_stage_labels = []
        for float_value in dict_record['avaliacao']['stage_values']:
            list_stage_labels.append(str(float_value))
        dict_row['estagios'] = '|'.join(list_stage_labels)
    list_csv_rows.append(dict_row)
    print(f"{str_case}: {dict_row['estagios']} violacao={dict_row['total_violation']}")

if len(list_csv_rows) > 0:
    with open(os.path.join(str_run_directory, 'avaliacao_monolitica.csv'), 'w', encoding='utf-8',
              newline='') as file_csv:
        writer = csv.DictWriter(file_csv, fieldnames=list(list_csv_rows[0].keys()), delimiter=';')
        writer.writeheader()
        for dict_row in list_csv_rows:
            writer.writerow(dict_row)
print(f'avaliacao em {str_output_directory}')
