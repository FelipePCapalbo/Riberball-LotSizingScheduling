import importlib.metadata
import json
import os
import platform
import subprocess
from datetime import datetime

LEVEL_COLUMNS = ['status', 'segundos', 'work', 'nos', 'iteracoes', 'variaveis', 'binarias', 'restricoes',
                 'nao_zeros', 'gap_max', 'bateu_limite', 'objetivos', 'limitantes', 'gaps', 'custo_total']


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


def open_environment(str_environment_path, str_code_directory, str_variant, bool_quick, str_machine_label,
                     dict_settings):
    str_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str_code_directory, capture_output=True,
                                text=True).stdout.strip()
    str_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=str_code_directory,
                                capture_output=True, text=True).stdout.strip()
    str_dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=str_code_directory,
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
            'pasta_codigo': str_code_directory,
            'branch': str_branch,
            'commit': str_commit,
            'alteracoes_nao_commitadas': str_dirty,
            'threads': dict_settings['threads'],
            'limite_semanal': dict_settings['weekly_time_limit'],
            'limite_diario': dict_settings['daily_time_limit'],
            'inicio': datetime.now().isoformat(timespec='seconds'),
            'retomadas': [],
        }
    else:
        dict_environment['retomadas'].append({'inicio': datetime.now().isoformat(timespec='seconds'),
                                              'commit': str_commit, 'alteracoes_nao_commitadas': str_dirty})
    dict_environment['pid'] = os.getpid()
    dict_environment['situacao'] = 'em_execucao'
    return dict_environment
