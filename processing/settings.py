"""
Persistência das configurações do sistema em arquivos JSON (fonte de verdade
lida tanto pela interface quanto pela execução standalone).
"""
import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT_DIR, 'config')

# Cada arquivo guarda uma seção; o dict combinado é plano (união das chaves).
SECTIONS = {
    'scenario.json': ['start_period', 'end_period', 'coverage_months'],
    'capacity.json': ['shifts_per_day', 'hours_per_shift', 'days_per_week'],
    'machines.json': ['active_machines',
                      'high_setup_machines', 'setup_time_high', 'setup_time_low'],
    'solver.json': ['solver_name', 'time_limit', 'threads'],
    'color.json': ['color_method', 'color_solver_name', 'color_time_limit', 'setup_time_color_default'],
}


def load_settings() -> dict:
    """Lê os JSONs de configuração e retorna um dict plano combinado."""
    settings = {}
    for filename in SECTIONS:
        with open(os.path.join(CONFIG_DIR, filename), encoding='utf-8') as f:
            settings.update(json.load(f))
    return settings


def save_settings(data: dict) -> None:
    """
    Atualiza cada JSON com as chaves presentes em data.
    Chaves não enviadas (ex: high_setup_machines) são preservadas no arquivo.
    """
    for filename, keys in SECTIONS.items():
        path = os.path.join(CONFIG_DIR, filename)
        with open(path, encoding='utf-8') as f:
            existing = json.load(f)
        existing.update({k: data[k] for k in keys if k in data})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=4, ensure_ascii=False)
