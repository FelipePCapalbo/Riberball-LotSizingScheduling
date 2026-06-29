"""
Execução standalone do otimizador, sem frontend.

Lê as configurações dos JSONs em config/, roda o solver com os dados do Excel
e grava o resultado em results.json, imprimindo um resumo no terminal.

Uso:
    python run.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processing.data import DataService, DATA_DIR, list_data_files
from processing.settings import load_settings
from optimization.planner import run_plan


def main():
    settings = load_settings()
    files = list_data_files()
    data_service = DataService(os.path.join(DATA_DIR, files[0]))
    result = run_plan(settings, data_service)

    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    status = result.get('status')
    kpis = result.get('kpis', {})
    print(f"\nStatus  : {status}")
    if status in ('Optimal', 'Feasible'):
        print(f"Custo   : R$ {kpis.get('total_cost', 0):,.2f}")
        print(f"Serviço : {kpis.get('service_level', 0):.1f}%")
        print(f"Estoque : {kpis.get('avg_inventory', 0):,.0f} (médio por período)")
    print("\nResultado completo gravado em results.json")


if __name__ == '__main__':
    main()
