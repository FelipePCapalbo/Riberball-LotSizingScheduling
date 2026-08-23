import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT_DIR, 'config')

SECTIONS = {
    'scenario.json': ['start_week', 'weeks_in_plan', 'frozen_weeks', 'coverage_weeks'],
    'capacity.json': ['shifts_per_day', 'hours_per_shift', 'working_days_per_week'],
    'machines.json': ['active_machines', 'setup_hourly_cost_default', 'setup_hourly_cost_by_machine'],
    'costs.json': ['annual_holding_rate', 'order_backlog_multiplier', 'coverage_weight'],
    'solver.json': ['weekly_solver_name', 'weekly_time_limit', 'daily_solver_name',
                    'daily_time_limit', 'positions_per_shift', 'threads'],
}


def load_settings():
    dict_settings = {}
    for str_filename in SECTIONS:
        str_path = os.path.join(CONFIG_DIR, str_filename)
        with open(str_path, encoding='utf-8') as file_config:
            dict_settings.update(json.load(file_config))
    return dict_settings


def save_settings(dict_incoming):
    for str_filename in SECTIONS:
        list_keys = SECTIONS[str_filename]
        str_path = os.path.join(CONFIG_DIR, str_filename)
        with open(str_path, encoding='utf-8') as file_config:
            dict_existing = json.load(file_config)
        for str_key in list_keys:
            if str_key in dict_incoming:
                dict_existing[str_key] = dict_incoming[str_key]
        with open(str_path, 'w', encoding='utf-8') as file_config:
            json.dump(dict_existing, file_config, indent=4, ensure_ascii=False)
