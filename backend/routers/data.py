import os

from fastapi import APIRouter, HTTPException

from backend import state
from backend.schemas import DataFileRequest
from processing.data import DataService, DATA_DIR, list_data_files

router = APIRouter()


@router.get('/api/data-files')
def get_data_files():
    files = list_data_files()
    active = os.path.basename(state.data_service.data_file) if state.data_service else None
    return {"files": files, "active": active}


@router.post('/api/set-data-file')
def set_data_file(payload: DataFileRequest):
    filename = os.path.basename(payload.file)
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    state.data_service = DataService(path)
    return {"status": "loaded", "file": filename}


@router.get('/api/init-data')
def get_init_data():
    return state.data_service.get_initial_data()
