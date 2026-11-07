import io
import json
import os
import sys
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import HOST, PORT, SHARED_SECRET
from backend.lifecycle import lifespan
from optimization.planner import run_weekly_plan, run_daily_plan
from processing.data import SNAPSHOT_SHEETS, fill_master_defaults, load_snapshot_instance, read_workbook_tables
from processing.database import MASTER_TABLES, SNAPSHOT_TABLES, connect_database, fetch_rows
from processing.history import get_run
from processing.settings import load_settings, save_settings
from processing.uploads import get_active_snapshot_id, get_upload_review, set_active_snapshot_id

app = FastAPI(lifespan=lifespan)


@app.middleware('http')
async def check_shared_secret(request, call_next):
    if request.url.path.startswith('/api/') and request.headers.get('authorization') != f'Bearer {SHARED_SECRET}':
        response = JSONResponse({'error': 'unauthorized'}, status_code=401)
    else:
        response = await call_next(request)
    return response


@app.get('/api/health')
async def get_health():
    return {'status': 'ok'}


@app.get('/api/snapshots')
async def get_snapshots():
    connection = connect_database()
    list_rows = fetch_rows(connection, 'SELECT * FROM snapshots ORDER BY snapshot_id DESC', ())
    connection.close()
    list_snapshots = []
    for dict_row in list_rows:
        list_snapshots.append({
            'snapshot_id': dict_row['snapshot_id'],
            'created_at': dict_row['created_at'],
            'source_file': dict_row['source_file'],
            'sheets': json.loads(dict_row['sheets']),
        })
    return {'snapshots': list_snapshots, 'active': get_active_snapshot_id()}


@app.post('/api/snapshots/active')
async def post_active_snapshot(request: Request):
    dict_body = await request.json()
    connection = connect_database()
    set_active_snapshot_id(connection, int(dict_body['snapshot_id']))
    connection.commit()
    connection.close()
    return {'status': 'ok', 'active': int(dict_body['snapshot_id'])}


@app.post('/api/uploads')
async def post_upload(request: Request):
    bytes_content = await request.body()
    str_source_file = request.query_params.get('filename', 'upload.xlsx')
    dict_tables, list_complete_tables, list_sheets = read_workbook_tables(io.BytesIO(bytes_content))
    connection = connect_database()
    cursor = connection.execute(
        'INSERT INTO uploads (created_at, source_file, status, payload) VALUES (?, ?, ?, ?)',
        (datetime.now().isoformat(timespec='seconds'), str_source_file, 'pending',
         json.dumps({'tables': dict_tables, 'sheets': list_sheets})))
    int_upload_id = cursor.lastrowid

    for str_table in MASTER_TABLES:
        if str_table in dict_tables:
            list_key_columns = MASTER_TABLES[str_table]['keys']
            dict_existing = {}
            for dict_row in fetch_rows(connection, f'SELECT * FROM {str_table} ORDER BY rowid', ()):
                dict_key = {}
                for str_column in list_key_columns:
                    dict_key[str_column] = dict_row[str_column]
                dict_existing[json.dumps(dict_key)] = dict_row

            dict_seen = {}
            for dict_row in dict_tables[str_table]:
                dict_key = {}
                for str_column in list_key_columns:
                    dict_key[str_column] = dict_row[str_column]
                str_record_key = json.dumps(dict_key)
                dict_seen[str_record_key] = True
                if str_record_key not in dict_existing:
                    connection.execute(
                        'INSERT INTO master_changes (upload_id, table_name, record_key, change_type, new_values, '
                        'decision) VALUES (?, ?, ?, ?, ?, ?)',
                        (int_upload_id, str_table, str_record_key, 'insert',
                         json.dumps(fill_master_defaults(str_table, dict_row)), 'approved'))
                else:
                    dict_old_row = dict_existing[str_record_key]
                    dict_old_values = {}
                    dict_new_values = {}
                    for str_column in dict_row:
                        if str_column not in list_key_columns:
                            value_old = dict_old_row[str_column]
                            value_new = dict_row[str_column]
                            bool_differs = False
                            if isinstance(value_old, (int, float)) and isinstance(value_new, (int, float)):
                                if abs(float(value_old) - float(value_new)) > 1e-9:
                                    bool_differs = True
                            elif str(value_old) != str(value_new):
                                bool_differs = True
                            if bool_differs:
                                dict_old_values[str_column] = value_old
                                dict_new_values[str_column] = value_new
                    if dict_new_values:
                        connection.execute(
                            'INSERT INTO master_changes (upload_id, table_name, record_key, change_type, old_values, '
                            'new_values, decision) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (int_upload_id, str_table, str_record_key, 'update', json.dumps(dict_old_values),
                             json.dumps(dict_new_values), 'pending'))

            if str_table in list_complete_tables:
                for str_record_key in dict_existing:
                    if str_record_key not in dict_seen:
                        connection.execute(
                            'INSERT INTO master_changes (upload_id, table_name, record_key, change_type, old_values, '
                            'decision) VALUES (?, ?, ?, ?, ?, ?)',
                            (int_upload_id, str_table, str_record_key, 'delete',
                             json.dumps(dict_existing[str_record_key]), 'pending'))

    connection.commit()
    connection.close()
    return get_upload_review(int_upload_id)


