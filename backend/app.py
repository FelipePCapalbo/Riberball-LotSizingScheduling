import os
import sys
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import HOST, PORT, SHARED_SECRET
from backend.lifecycle import lifespan
from optimization.planner import run_plan
from processing.data import DATA_DIR, DataService, list_data_files
from processing.history import get_run, list_runs, save_run
from processing.settings import load_settings, save_settings

app = FastAPI(lifespan=lifespan)

available_files = list_data_files()
if available_files:
    data_service = DataService(os.path.join(DATA_DIR, available_files[0]))
else:
    data_service = None


@app.middleware('http')
async def check_shared_secret(request, call_next):
    if request.url.path.startswith('/api/') and request.headers.get('authorization') != f'Bearer {SHARED_SECRET}':
        response = JSONResponse({'error': 'unauthorized'}, status_code=401)
    else:
        response = await call_next(request)
    return response


@app.get('/api/data-files')
async def get_data_files():
    files = list_data_files()
    if data_service:
        active = os.path.basename(data_service.data_file)
    else:
        active = None
    return {'files': files, 'active': active}


@app.post('/api/set-data-file')
async def set_data_file(request: Request):
    global data_service
    body = await request.json()
    filename = body.get('file', '')
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        response = JSONResponse({'error': 'Arquivo não encontrado.'}, status_code=404)
    else:
        data_service = DataService(path)
        response = {'status': 'loaded', 'file': filename}
    return response


@app.get('/api/init-data')
async def get_init_data():
    return data_service.get_initial_data()


@app.get('/api/settings')
async def get_settings():
    return load_settings()


@app.post('/api/settings')
async def post_settings(request: Request):
    body = await request.json()
    save_settings(body)
    return {'status': 'saved'}


@app.post('/api/run')
async def run_optimization(request: Request):
    body = await request.json()
    if body:
        label = body.get('label', '')
    else:
        label = ''
    settings = load_settings()

    time_start = time.perf_counter()
    result = run_plan(settings, data_service)
    duration = time.perf_counter() - time_start

    if result.get('status') not in ('Optimal', 'Feasible'):
        response = {
            'status': result.get('status', 'Unknown'),
            'message': f"Otimização falhou ou é inviável. Status: {result.get('status')}",
        }
    else:
        if data_service:
            active_file = os.path.basename(data_service.data_file)
        else:
            active_file = ''
        run_id = save_run(settings, duration, result, label=label, data_file=active_file)

        payload = {}
        for key in ['status', 'inventory', 'production', 'setups', 'machine_stops', 'demand', 'summary', 'kpis']:
            if result.get(key) is not None:
                payload[key] = result.get(key)
        payload['run_id'] = run_id
        payload['duration_seconds'] = round(duration, 2)
        if data_service:
            payload['data_file'] = os.path.basename(data_service.data_file)
        else:
            payload['data_file'] = None
        response = payload
    return response


@app.get('/api/history')
async def get_history():
    return list_runs()


@app.get('/api/history/{run_id}')
async def get_history_run(run_id):
    record = get_run(run_id)
    if not record:
        response = JSONResponse({'error': 'not found'}, status_code=404)
    else:
        response = record
    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
