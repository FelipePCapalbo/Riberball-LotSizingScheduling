from fastapi import APIRouter

from backend.schemas import SettingsPayload
from processing.settings import load_settings, save_settings

router = APIRouter()


@router.get('/api/settings')
def get_settings():
    return load_settings()


@router.post('/api/settings')
def post_settings(payload: SettingsPayload):
    save_settings(payload.model_dump(exclude_none=True))
    return {"status": "saved"}
