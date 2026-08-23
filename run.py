import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processing.data import load_instance, list_data_files, DATA_DIR
from processing.settings import load_settings
from optimization.planner import run_weekly_plan, run_daily_plan


dict_settings = load_settings()
list_files = list_data_files()
if len(sys.argv) > 1:
    str_file = sys.argv[1]
else:
    str_file = list_files[0]
dict_instance = load_instance(os.path.join(DATA_DIR, str_file))

print(f'instancia: {str_file}')
print(f'produtos={len(dict_instance["products"])} maquinas={len(dict_instance["machines"])} '
      f'semanas={len(dict_instance["weeks"])} pedidos={len(dict_instance["orders"])}')

float_started_at = time.perf_counter()
dict_weekly = run_weekly_plan(dict_settings, dict_instance)
float_weekly_seconds = time.perf_counter() - float_started_at
print(f'\nplano semanal: {dict_weekly["status"]} em {float_weekly_seconds:.1f}s')
if dict_weekly['status'] in ('Optimal', 'Feasible'):
    for str_key in dict_weekly['kpis']:
        print(f'  {str_key:24s} {dict_weekly["kpis"][str_key]:,.2f}')

    float_started_at = time.perf_counter()
    dict_daily = run_daily_plan(dict_settings, dict_instance, dict_weekly)
    float_daily_seconds = time.perf_counter() - float_started_at
    print(f'\nprogramacao por turno: {dict_daily["status"]} em {float_daily_seconds:.1f}s')
    if dict_daily['status'] in ('Optimal', 'Feasible'):
        for str_key in dict_daily['kpis']:
            print(f'  {str_key:24s} {dict_daily["kpis"][str_key]:,.2f}')

    with open('results.json', 'w', encoding='utf-8') as file_results:
        json.dump({'weekly': dict_weekly, 'daily': dict_daily}, file_results,
                  indent=2, ensure_ascii=False)
    print('\nresultado completo gravado em results.json')