@app.get('/api/uploads/{upload_id}')
async def get_upload(upload_id: int):
    dict_review = get_upload_review(upload_id)
    if dict_review is None:
        response = JSONResponse({'error': 'not found'}, status_code=404)
    else:
        response = dict_review
    return response


@app.post('/api/uploads/{upload_id}/apply')
async def post_apply_upload(upload_id: int, request: Request):
    dict_body = await request.json()
    dict_decisions = dict_body.get('decisions', {})
    connection = connect_database()
    list_uploads = fetch_rows(connection, 'SELECT * FROM uploads WHERE upload_id = ?', (upload_id,))
    dict_outcome = {'status': 'not_pending', 'applied': 0, 'rejected': 0, 'snapshot_id': None}
    if list_uploads and list_uploads[0]['status'] == 'pending':
        dict_payload = json.loads(list_uploads[0]['payload'])
        list_changes = fetch_rows(connection, 'SELECT * FROM master_changes WHERE upload_id = ? ORDER BY change_id',
                                  (upload_id,))
        for dict_change in list_changes:
            str_decision = dict_change['decision']
            if dict_change['change_type'] != 'insert':
                str_decision = 'rejected'
                if dict_decisions.get(str(dict_change['change_id'])) == 'approved':
                    str_decision = 'approved'
                connection.execute('UPDATE master_changes SET decision = ? WHERE change_id = ?',
                                   (str_decision, dict_change['change_id']))

            if str_decision == 'approved':
                dict_outcome['applied'] += 1
                str_table = dict_change['table_name']
                dict_key = json.loads(dict_change['record_key'])
                list_where_terms = []
                list_where_values = []
                for str_column in dict_key:
                    list_where_terms.append(f'{str_column} = ?')
                    list_where_values.append(dict_key[str_column])
                str_where = ' AND '.join(list_where_terms)
                if dict_change['change_type'] == 'insert':
                    dict_new_values = json.loads(dict_change['new_values'])
                    list_columns = []
                    list_placeholders = []
                    list_values = []
                    for str_column in dict_new_values:
                        list_columns.append(str_column)
                        list_placeholders.append('?')
                        list_values.append(dict_new_values[str_column])
                    connection.execute(
                        f"INSERT INTO {str_table} ({', '.join(list_columns)}) VALUES ({', '.join(list_placeholders)})",
                        tuple(list_values))
                elif dict_change['change_type'] == 'update':
                    dict_new_values = json.loads(dict_change['new_values'])
                    list_set_terms = []
                    list_values = []
                    for str_column in dict_new_values:
                        list_set_terms.append(f'{str_column} = ?')
                        list_values.append(dict_new_values[str_column])
                    for value_key in list_where_values:
                        list_values.append(value_key)
                    connection.execute(f"UPDATE {str_table} SET {', '.join(list_set_terms)} WHERE {str_where}",
                                       tuple(list_values))
                else:
                    connection.execute(f'DELETE FROM {str_table} WHERE {str_where}', tuple(list_where_values))
            else:
                dict_outcome['rejected'] += 1

        list_snapshot_sheets = []
        for str_sheet in SNAPSHOT_SHEETS:
            if str_sheet in dict_payload['sheets']:
                list_snapshot_sheets.append(str_sheet)
        int_snapshot_id = None
        if list_snapshot_sheets:
            cursor = connection.execute(
                'INSERT INTO snapshots (created_at, source_file, sheets) VALUES (?, ?, ?)',
                (datetime.now().isoformat(timespec='seconds'), list_uploads[0]['source_file'],
                 json.dumps(list_snapshot_sheets)))
            int_snapshot_id = cursor.lastrowid
            for str_table in SNAPSHOT_TABLES:
                for dict_row in dict_payload['tables'].get(str_table, []):
                    list_columns = ['snapshot_id']
                    list_placeholders = ['?']
                    list_values = [int_snapshot_id]
                    for str_column in dict_row:
                        list_columns.append(str_column)
                        list_placeholders.append('?')
                        list_values.append(dict_row[str_column])
                    connection.execute(
                        f"INSERT INTO {str_table} ({', '.join(list_columns)}) VALUES ({', '.join(list_placeholders)})",
                        tuple(list_values))
            set_active_snapshot_id(connection, int_snapshot_id)

        connection.execute('UPDATE uploads SET status = ?, snapshot_id = ? WHERE upload_id = ?',
                           ('applied', int_snapshot_id, upload_id))
        connection.commit()
        dict_outcome['status'] = 'applied'
        dict_outcome['snapshot_id'] = int_snapshot_id
    connection.close()
    return dict_outcome


