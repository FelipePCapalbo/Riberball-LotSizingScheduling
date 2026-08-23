import os
import json
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR = os.path.join(ROOT_DIR, 'history')


def save_weekly_run(dict_settings, dict_result, float_seconds, str_label, str_data_file):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    str_run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19]
    dict_record = {
        'id': str_run_id,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'label': str_label or str_run_id,
        'data_file': str_data_file,
        'inputs': dict_settings,
        'weekly': {
            'status': dict_result['status'],
            'duration_seconds': round(float_seconds, 2),
            'kpis': dict_result['kpis'],
            'weeks': dict_result['weeks'],
            'production': dict_result['production'],
            'inventory': dict_result['inventory'],
            'demand': dict_result['demand'],
            'targets': dict_result['targets'],
        },
        'daily': None,
    }
    str_path = os.path.join(HISTORY_DIR, f'{str_run_id}.json')
    with open(str_path, 'w', encoding='utf-8') as file_record:
        json.dump(dict_record, file_record, indent=2, ensure_ascii=False)
    return str_run_id


def save_daily_run(str_run_id, dict_result, float_seconds):
    str_path = os.path.join(HISTORY_DIR, f'{str_run_id}.json')
    if os.path.exists(str_path):
        with open(str_path, encoding='utf-8') as file_record:
            dict_record = json.load(file_record)
        dict_record['daily'] = {
            'status': dict_result['status'],
            'duration_seconds': round(float_seconds, 2),
            'kpis': dict_result['kpis'],
            'shifts': dict_result.get('shifts', 0),
            'schedule': dict_result.get('schedule', []),
            'orders': dict_result.get('orders', []),
            'targets': dict_result.get('targets', []),
        }
        with open(str_path, 'w', encoding='utf-8') as file_record:
            json.dump(dict_record, file_record, indent=2, ensure_ascii=False)


def list_runs():
    if not os.path.isdir(HISTORY_DIR):
        return []
    list_records = []
    for str_name in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if str_name.endswith('.json'):
            with open(os.path.join(HISTORY_DIR, str_name), encoding='utf-8') as file_record:
                dict_record = json.load(file_record)
            if 'weekly' in dict_record:
                dict_summary = {
                    'id': dict_record['id'],
                    'timestamp': dict_record['timestamp'],
                    'label': dict_record['label'],
                    'data_file': dict_record['data_file'],
                    'start_week': dict_record['inputs'].get('start_week'),
                    'weeks_in_plan': dict_record['inputs'].get('weeks_in_plan'),
                    'machines': len(dict_record['inputs'].get('active_machines', [])),
                    'weekly_kpis': dict_record['weekly']['kpis'],
                    'weekly_duration': dict_record['weekly']['duration_seconds'],
                    'daily_kpis': None,
                    'daily_duration': None,
                }
                if dict_record['daily']:
                    dict_summary['daily_kpis'] = dict_record['daily']['kpis']
                    dict_summary['daily_duration'] = dict_record['daily']['duration_seconds']
                list_records.append(dict_summary)
    return list_records


def get_run(str_run_id):
    str_path = os.path.join(HISTORY_DIR, f'{str_run_id}.json')
    if not os.path.exists(str_path):
        return None
    with open(str_path, encoding='utf-8') as file_record:
        return json.load(file_record)
