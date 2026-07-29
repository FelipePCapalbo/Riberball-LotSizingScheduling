import os
import time

from fastapi import APIRouter, HTTPException

from backend import state
from backend.schemas import RunRequest, ColorRunRequest
from processing.settings import load_settings, save_settings
from processing.history import save_run, save_color_result
from optimization.planner import run_tactical_plan, run_color_plan

router = APIRouter()


@router.post('/api/run')
def run_optimization(payload: RunRequest):
    save_settings(payload.settings.model_dump(exclude_none=True))
    settings = load_settings()

    t_start = time.perf_counter()
    solver, result = run_tactical_plan(settings, state.data_service)
    duration = time.perf_counter() - t_start

    if result.get('status') not in ('Optimal', 'Feasible'):
        raise HTTPException(status_code=422, detail={
            "status": result.get('status', 'Unknown'),
            "message": f"Otimização falhou ou é inviável. Status: {result.get('status')}"
        })

    state.last_tactical_solver = solver

    active_file = os.path.basename(state.data_service.data_file) if state.data_service else ''
    run_id = save_run(settings, duration, result, label=payload.label, data_file=active_file)
    state.last_tactical_run_id = run_id

    response = {k: result.get(k) for k in [
        'status', 'inventory', 'production', 'setups',
        'machine_stops', 'demand', 'summary', 'kpis'
    ] if result.get(k) is not None}
    response['run_id'] = run_id
    response['duration_seconds'] = round(duration, 2)
    response['data_file'] = active_file
    return response


@router.post('/api/run-color')
def run_color_optimization(payload: ColorRunRequest):
    if state.last_tactical_solver is None:
        raise HTTPException(status_code=409, detail={
            "status": "NoTacticalRun",
            "message": "Rode a otimização tática (/api/run) antes de sequenciar as cores."
        })

    settings = load_settings()
    if payload.color_method:
        settings['color_method'] = payload.color_method

    t_start = time.perf_counter()
    result = run_color_plan(settings, state.data_service, state.last_tactical_solver)
    duration = time.perf_counter() - t_start

    if state.last_tactical_run_id:
        save_color_result(state.last_tactical_run_id, result, duration)

    response = dict(result)
    response['run_id'] = state.last_tactical_run_id
    response['duration_seconds'] = round(duration, 2)
    response['data_file'] = os.path.basename(state.data_service.data_file) if state.data_service else None
    return response
