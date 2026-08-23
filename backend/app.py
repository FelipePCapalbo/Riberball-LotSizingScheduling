import os
import sys
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import HOST, PORT, SHARED_SECRET
from backend.lifecycle import lifespan
from optimization.planner import run_weekly_plan, run_daily_plan
from processing.data import DATA_DIR, load_instance, list_data_files
from processing.history import get_run, list_runs, save_daily_run, save_weekly_run
from processing.settings import load_settings, save_settings

app = FastAPI(lifespan=lifespan)

list_available_files = list_data_files()
if list_available_files:
    dict_instance = load_instance(os.path.join(DATA_DIR, list_available_files[0]))
else:
    dict_instance = None

last_weekly_result = None
last_run_id = None


@app.middleware('http')
async def check_shared_secret(request, call_next):
    if request.url.path.startswith('/api/') and request.headers.get('authorization') != f'Bearer {SHARED_SECRET}':
        response = JSONResponse({'error': 'unauthorized'}, status_code=401)
    else:
        response = await call_next(request)
    return response


@app.get('/api/data-files')
async def get_data_files():
    if dict_instance:
        str_active = os.path.basename(dict_instance['data_file'])
    else:
        str_active = None
    return {'files': list_data_files(), 'active': str_active}


@app.post('/api/set-data-file')
async def set_data_file(request: Request):
    global dict_instance
    dict_body = await request.json()
    str_path = os.path.join(DATA_DIR, dict_body.get('file', ''))
    if not os.path.isfile(str_path):
        response = JSONResponse({'error': 'Arquivo nao encontrado.'}, status_code=404)
    else:
        dict_instance = load_instance(str_path)
        response = {'status': 'loaded', 'file': os.path.basename(str_path)}
    return response


@app.get('/api/init-data')
async def get_init_data():
    list_weeks = []
    for timestamp_week in dict_instance['weeks']:
        list_weeks.append(timestamp_week.strftime('%Y-%m-%d'))
    return {
        'weeks': list_weeks,
        'machines': dict_instance['machines'],
        'products': dict_instance['products'],
        'orders': len(dict_instance['orders']),
    }


@app.get('/api/settings')
async def get_settings():
    return load_settings()


@app.post('/api/settings')
async def post_settings(request: Request):
    save_settings(await request.json())
    return {'status': 'saved'}


@app.post('/api/run')
async def run_weekly(request: Request):
    global last_weekly_result, last_run_id
    dict_body = await request.json()
    save_settings(dict_body.get('settings', {}))
    dict_settings = load_settings()

    float_started_at = time.perf_counter()
    dict_result = run_weekly_plan(dict_settings, dict_instance)
    float_seconds = time.perf_counter() - float_started_at

    if dict_result['status'] not in ('Optimal', 'Feasible'):
        response = {'status': dict_result['status'],
                    'message': f"Plano semanal inviavel. Status: {dict_result['status']}"}
    else:
        last_weekly_result = dict_result
        last_run_id = save_weekly_run(dict_settings, dict_result, float_seconds,
                                      dict_body.get('label', ''),
                                      os.path.basename(dict_instance['data_file']))
        response = dict(dict_result)
        response['run_id'] = last_run_id
        response['duration_seconds'] = round(float_seconds, 2)
        response['data_file'] = os.path.basename(dict_instance['data_file'])
    return response


@app.post('/api/run-daily')
async def run_daily(request: Request):
    await request.json()
    if last_weekly_result is None:
        response = {'status': 'NoWeeklyRun',
                    'message': 'Rode o plano semanal (/api/run) antes de programar os turnos.'}
    else:
        dict_settings = load_settings()
        float_started_at = time.perf_counter()
        dict_result = run_daily_plan(dict_settings, dict_instance, last_weekly_result)
        float_seconds = time.perf_counter() - float_started_at
        if last_run_id:
            save_daily_run(last_run_id, dict_result, float_seconds)
        response = dict(dict_result)
        response['run_id'] = last_run_id
        response['duration_seconds'] = round(float_seconds, 2)
        response['data_file'] = os.path.basename(dict_instance['data_file'])
    return response


@app.get('/api/history')
async def get_history():
    return list_runs()


@app.get('/api/history/{run_id}')
async def get_history_run(run_id):
    dict_record = get_run(run_id)
    if not dict_record:
        response = JSONResponse({'error': 'not found'}, status_code=404)
    else:
        response = dict_record
    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
