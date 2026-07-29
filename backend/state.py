import os

from processing.data import DataService, DATA_DIR, list_data_files

data_service = None
last_tactical_solver = None
last_tactical_run_id = None


def init_data_service():
    global data_service
    available = list_data_files()
    if available:
        data_service = DataService(os.path.join(DATA_DIR, available[0]))
