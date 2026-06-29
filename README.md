# Riberball — Dimensionamento de Lotes

Otimização de produção e estoques (MILP) com interface web opcional.

## Estrutura

- `optimization/` — solver MILP (`solver.py`) e orquestração (`planner.py`).
- `processing/` — leitura do Excel e montagem do cenário (`data.py`), persistência das configurações (`settings.py`).
- `frontend/` — servidor Flask e interface (`app.py`, `templates/`, `static/`).
- `config/*.json` — configurações do sistema (horizonte, capacidade, máquinas, operadores, solver).
- `data/inputs.xlsx` — dados de entrada (demanda, estoque, produtividade, custos).

## Como usar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Interface web (abre o navegador em http://127.0.0.1:5000):

```bash
python launcher.py
```

Execução sem interface (lê os JSONs de `config/`, grava `results.json`):

```bash
python run.py
```

## Configuração

A otimização lê os parâmetros dos arquivos em `config/`. A interface edita esses
mesmos arquivos; a execução standalone os usa diretamente. Os dados de produto
ficam em `data/inputs.xlsx`.
