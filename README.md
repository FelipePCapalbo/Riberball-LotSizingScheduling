# Riberball — Dimensionamento de Lotes e Sequenciamento de Cores

Otimização de produção e estoques em duas etapas, com interface web opcional:

1. **Tático** (MILP) — dimensiona lotes por MODELO-TIPO, decidindo o que cada máquina produz dia a dia.
2. **Operacional** (MILP ou heurística) — dentro das janelas definidas pela etapa 1, sequencia as cores (MODELO-TIPO-COR), respeitando prazos de entrega e restrições de troca de cor.

## Estrutura

```
optimization/
    solver.py             — modelo MILP tático (PuLP); granularidade diária dentro de períodos mensais
    color_problem.py       — monta o problema de sequenciamento de cores a partir do resultado tático
    scheduler_milp.py      — resolve o sequenciamento de cores via MILP (PuLP)
    scheduler_heuristic.py — resolve o sequenciamento de cores via heurística EDD
    planner.py             — orquestra leitura de dados, configuração e chamada aos solvers
processing/
    data.py       — leitura do Excel e montagem do cenário para os solvers
    settings.py   — persistência das configurações em JSON
    history.py    — registro e leitura de execuções passadas
backend/
    main.py       — app FastAPI; monta o StaticFiles do frontend compilado e inclui os routers
    state.py      — estado de processo (data_service, último solver/run tático resolvido)
    schemas.py    — modelos Pydantic de entrada (borda HTTP; processing/ e optimization/ seguem sem type hints)
    routers/      — data.py, settings.py, runs.py, history.py — rotas finas, lógica nos módulos acima
frontend/
    package.json, vite.config.js, index.html — build Vite
    src/          — app React (componentes, cliente HTTP, gráficos Chart.js)
    dist/         — bundle estático compilado (commitado; servido pelo FastAPI, roda offline sem Node)
config/
    scenario.json — horizonte de planejamento e cobertura de segurança
    capacity.json — turnos, horas por turno, dias por semana
    machines.json — máquinas ativas, setup alto/baixo e tempos de setup
    solver.json   — solver (CBC/Gurobi), tempo limite, threads
    color.json    — método de sequenciamento de cores e setup padrão
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

SKUs são identificados no formato `MODELO-TIPO` em todas as abas acima.

Além dessas, o mesmo arquivo `.xlsx` contém três abas para a etapa 2 (sequenciamento de cores), identificadas no formato `MODELO-TIPO-COR`:

| Aba | Cabeçalho | Conteúdo |
|-----|-----------|----------|
| `Demanda_Cor` | linha 1 (header=0) | `MODELO`, `TIPO`, `COR`, `QUANTIDADE`, `PRAZO_ENTREGA` — uma linha por pedido |
| `Estoque_Cor` | linha 1 (header=0) | `MODELO`, `TIPO`, `COR`, `ESTOQUE_INICIAL` — saldo inicial por SKU-cor |
| `De_Para_Cores` | linha 1 (header=0) | matriz COR x COR (mesmo formato de `Disponibilidade de maquinas`): primeira coluna `DE`, demais colunas = cor de destino; célula = tempo de setup (h) se a transição imediata é permitida, célula vazia = transição proibida |

Não existem `Produtividade_Cor` nem `Custos_Cor`: cada pedido de `Demanda_Cor`/`Estoque_Cor` referencia seu `MODELO-TIPO` pai (via colunas `MODELO`/`TIPO`) para resolver produtividade e custo unitário — ambos permanecem exclusivamente no nível tático. As únicas equivalências exigidas entre os dois níveis são de soma: `Σ_cor Demanda_Cor(MODELO, TIPO, COR)` no mês do prazo deve bater com `Demanda(MODELO, TIPO)` daquele mês, e o mesmo vale para `Estoque_Cor` frente a `Estoque`. O `instance_generator.ipynb` garante essas somas por construção (ver seção da etapa 2 abaixo).

## Configuração (`config/`)

Os JSONs em `config/` controlam parâmetros de execução — horizonte, capacidade e solver. A interface web os edita diretamente; a execução standalone os lê sem intermediários.

| Arquivo | Chaves |
|---------|--------|
| `scenario.json` | `start_period`, `end_period`, `coverage_months` |
| `capacity.json` | `shifts_per_day`, `hours_per_shift`, `days_per_week` |
| `machines.json` | `active_machines`, `high_setup_machines`, `setup_time_high`, `setup_time_low` |
| `solver.json` | `solver_name`, `time_limit`, `threads` |
| `color.json` | `color_method` (`"milp"` ou `"heuristic"`), `color_solver_name`, `color_time_limit` (motor e tempo limite do modelo operacional, independentes do tático), `setup_time_color_default` (h de setup no primeiro dia de cada janela) |

## Etapa 2 — Sequenciamento de cores

O modelo tático decide, por máquina e dia, qual MODELO-TIPO é produzido — isso define **janelas**: blocos de dias consecutivos com o mesmo MODELO-TIPO numa máquina. A etapa 2 não altera essas janelas; ela as subdivide entre as cores daquele MODELO-TIPO, com a mesma produtividade por máquina já usada na etapa 1.

A conexão entre as duas etapas é feita por uma camada única de preparação de dados, desacoplada de qualquer solver:

- `optimization/color_problem.py` (`build_color_scheduling_problem`) lê a instância já resolvida do `LotSizingSolver` (janelas de produção) e os dados de cor (`Demanda_Cor`, `Estoque_Cor`, `De_Para_Cores`), e monta um dict plano — o "problema" de sequenciamento — sem depender de `pulp` nem de estado de solver.
- Dois módulos resolvem esse mesmo problema de forma **totalmente independente** entre si (nenhum importa o outro nem o `LotSizingSolver`):
  - `optimization/scheduler_milp.py` (`solve_color_schedule_milp`) — modelo matemático MILP: elegibilidade de transição de cor via matriz DE-PARA, variáveis de troca (`Trans`) e balanço de estoque/atraso por pedido.
  - `optimization/scheduler_heuristic.py` (`solve_color_schedule_heuristic`) — heurística gulosa por EDD (Earliest Due Date): a cada dia de janela, escolhe a cor mais urgente que não viola a matriz DE-PARA em relação ao dia anterior naquela máquina.
- `optimization/planner.py` expõe `run_tactical_plan` (roda a etapa 1 e devolve `(solver, resultado)`) e `run_color_plan` (usa o `solver` tático já resolvido para montar e resolver o problema de cor, despachando para MILP ou heurística conforme `color_method`).

Ambos os solvers devolvem o mesmo formato de resultado (`status`, `method`, `color_schedule`, `color_setups`, `orders`, `kpis`), o que permite trocar de método via `config/color.json` sem alterar nenhum dos dois módulos, e rodar os dois lado a lado para comparação.

Na interface web, a seção retrátil **Solver** da barra lateral é dividida em **Modelo Tático** (motor e tempo limite da etapa 1) e **Modelo Operacional** (método de sequenciamento — heurística ou modelo matemático — e, quando o modelo matemático é escolhido, motor e tempo limite próprios da etapa 2). Assim que a execução tática (`/api/run`) termina com sucesso, a etapa 2 é disparada automaticamente (`/api/run-color`); não há botão de execução manual na aba **Sequenciamento de Cores** — ela é somente para visualização, e um novo ciclo completo (tático + operacional) é sempre disparado a partir do botão "Rodar Otimização" com as configurações persistidas na barra lateral.

O resultado da etapa 2 é anexado ao mesmo registro de histórico (`history/<run_id>.json`) criado pela etapa 1, em `save_color_result`. Ao carregar um cenário salvo na aba **Comparação de Cenários**, a interface recupera tanto o resultado tático quanto — se existir — o resultado operacional daquele `run_id`, repopulando as duas abas sem precisar rodar nada novamente.

### `instance_generator.ipynb` e os dados de cor

O gerador de instâncias sintéticas cria, para todo perfil (`micro`, `pequeno`, `medio`, `grande`, `real`) e para a instância avulsa, as três abas de cor a partir de um "mix de cores" por produto (`make_color_mix`): cada MODELO-TIPO recebe entre `MIN_COLORS_PER_PRODUCT` e `MAX_COLORS_PER_PRODUCT` cores de `COLOR_POOL`, com pesos que somam 1. `make_color_demand` e `make_color_inventory` decompõem `Demanda`/`Estoque` nesses pesos, garantindo as equivalências de soma por construção. `make_color_setup_matrix` sorteia a matriz DE-PARA, bloqueando pares com probabilidade `COLOR_TRANSITION_BLOCK_PROB` e definindo tempos de setup entre `COLOR_SETUP_TIME_MIN` e `COLOR_SETUP_TIME_MAX` para os pares permitidos.

## Como usar

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

Interface web (abre o navegador em http://127.0.0.1:5000). O bundle do frontend em `frontend/dist/` já vem compilado e commitado, então isto roda sem precisar de Node instalado:

```bash
python run_app.py
```

Para desenvolver o frontend (hot reload), rode o backend e o Vite dev server em paralelo — o Vite faz proxy de `/api` para `http://127.0.0.1:5000`:

```bash
python run_app.py            # backend na porta 5000
cd frontend && npm install && npm run dev   # dev server do Vite (porta 5173)
```

Depois de alterar o frontend, gere o novo bundle estático (commitado em `frontend/dist/`):

```bash
cd frontend && npm run build
```

Execução sem interface (lê `config/` e o primeiro `.xlsx` em `data/`, grava `results.json`):

```bash
python run.py
```

`run.py` chama `run_plan` (`optimization/planner.py`), que descarta o solver tático retornado e portanto não executa a etapa 2 (sequenciamento de cores) — um bug pré-existente, fora do escopo da refatoração do frontend. Para rodar as duas etapas sem interface, use a API do backend (`/api/run` seguido de `/api/run-color`).
