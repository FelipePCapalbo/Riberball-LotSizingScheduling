import argparse
import csv
import json
import math
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RESULTS_ROOT = os.path.join(ROOT_DIR, 'experimentos', 'esforco_computacional')
CHART_DIRECTORY = os.path.join(ROOT_DIR, 'dissertacao', 'dados', 'esforco')
REFERENCE_VARIANT = 'formulacao'
WORK_SHIFT = 1.0

FACTOR_LABELS = {
    'maquinas': 'Máquinas ativas',
    'baloes': 'Balões',
    'cores': 'Cores por balão',
    'flexibilidade': 'Flexibilidade balão-máquina',
    'demanda': 'Demanda',
    'estoque': 'Estoque inicial',
    'capacidade': 'Capacidade',
    'setup': 'Tempos de setup',
    'duas_cores': 'Máquinas de duas cores',
    'horizonte': 'Horizonte semanal',
    'congeladas': 'Semanas congeladas',
}
LEVELS = ['semanal', 'diario']


def read_numeric(str_value):
    float_value = None
    if str_value not in (None, '', 'None'):
        float_value = float(str_value)
    return float_value


def shifted_geometric_mean(list_values):
    float_log_sum = 0.0
    for float_value in list_values:
        float_log_sum += math.log(float_value + WORK_SHIFT)
    return math.exp(float_log_sum / len(list_values)) - WORK_SHIFT


def write_table(str_path, list_columns, list_rows):
    with open(str_path, 'w', encoding='utf-8', newline='') as file_csv:
        writer = csv.writer(file_csv, delimiter=';')
        writer.writerow(list_columns)
        for list_row in list_rows:
            list_formatted = []
            for value_cell in list_row:
                if value_cell is None:
                    list_formatted.append('nan')
                elif isinstance(value_cell, float):
                    list_formatted.append(f'{value_cell:.6g}')
                else:
                    list_formatted.append(value_cell)
            writer.writerow(list_formatted)


parser = argparse.ArgumentParser()
parser.add_argument('--saida', default=DEFAULT_RESULTS_ROOT)
parser.add_argument('--referencia', default=REFERENCE_VARIANT)
parser.add_argument('--maquina', default=None)
parser.add_argument('--incluir-rapidas', action='store_true')
dict_arguments = vars(parser.parse_args())
str_results_root = os.path.abspath(dict_arguments['saida'])
str_reference_variant = dict_arguments['referencia']
os.makedirs(CHART_DIRECTORY, exist_ok=True)

with open(os.path.join(str_results_root, 'plano.json'), encoding='utf-8') as file_plan:
    dict_plan = json.load(file_plan)

str_runs_root = os.path.join(str_results_root, 'rodadas')
dict_variant_rows = {}
dict_variant_folder = {}
for str_name in sorted(os.listdir(str_runs_root)):
    str_environment_path = os.path.join(str_runs_root, str_name, 'ambiente.json')
    str_csv_path = os.path.join(str_runs_root, str_name, 'resultados.csv')
    if os.path.exists(str_environment_path) and os.path.exists(str_csv_path):
        with open(str_environment_path, encoding='utf-8') as file_environment:
            dict_environment = json.load(file_environment)
        bool_selected = True
        if dict_environment['rapido'] and not dict_arguments['incluir_rapidas']:
            bool_selected = False
        if dict_arguments['maquina'] is not None and dict_environment['maquina'] != dict_arguments['maquina']:
            bool_selected = False
        if bool_selected:
            list_rows = []
            with open(str_csv_path, encoding='utf-8') as file_csv:
                for dict_row in csv.DictReader(file_csv, delimiter=';'):
                    list_rows.append(dict_row)
            dict_variant_rows[dict_environment['variante']] = list_rows
            dict_variant_folder[dict_environment['variante']] = str_name
for str_variant in dict_variant_folder:
    print(f'{str_variant}: rodadas/{dict_variant_folder[str_variant]}')

list_reference_rows = dict_variant_rows[str_reference_variant]

