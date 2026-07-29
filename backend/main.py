import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend import state
from backend.routers import data, settings, runs, history

app = FastAPI(title="Riberball")

app.include_router(data.router)
app.include_router(settings.router)
app.include_router(runs.router)
app.include_router(history.router)


@app.on_event('startup')
def on_startup():
    state.init_data_service()


DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'dist')
app.mount('/', StaticFiles(directory=DIST_DIR, html=True), name='frontend')
