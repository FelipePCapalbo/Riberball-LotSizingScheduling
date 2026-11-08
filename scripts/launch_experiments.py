import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ROOT = os.path.join(ROOT_DIR, 'experimentos', 'esforco_computacional')
RUNS_ROOT = os.path.join(OUTPUT_ROOT, 'rodadas')
LAUNCHES_ROOT = os.path.join(OUTPUT_ROOT, 'disparos')
WORKTREE_PREFIX = 'Riberball-wt-'

VARIANTS = {
    'formulacao': {'branch': None, 'folder': None},
    'rf_tempo': {'branch': 'exp/rf-tempo', 'folder': 'rf-tempo'},
    'rf_maquina': {'branch': 'exp/rf-maquina', 'folder': 'rf-maquina'},
    'rf_produto': {'branch': 'exp/rf-produto', 'folder': 'rf-produto'},
    'preprocessamento': {'branch': 'exp/preprocessamento-numba', 'folder': 'numba'},
    'warm_start': {'branch': 'exp/warm-start', 'folder': 'warm-start'},
    'cascata': {'branch': 'exp/cascata-negocio', 'folder': 'cascata'},
}
VARIANTS['classes_variaveis'] = {'branch': 'exp/classes-variaveis', 'folder': 'classes-variaveis'}
MONOLITHIC_TECHNIQUES = ['pura', 'desagregado', 'rf_tempo', 'rf_maquina', 'rf_produto', 'preprocessamento',
                         'warm_start', 'cascata']
for str_technique in MONOLITHIC_TECHNIQUES:
    VARIANTS[f'monolitico_{str_technique}'] = {'branch': 'exp/monolitico', 'folder': 'monolitico',
                                               'tecnica': str_technique}

parser = argparse.ArgumentParser()
parser.add_argument('variantes', nargs='*')
parser.add_argument('--bateria', choices=['esforco', 'arquitetura', 'classes'], default='esforco')
parser.add_argument('--apos', default=None)
parser.add_argument('--paralelo', type=int, default=3)
parser.add_argument('--rapido', action='store_true')
parser.add_argument('--threads', type=int, default=2)
parser.add_argument('--retomar', default=None)
parser.add_argument('--situacao', action='store_true')
parser.add_argument('--supervisor', default=None)
dict_arguments = vars(parser.parse_args())

if dict_arguments['supervisor'] is not None:
    with open(dict_arguments['supervisor'], encoding='utf-8') as file_launch:
        dict_launch = json.load(file_launch)
    if dict_launch['apos'] is not None:
        with open(dict_launch['apos'], encoding='utf-8') as file_previous:
            dict_previous = json.load(file_previous)
        bool_waiting = True
        while bool_waiting:
            bool_waiting = False
            for list_previous_wave in dict_previous['ondas']:
                for dict_previous_job in list_previous_wave:
                    str_previous_environment = os.path.join(dict_previous_job['pasta'], 'ambiente.json')
                    if not os.path.exists(str_previous_environment):
                        bool_waiting = True
                    else:
                        with open(str_previous_environment, encoding='utf-8') as file_previous_environment:
                            dict_previous_environment = json.load(file_previous_environment)
                        if dict_previous_environment['situacao'] != 'concluida':
                            bool_waiting = True
            if bool_waiting:
                time.sleep(60)
    for list_wave in dict_launch['ondas']:
        list_processes = []
        for dict_job in list_wave:
            os.makedirs(dict_job['pasta'], exist_ok=True)
            file_output = open(os.path.join(dict_job['pasta'], 'saida.out'), 'a', encoding='utf-8')
            if dict_job['bateria'] == 'classes':
                list_command = [dict_job['python'], os.path.join(dict_job['codigo'], 'scripts',
                                                                'variable_class_test.py'),
                                '--saida', OUTPUT_ROOT, '--pasta', dict_job['pasta'], '--threads', '1']
            elif dict_job['bateria'] == 'arquitetura':
                list_command = [dict_job['python'], os.path.join(ROOT_DIR, 'scripts', 'architecture_experiments.py'),
                                '--codigo', dict_job['codigo'], '--arquitetura', dict_job['arquitetura'],
                                '--tecnica', dict_job['tecnica'], '--variante', dict_job['variante'],
                                '--saida', OUTPUT_ROOT, '--pasta', dict_job['pasta'],
                                '--threads', str(dict_job['threads'])]
            else:
                list_command = [dict_job['python'], os.path.join(dict_job['codigo'], 'scripts',
                                                                'computational_experiments.py'),
                                '--variante', dict_job['variante'], '--saida', OUTPUT_ROOT,
                                '--pasta', dict_job['pasta'], '--threads', str(dict_job['threads'])]
            if dict_job['rapido']:
                list_command.append('--rapido')
            list_processes.append([subprocess.Popen(list_command, cwd=dict_job['codigo'], stdout=file_output,
                                                    stderr=subprocess.STDOUT), file_output])
        for list_process in list_processes:
            list_process[0].wait()
            list_process[1].close()