@app.post('/api/uploads/{upload_id}/discard')
async def post_discard_upload(upload_id: int):
    connection = connect_database()
    connection.execute("UPDATE uploads SET status = 'discarded' WHERE upload_id = ? AND status = 'pending'",
                       (upload_id,))
    connection.commit()
    connection.close()
    return {'status': 'discarded'}


@app.get('/api/init-data')
async def get_init_data():
    int_snapshot_id = get_active_snapshot_id()
    if int_snapshot_id is None:
        response = {'weeks': [], 'machines': [], 'active_machines': [], 'two_color_machines': [], 'products': [],
                    'orders': 0, 'source': None, 'snapshot_id': None}
    else:
        dict_instance = load_snapshot_instance(int_snapshot_id)
        list_weeks = []
        for timestamp_week in dict_instance['weeks']:
            list_weeks.append(timestamp_week.strftime('%Y-%m-%d'))
        list_two_color_machines = []
        for str_machine in dict_instance['all_machines']:
            if dict_instance['color_sides'][str_machine] == 2:
                list_two_color_machines.append(str_machine)
        response = {
            'weeks': list_weeks,
            'machines': dict_instance['all_machines'],
            'active_machines': dict_instance['machines'],
            'two_color_machines': list_two_color_machines,
            'products': dict_instance['products'],
            'orders': len(dict_instance['orders']),
            'source': dict_instance['source'],
            'snapshot_id': int_snapshot_id,
        }
    return response


@app.post('/api/machines/active')
async def post_machine_active(request: Request):
    dict_body = await request.json()
    int_is_active = 0
    if dict_body['is_active']:
        int_is_active = 1
    connection = connect_database()
    connection.execute('UPDATE machines SET is_active = ? WHERE machine = ?',
                       (int_is_active, str(dict_body['machine'])))
    connection.commit()
    connection.close()
    return {'status': 'ok'}


@app.post('/api/machines/color-sides')
async def post_machine_color_sides(request: Request):
    dict_body = await request.json()
    int_color_sides = 1
    if int(dict_body['color_sides']) == 2:
        int_color_sides = 2
    connection = connect_database()
    connection.execute('UPDATE machines SET color_sides = ? WHERE machine = ?',
                       (int_color_sides, str(dict_body['machine'])))
    connection.commit()
    connection.close()
    return {'status': 'ok'}


@app.get('/api/settings')
async def get_settings():
    return load_settings()


@app.post('/api/settings')
async def post_settings(request: Request):
    save_settings(await request.json())
    return {'status': 'saved'}


