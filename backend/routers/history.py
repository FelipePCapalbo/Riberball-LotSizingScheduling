import os

from fastapi import APIRouter, HTTPException

from processing.history import list_runs, get_run

router = APIRouter()


@router.get('/api/history')
def get_history():
    return list_runs()


@router.get('/api/history/{run_id}')
def get_history_run(run_id: str):
    record = get_run(os.path.basename(run_id))
    if not record:
        raise HTTPException(status_code=404, detail="not found")
    return record
