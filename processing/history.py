"""
Persistência do histórico de execuções em arquivos JSON individuais.

Cada execução gera um arquivo history/<id>.json com inputs, resultado
e metadados (tempo, label, timestamp). As funções de listagem retornam
apenas metadados + KPIs para não carregar o payload completo na tabela
de comparação.
"""
import os
import json
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR = os.path.join(ROOT_DIR, 'history')


def _ensure_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)


def save_run(inputs: dict, duration_seconds: float, result: dict, label: str = '', data_file: str = '') -> str:
    """
    Grava a execução em history/<id>.json.
    Retorna o id gerado (timestamp no formato YYYYMMDD_HHMMSS_mmm).
    """
    _ensure_dir()
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19]
    record = {
        'id': run_id,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'label': label or run_id,
        'duration_seconds': round(duration_seconds, 2),
        'data_file': data_file,
        'inputs': inputs,
        'kpis': result.get('kpis', {}),
        'result': {k: result.get(k) for k in [
            'status', 'inventory', 'production', 'setups',
            'machine_stops', 'demand', 'summary'
        ] if result.get(k) is not None},
    }
    path = os.path.join(HISTORY_DIR, f'{run_id}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return run_id


def list_runs() -> list:
    """
    Retorna metadados + KPIs de todas as execuções, ordenado do mais recente.
    Cada item: {id, timestamp, label, duration_seconds, inputs (parcial), kpis}.
    """
    _ensure_dir()
    runs = []
    for filename in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if not filename.endswith('.json'):
            continue
        path = os.path.join(HISTORY_DIR, filename)
        try:
            with open(path, encoding='utf-8') as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        inputs = rec.get('inputs', {})
        runs.append({
            'id': rec.get('id'),
            'timestamp': rec.get('timestamp'),
            'label': rec.get('label'),
            'duration_seconds': rec.get('duration_seconds'),
            'kpis': rec.get('kpis', {}),
            # Campos de inputs relevantes para a tabela de comparação
            'start_period': inputs.get('start_period', ''),
            'end_period': inputs.get('end_period', ''),
            'solver_name': inputs.get('solver_name', ''),
            'active_machines_count': len(inputs.get('active_machines', [])),
        })
    return runs


def get_run(run_id: str) -> dict:
    """Retorna o registro completo de uma execução pelo id."""
    _ensure_dir()
    path = os.path.join(HISTORY_DIR, f'{run_id}.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)
