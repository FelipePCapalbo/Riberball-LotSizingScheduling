import json

from processing.database import connect_database, fetch_rows


def get_run(str_run_id):
    connection = connect_database()
    if str_run_id is None:
        list_rows = fetch_rows(connection, 'SELECT * FROM runs ORDER BY created_at DESC, run_id DESC LIMIT 1', ())
    else:
        list_rows = fetch_rows(connection, 'SELECT * FROM runs WHERE run_id = ?', (str_run_id,))
    connection.close()
    dict_record = None
    if list_rows:
        dict_row = list_rows[0]
        dict_weekly = json.loads(dict_row['weekly_result'])
        dict_weekly['duration_seconds'] = dict_row['weekly_duration']
        dict_record = {
            'id': dict_row['run_id'],
            'timestamp': dict_row['created_at'],
            'label': dict_row['label'],
            'snapshot_id': dict_row['snapshot_id'],
            'source': dict_row['source'],
            'inputs': json.loads(dict_row['settings']),
            'weekly': dict_weekly,
            'daily': None,
        }
        if dict_row['daily_result'] is not None:
            dict_daily = json.loads(dict_row['daily_result'])
            dict_daily['duration_seconds'] = dict_row['daily_duration']
            dict_record['daily'] = dict_daily
    return dict_record
