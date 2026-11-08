import json

from processing.database import connect_database, fetch_rows

DEFAULT_SETTINGS = {
    'start_week': '2024-01-01',
    'weeks_in_plan': 13,
    'frozen_weeks': 1,
    'shifts_per_day': 3,
    'hours_per_shift': 8,
    'working_days_per_week': 7,
    'warehouse_capacity_kg': None,
    'annual_holding_rate': 0.25,
    'weekly_solver_name': 'ORTOOLS',
    'weekly_time_limit': 300,
    'daily_solver_name': 'ORTOOLS',
    'daily_time_limit': 600,
    'threads': None,
    'solver_seed': 0,
    'solver_log_file': None,
    'monolithic_technique': 'pura',
    'monolithic_time_limit': 900,
    'monolithic_max_nonzeros': 30_000_000,
    'monolithic_rf_tempo_block_size': 1,
    'monolithic_rf_maquina_block_size': 7,
    'monolithic_rf_produto_block_size': 5,
    'monolithic_fo_time_share': 0.3,
    'monolithic_cascade_time_share': 0.5,
    'monolithic_cascade_tie_breaker': 0.0001,
}


def load_settings():
    dict_settings = dict(DEFAULT_SETTINGS)
    connection = connect_database()
    for dict_row in fetch_rows(connection, 'SELECT key, value FROM settings', ()):
        if dict_row['key'] in dict_settings:
            dict_settings[dict_row['key']] = json.loads(dict_row['value'])
    connection.close()
    return dict_settings


def save_settings(dict_incoming):
    connection = connect_database()
    for str_key in DEFAULT_SETTINGS:
        if str_key in dict_incoming:
            connection.execute(
                'INSERT INTO settings (key, value) VALUES (?, ?) '
                'ON CONFLICT (key) DO UPDATE SET value = excluded.value',
                (str_key, json.dumps(dict_incoming[str_key])))
    connection.commit()
    connection.close()