dict_baseline_work = {}
dict_noise = {}
for str_level in LEVELS:
    list_baseline_work = []
    for dict_row in list_reference_rows:
        if dict_row['fase'] == 'base' and read_numeric(dict_row[f'{str_level}_work']) is not None:
            list_baseline_work.append(read_numeric(dict_row[f'{str_level}_work']))
    list_baseline_work.sort()
    dict_baseline_work[str_level] = list_baseline_work[len(list_baseline_work) // 2]
    dict_noise[str_level] = [list_baseline_work[0], list_baseline_work[-1]]
write_table(os.path.join(CHART_DIRECTORY, 'ruido_base.csv'),
            ['nivel', 'work_mediana', 'work_min', 'work_max'],
            [['semanal', dict_baseline_work['semanal'], dict_noise['semanal'][0], dict_noise['semanal'][1]],
             ['diario', dict_baseline_work['diario'], dict_noise['diario'][0], dict_noise['diario'][1]]])

list_tornado_rows = []
for dict_factor in dict_plan['fatores']:
    str_factor = dict_factor['name']
    list_ofat_rows = []
    list_levels = []
    for value_level in dict_factor['levels']:
        list_level_rows = []
        if value_level == dict_factor['baseline']:
            for dict_row in list_reference_rows:
                if dict_row['fase'] == 'base' and dict_row['semente_solver'] == '0':
                    list_level_rows.append(dict_row)
        else:
            for dict_row in list_reference_rows:
                if (dict_row['fase'] == 'ofat' and dict_row['fator_a'] == str_factor
                        and float(dict_row['nivel_a']) == float(value_level)):
                    list_level_rows.append(dict_row)
        if len(list_level_rows) > 0:
            list_levels.append(value_level)
            list_cells = [value_level, 0]
            if value_level == dict_factor['baseline']:
                list_cells[1] = 1
            for str_level in LEVELS:
                list_work = []
                list_seconds = []
                float_worst_gap = None
                bool_hit_limit = False
                bool_any_executed = False
                for dict_row in list_level_rows:
                    float_work = read_numeric(dict_row[f'{str_level}_work'])
                    if float_work is not None:
                        bool_any_executed = True
                        list_work.append(float_work)
                        list_seconds.append(read_numeric(dict_row[f'{str_level}_segundos']))
                        float_gap = read_numeric(dict_row[f'{str_level}_gap_max'])
                        if float_gap is not None and (float_worst_gap is None or float_gap > float_worst_gap):
                            float_worst_gap = float_gap
                        if dict_row[f'{str_level}_bateu_limite'] == 'True':
                            bool_hit_limit = True
                float_level_work = None
                float_level_seconds = None
                float_limit_marker = None
                if bool_any_executed:
                    float_level_work = shifted_geometric_mean(list_work)
                    float_level_seconds = shifted_geometric_mean(list_seconds)
                    if bool_hit_limit:
                        float_limit_marker = float_level_work
                list_cells.append(float_level_work)
                list_cells.append(float_level_seconds)
                list_cells.append(float_worst_gap)
                list_cells.append(float_limit_marker)
            list_ofat_rows.append(list_cells)
    list_columns = ['nivel', 'base']
    for str_level in LEVELS:
        list_columns.append(f'{str_level}_work')
        list_columns.append(f'{str_level}_segundos')
        list_columns.append(f'{str_level}_gap')
        list_columns.append(f'{str_level}_limite')
    write_table(os.path.join(CHART_DIRECTORY, f'ofat_{str_factor}.csv'), list_columns, list_ofat_rows)

    list_tornado_cells = [FACTOR_LABELS[str_factor]]
    int_column = 2
    for str_level in LEVELS:
        float_low = None
        float_high = None
        for list_cells in list_ofat_rows:
            if list_cells[int_column] is not None:
                float_ratio = math.log10((list_cells[int_column] + WORK_SHIFT)
                                         / (dict_baseline_work[str_level] + WORK_SHIFT))
                if float_low is None or float_ratio < float_low:
                    float_low = float_ratio
                if float_high is None or float_ratio > float_high:
                    float_high = float_ratio
        list_tornado_cells.append(float_low)
        list_tornado_cells.append(float_high)
        int_column += 4
    list_tornado_rows.append(list_tornado_cells)

list_sorted_tornado = []
list_remaining = list(list_tornado_rows)
while len(list_remaining) > 0:
    list_smallest = list_remaining[0]
    for list_candidate in list_remaining:
        float_candidate_range = 0.0
        if list_candidate[3] is not None:
            float_candidate_range = list_candidate[4] - list_candidate[3]
        float_smallest_range = 0.0
        if list_smallest[3] is not None:
            float_smallest_range = list_smallest[4] - list_smallest[3]
        if float_candidate_range < float_smallest_range:
            list_smallest = list_candidate
    list_sorted_tornado.append(list_smallest)
    list_remaining.remove(list_smallest)
list_tornado_output = []
int_position = 0
for list_cells in list_sorted_tornado:
    list_output = [int_position, list_cells[0]]
    int_cell = 1
    while int_cell < len(list_cells):
        float_low = list_cells[int_cell]
        float_high = list_cells[int_cell + 1]
        if float_low is None:
            list_output.append(None)
            list_output.append(None)
        else:
            list_output.append((float_low + float_high) / 2.0)
            list_output.append((float_high - float_low) / 2.0)
        int_cell += 2
    list_tornado_output.append(list_output)
    int_position += 1
write_table(os.path.join(CHART_DIRECTORY, 'tornado.csv'),
            ['posicao', 'rotulo', 'semanal_centro', 'semanal_meia', 'diario_centro', 'diario_meia'],
            list_tornado_output)

int_grid = 0
for list_grid in dict_plan['grades']:
    int_grid += 1
    str_factor_a = list_grid[0][0]
    str_factor_b = list_grid[1][0]
    list_grid_rows = []
    int_index_b = 0
    for value_level_b in list_grid[1][1]:
        int_index_a = 0
        for value_level_a in list_grid[0][1]:
            dict_found = None
            for dict_row in list_reference_rows:
                if (dict_row['fase'] == 'grade' and dict_row['fator_a'] == str_factor_a
                        and dict_row['fator_b'] == str_factor_b
                        and float(dict_row['nivel_a']) == float(value_level_a)
                        and float(dict_row['nivel_b']) == float(value_level_b)):
                    dict_found = dict_row
            list_cells = [int_index_a, int_index_b, value_level_a, value_level_b]
            for str_level in LEVELS:
                float_work = None
                float_gap = None
                if dict_found is not None:
                    float_work = read_numeric(dict_found[f'{str_level}_work'])
                    float_gap = read_numeric(dict_found[f'{str_level}_gap_max'])
                if float_work is None:
                    list_cells.append(None)
                else:
                    list_cells.append(math.log10(float_work + WORK_SHIFT))
                list_cells.append(float_gap)
            list_grid_rows.append(list_cells)
            int_index_a += 1
        int_index_b += 1
    write_table(os.path.join(CHART_DIRECTORY, f'grade_{int_grid}_{str_factor_a}_{str_factor_b}.csv'),
                ['i', 'j', 'nivel_a', 'nivel_b', 'semanal_log_work', 'semanal_gap', 'diario_log_work', 'diario_gap'],
                list_grid_rows)

list_size_rows = []
for dict_row in list_reference_rows:
    list_cells = [dict_row['id']]
    for str_level in LEVELS:
        list_cells.append(read_numeric(dict_row[f'{str_level}_binarias']))
        list_cells.append(read_numeric(dict_row[f'{str_level}_work']))
    list_size_rows.append(list_cells)
write_table(os.path.join(CHART_DIRECTORY, 'tamanho.csv'),
            ['id', 'semanal_binarias', 'semanal_work', 'diario_binarias', 'diario_work'], list_size_rows)

list_variants = []
for str_name in dict_variant_rows:
    if str_name != str_reference_variant:
        list_variants.append(str_name)
if len(list_variants) > 0:
    str_comparison_directory = os.path.join(str_results_root, 'comparativo')
    os.makedirs(str_comparison_directory, exist_ok=True)
    dict_reference_by_id = {}
    for dict_row in list_reference_rows:
        dict_reference_by_id[dict_row['id']] = dict_row
    dict_rows_by_variant_id = {}
    for str_variant in list_variants:
        dict_rows_by_variant_id[str_variant] = {}
        for dict_row in dict_variant_rows[str_variant]:
            dict_rows_by_variant_id[str_variant][dict_row['id']] = dict_row

    list_summary_rows = []
    for str_level in LEVELS:
        for str_variant in list_variants:
            list_work_ratios = []
            list_time_ratios = []
            list_primal_gaps = []
            for str_id in dict_reference_by_id:
                if str_id in dict_rows_by_variant_id[str_variant]:
                    dict_reference = dict_reference_by_id[str_id]
                    dict_variant = dict_rows_by_variant_id[str_variant][str_id]
                    float_reference_work = read_numeric(dict_reference[f'{str_level}_work'])
                    float_variant_work = read_numeric(dict_variant[f'{str_level}_work'])
                    if float_reference_work is not None and float_variant_work is not None:
                        list_work_ratios.append((float_variant_work + WORK_SHIFT)
                                                / (float_reference_work + WORK_SHIFT))
                        list_time_ratios.append((read_numeric(dict_variant[f'{str_level}_segundos']) + WORK_SHIFT)
                                                / (read_numeric(dict_reference[f'{str_level}_segundos'])
                                                   + WORK_SHIFT))
                        list_reference_objectives = dict_reference[f'{str_level}_objetivos'].split('|')
                        list_variant_objectives = dict_variant[f'{str_level}_objetivos'].split('|')
                        list_reference_bounds = dict_reference[f'{str_level}_limitantes'].split('|')
                        int_last = len(list_reference_objectives) - 1
                        if (len(list_variant_objectives) == len(list_reference_objectives)
                                and list_variant_objectives[int_last] != 'None'
                                and list_reference_bounds[int_last] != 'None'):
                            float_variant_objective = float(list_variant_objectives[int_last])
                            float_bound = float(list_reference_bounds[int_last])
                            if abs(float_variant_objective) > 1.0:
                                list_primal_gaps.append((float_variant_objective - float_bound)
                                                        / abs(float_variant_objective))
            if len(list_work_ratios) > 0:
                float_log_work = 0.0
                for float_ratio in list_work_ratios:
                    float_log_work += math.log(float_ratio)
                float_log_time = 0.0
                for float_ratio in list_time_ratios:
                    float_log_time += math.log(float_ratio)
                float_mean_gap = None
                if len(list_primal_gaps) > 0:
                    float_mean_gap = 0.0
                    for float_gap in list_primal_gaps:
                        float_mean_gap += float_gap
                    float_mean_gap = float_mean_gap / len(list_primal_gaps)
                list_summary_rows.append([str_level, str_variant, len(list_work_ratios),
                                          math.exp(float_log_work / len(list_work_ratios)),
                                          math.exp(float_log_time / len(list_time_ratios)), float_mean_gap])
    write_table(os.path.join(str_comparison_directory, 'resumo_variantes.csv'),
                ['nivel', 'variante', 'execucoes', 'razao_work', 'razao_tempo', 'gap_primal_medio'],
                list_summary_rows)
    write_table(os.path.join(CHART_DIRECTORY, 'resumo_variantes.csv'),
                ['nivel', 'variante', 'execucoes', 'razao_work', 'razao_tempo', 'gap_primal_medio'],
                list_summary_rows)

    for str_level in LEVELS:
        list_all_variants = [str_reference_variant]
        for str_variant in list_variants:
            list_all_variants.append(str_variant)
        dict_ratios = {}
        for str_variant in list_all_variants:
            dict_ratios[str_variant] = []
        for str_id in dict_reference_by_id:
            dict_seconds = {}
            bool_complete = True
            for str_variant in list_all_variants:
                dict_row = None
                if str_variant == str_reference_variant:
                    dict_row = dict_reference_by_id[str_id]
                elif str_id in dict_rows_by_variant_id[str_variant]:
                    dict_row = dict_rows_by_variant_id[str_variant][str_id]
                if dict_row is None or read_numeric(dict_row[f'{str_level}_segundos']) is None:
                    bool_complete = False
                else:
                    dict_seconds[str_variant] = read_numeric(dict_row[f'{str_level}_segundos'])
            if bool_complete:
                float_best = None
                for str_variant in dict_seconds:
                    if float_best is None or dict_seconds[str_variant] < float_best:
                        float_best = dict_seconds[str_variant]
                for str_variant in dict_seconds:
                    dict_ratios[str_variant].append(dict_seconds[str_variant] / float_best)
        list_thresholds = [1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0]
        list_profile_rows = []
        for float_threshold in list_thresholds:
            list_cells = [float_threshold]
            for str_variant in list_all_variants:
                int_within = 0
                for float_ratio in dict_ratios[str_variant]:
                    if float_ratio <= float_threshold:
                        int_within += 1
                float_share = None
                if len(dict_ratios[str_variant]) > 0:
                    float_share = int_within / len(dict_ratios[str_variant])
                list_cells.append(float_share)
            list_profile_rows.append(list_cells)
        list_profile_columns = ['tau']
        for str_variant in list_all_variants:
            list_profile_columns.append(str_variant)
        write_table(os.path.join(CHART_DIRECTORY, f'perfil_desempenho_{str_level}.csv'), list_profile_columns,
                    list_profile_rows)

print(f'graficos em {CHART_DIRECTORY}')
