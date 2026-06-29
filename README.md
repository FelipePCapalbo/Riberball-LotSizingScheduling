# Riberball — Dimensionamento de Lotes

Otimização de produção e estoques (MILP) com interface web opcional.

## Estrutura

```
optimization/
    solver.py     — modelo MILP (PuLP); granularidade diária dentro de períodos mensais
    planner.py    — orquestra leitura de dados, configuração e chamada ao solver
processing/
    data.py       — leitura do Excel e montagem do cenário para o solver
    settings.py   — persistência das configurações em JSON
    history.py    — registro e leitura de execuções passadas
frontend/
    app.py        — servidor Flask; rotas finas, lógica nos módulos acima
    templates/    — interface web
    static/       — JS, CSS, vendors
config/
    scenario.json — horizonte de planejamento e cobertura de segurança
    capacity.json — turnos, horas por turno, dias por semana
    machines.json — máquinas ativas, setup alto/baixo e tempos de setup
    solver.json   — solver (CBC/Gurobi), tempo limite, threads
data/
    *.xlsx        — arquivo(s) de entrada (ver abas abaixo)
history/
    *.json        — resultados de execuções anteriores
```

## Arquivo de entrada (Excel)

Cada `.xlsx` em `data/` deve conter as seguintes abas:

| Aba | Cabeçalho | Conteúdo |
|-----|-----------|----------|
| `Produtividade` | linha 2 (header=1) | `MODELO`, `TIPO`, colunas numéricas por máquina (kg/h) |
| `Demanda` | linha 2 (header=1) | `MODELO`, `TIPO`, colunas `MM/AAAA` com previsão de demanda |
| `Estoque` | linha 2 (header=1) | `MODELO`, `TIPO`, colunas `MM/AAAA` com saldos |
| `Custos` | linha 1 (header=0) | `MODELO`, `TIPO`, `CUSTO_UNITARIO` |
| `Disponibilidade de maquinas` | linha 1 (header=0) | `DATA` (MM/AAAA), colunas numéricas por ID de máquina; célula = fração [0, 1] de disponibilidade no mês |

A aba `Disponibilidade de maquinas` é o único local onde se define quando cada máquina está parcial ou totalmente indisponível. Um valor de `0.8` significa que a máquina tem 80 % dos dias úteis do mês disponíveis; `1.0` é disponibilidade plena.

SKUs são identificados no formato `MODELO-TIPO` em todas as abas.

## Configuração (`config/`)

Os JSONs em `config/` controlam parâmetros de execução — horizonte, capacidade e solver. A interface web os edita diretamente; a execução standalone os lê sem intermediários.

| Arquivo | Chaves |
|---------|--------|
| `scenario.json` | `start_period`, `end_period`, `coverage_months` |
| `capacity.json` | `shifts_per_day`, `hours_per_shift`, `days_per_week` |
| `machines.json` | `active_machines`, `high_setup_machines`, `setup_time_high`, `setup_time_low` |
| `solver.json` | `solver_name`, `time_limit`, `threads` |

## Como usar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Interface web (abre o navegador em http://127.0.0.1:5000):

```bash
python frontend/app.py
```

Execução sem interface (lê `config/` e o primeiro `.xlsx` em `data/`, grava `results.json`):

```bash
python run.py
```