elif dict_arguments['situacao']:
    list_folders = []
    if os.path.exists(RUNS_ROOT):
        list_folders = sorted(os.listdir(RUNS_ROOT))
    print(f"{'rodada':58s} {'feitas':>9s}  situacao")
    for str_folder in list_folders:
        str_environment_path = os.path.join(RUNS_ROOT, str_folder, 'ambiente.json')
        if os.path.exists(str_environment_path):
            with open(str_environment_path, encoding='utf-8') as file_environment:
                dict_environment = json.load(file_environment)
            int_done = len(os.listdir(os.path.join(RUNS_ROOT, str_folder, 'execucoes')))
            str_state = dict_environment['situacao']
            if str_state == 'em_execucao' and os.path.exists('/proc'):
                if not os.path.exists(f"/proc/{dict_environment['pid']}"):
                    str_state = 'interrompida'
            str_planned = '?'
            if 'execucoes_planejadas' in dict_environment:
                str_planned = str(dict_environment['execucoes_planejadas'])
            print(f'{str_folder:58s} {int_done:>4d}/{str_planned:<4s}  {str_state}')
        else:
            print(f'{str_folder:58s} {"":>9s}  aguardando')

else:
    str_machine_label = os.environ.get('EXPERIMENT_MACHINE_LABEL', platform.node()).lower().replace(' ', '-')
    str_stamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    list_jobs = []
    if dict_arguments['retomar'] is not None:
        str_folder = os.path.abspath(dict_arguments['retomar'])
        with open(os.path.join(str_folder, 'ambiente.json'), encoding='utf-8') as file_environment:
            dict_environment = json.load(file_environment)
        str_battery = 'esforco'
        if 'bateria' in dict_environment:
            str_battery = dict_environment['bateria']
        list_jobs.append({'variante': dict_environment['variante'], 'pasta': str_folder, 'bateria': str_battery,
                          'rapido': dict_environment['rapido'], 'threads': dict_environment['threads']})
    else:
        list_names = dict_arguments['variantes']
        if list_names == ['todas']:
            list_names = []
            for str_name in VARIANTS:
                if dict_arguments['bateria'] == 'arquitetura' or 'tecnica' not in VARIANTS[str_name]:
                    if str_name != 'classes_variaveis':
                        list_names.append(str_name)
        for str_name in list_names:
            str_folder_name = f'{str_stamp}_{str_machine_label}_{str_name}'
            if dict_arguments['bateria'] == 'arquitetura':
                str_folder_name = f'{str_stamp}_{str_machine_label}_arquitetura_{str_name}'
            if dict_arguments['bateria'] == 'classes':
                str_folder_name = f'{str_stamp}_{str_machine_label}_classes_variaveis'
            if dict_arguments['rapido']:
                str_folder_name = f'{str_folder_name}_rapido'
            list_jobs.append({'variante': str_name, 'pasta': os.path.join(RUNS_ROOT, str_folder_name),
                              'bateria': dict_arguments['bateria'], 'rapido': dict_arguments['rapido'],
                              'threads': dict_arguments['threads']})

    for dict_job in list_jobs:
        dict_variant = VARIANTS[dict_job['variante']]
        if dict_variant['folder'] is None:
            str_code_directory = ROOT_DIR
        else:
            str_code_directory = os.path.join(os.path.dirname(ROOT_DIR), WORKTREE_PREFIX + dict_variant['folder'])
            if not os.path.exists(str_code_directory):
                subprocess.run(['git', 'worktree', 'add', str_code_directory, dict_variant['branch']], cwd=ROOT_DIR,
                               check=True)
        str_python = sys.executable
        if os.path.exists(os.path.join(str_code_directory, '.venv', 'bin', 'python')):
            str_python = os.path.join(str_code_directory, '.venv', 'bin', 'python')
        dict_job['codigo'] = str_code_directory
        dict_job['python'] = str_python
        dict_job['arquitetura'] = 'hierarquica'
        dict_job['tecnica'] = 'pura'
        if 'tecnica' in dict_variant:
            dict_job['arquitetura'] = 'monolitica'
            dict_job['tecnica'] = dict_variant['tecnica']

    list_waves = []
    for int_start in range(0, len(list_jobs), dict_arguments['paralelo']):
        list_waves.append(list_jobs[int_start:int_start + dict_arguments['paralelo']])

    os.makedirs(LAUNCHES_ROOT, exist_ok=True)
    str_launch_path = os.path.join(LAUNCHES_ROOT, f'{str_stamp}_{str_machine_label}.json')
    str_previous_launch = None
    if dict_arguments['apos'] is not None:
        str_previous_launch = os.path.abspath(dict_arguments['apos'])
    with open(str_launch_path, 'w', encoding='utf-8') as file_launch:
        json.dump({'maquina': str_machine_label, 'inicio': str_stamp, 'bateria': dict_arguments['bateria'],
                   'paralelo': dict_arguments['paralelo'], 'apos': str_previous_launch, 'ondas': list_waves},
                  file_launch, indent=2, ensure_ascii=False)
    file_supervisor_log = open(str_launch_path.replace('.json', '.log'), 'a', encoding='utf-8')
    subprocess.Popen([sys.executable, os.path.abspath(__file__), '--supervisor', str_launch_path], cwd=ROOT_DIR,
                     stdout=file_supervisor_log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     start_new_session=True)

    print(f'disparo gravado em {os.path.relpath(str_launch_path, ROOT_DIR)}')
    if str_previous_launch is not None:
        print(f'aguarda o fim de {os.path.relpath(str_previous_launch, ROOT_DIR)}')
    int_wave = 0
    for list_wave in list_waves:
        int_wave += 1
        print(f'onda {int_wave}:')
        for dict_job in list_wave:
            print(f"  {dict_job['variante']:18s} {os.path.relpath(dict_job['pasta'], ROOT_DIR)}")
    print('acompanhar: python scripts/launch_experiments.py --situacao')