@app.post('/api/run')
async def run_weekly(request: Request):
    dict_body = await request.json()
    save_settings(dict_body.get('settings', {}))
    dict_settings = load_settings()
    int_snapshot_id = get_active_snapshot_id()

    if int_snapshot_id is None:
        response = {'status': 'NoData', 'message': 'Suba um Excel com os dados antes de executar o plano.'}
    else:
        dict_instance = load_snapshot_instance(int_snapshot_id)
        float_started_at = time.perf_counter()
        dict_result = run_weekly_plan(dict_settings, dict_instance)
        float_seconds = time.perf_counter() - float_started_at

        if dict_result['status'] not in ('Optimal', 'Feasible'):
            response = {'status': dict_result['status'],
                        'message': f"Plano semanal inviavel. Status: {dict_result['status']}"}
        else:
            dict_inputs = dict(dict_settings)
            dict_inputs['machines'] = dict_instance['machines']
            str_run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19]
            str_label = dict_body.get('label', '')
            if not str_label:
                str_label = str_run_id
            connection = connect_database()
            connection.execute(
                'INSERT INTO runs (run_id, created_at, label, snapshot_id, source, settings, weekly_status, '
                'weekly_duration, weekly_result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (str_run_id, datetime.now().isoformat(timespec='seconds'), str_label, int_snapshot_id,
                 dict_instance['source'], json.dumps(dict_inputs), dict_result['status'], round(float_seconds, 2),
                 json.dumps(dict_result)))
            connection.commit()
            connection.close()
            response = dict(dict_result)
            response['run_id'] = str_run_id
            response['duration_seconds'] = round(float_seconds, 2)
            response['source'] = dict_instance['source']
    return response


@app.post('/api/run-daily')
async def run_daily(request: Request):
    dict_body = await request.json()
    dict_record = get_run(dict_body.get('run_id'))
    if dict_record is None:
        response = {'status': 'NoWeeklyRun',
                    'message': 'Rode o plano semanal (/api/run) antes de programar os turnos.'}
    else:
        dict_settings = load_settings()
        dict_instance = load_snapshot_instance(dict_record['snapshot_id'])
        float_started_at = time.perf_counter()
        dict_result = run_daily_plan(dict_settings, dict_instance, dict_record['weekly'])
        float_seconds = time.perf_counter() - float_started_at
        connection = connect_database()
        connection.execute(
            'UPDATE runs SET daily_status = ?, daily_duration = ?, daily_result = ? WHERE run_id = ?',
            (dict_result['status'], round(float_seconds, 2), json.dumps(dict_result), dict_record['id']))
        connection.commit()
        connection.close()
        response = dict(dict_result)
        response['run_id'] = dict_record['id']
        response['duration_seconds'] = round(float_seconds, 2)
        response['source'] = dict_instance['source']
    return response


@app.get('/api/history')
async def get_history():
    connection = connect_database()
    list_rows = fetch_rows(connection, 'SELECT * FROM runs ORDER BY created_at DESC, run_id DESC', ())
    connection.close()
    list_records = []
    for dict_row in list_rows:
        dict_inputs = json.loads(dict_row['settings'])
        dict_weekly = json.loads(dict_row['weekly_result'])
        dict_summary = {
            'id': dict_row['run_id'],
            'timestamp': dict_row['created_at'],
            'label': dict_row['label'],
            'source': dict_row['source'],
            'start_week': dict_inputs.get('start_week'),
            'weeks_in_plan': dict_inputs.get('weeks_in_plan'),
            'machines': len(dict_inputs.get('machines', [])),
            'weekly_kpis': dict_weekly.get('kpis'),
            'weekly_duration': dict_row['weekly_duration'],
            'daily_kpis': None,
            'daily_duration': None,
        }
        if dict_row['daily_result'] is not None:
            dict_summary['daily_kpis'] = json.loads(dict_row['daily_result']).get('kpis')
            dict_summary['daily_duration'] = dict_row['daily_duration']
        list_records.append(dict_summary)
    return list_records


@app.get('/api/history/{run_id}')
async def get_history_run(run_id):
    dict_record = get_run(run_id)
    if dict_record is None:
        response = JSONResponse({'error': 'not found'}, status_code=404)
    else:
        response = dict_record
    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
