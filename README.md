# Riberball — Planejamento semanal e programação por turno

Otimização de produção em dois níveis hierárquicos, com interface web:

1. **Plano semanal** (MILP) — decide, por balão (`MODELO-TIPO`) e máquina, quanto produzir em cada
   semana, arbitrando entre **carteira firme**, **previsão de demanda** e **meta de estoque de
   cobertura**, com custo financeiro real (setup, estocagem, faltas).
2. **Programação por turno** (MILP) — recebe do semanal apenas a **meta de estoque de fim de semana**
   e decide, com **sequenciamento embutido**, o que cada máquina produz em cada turno e em que ordem,
   respeitando lote mínimo, troca de forma na fronteira de turno e troca de cor dentro do turno.

Não há etapa heurística de sequenciamento a posteriori: a sequência é decidida dentro do modelo do
nível 2.

## Estrutura

```
optimization/
    weekly_model.py  — MILP semanal (CLSP em máquinas paralelas não relacionadas)
    daily_model.py   — MILP por turno (GLSP: microperíodos = posições dentro do turno)
    planner.py       — orquestra as duas etapas
processing/
    data.py       — leitura do Excel para um dict de instância
    settings.py   — persistência das configurações em JSON
    history.py    — registro das execuções (semanal + diário no mesmo run_id)
backend/
    app.py               — FastAPI; rotas finas, lógica nos módulos acima
    config.py            — variáveis de ambiente (backend/.env)
    lifecycle.py         — registro/heartbeat no Worker + start/stop do túnel
    registration_client.py — chamadas HTTP para /internal/backend/* no Worker
    tunnel.py            — sobe/derruba o Quick Tunnel e extrai a URL pública
frontend/
    app/    — dashboard React + Vite + TypeScript
    worker/ — Cloudflare Worker (serve o app, proxy /api/*, lock de conexão única)
config/
    scenario.json — start_week, weeks_in_plan, frozen_weeks, coverage_weeks
    capacity.json — shifts_per_day, hours_per_shift, working_days_per_week
    machines.json — active_machines, setup_hourly_cost_default, setup_hourly_cost_by_machine
    costs.json    — annual_holding_rate, order_backlog_multiplier, coverage_weight
    solver.json   — motores, tempos limite, positions_per_shift, daily_strategy
data/
    *.xlsx        — instâncias (ver abas abaixo)
tests/
    test_models.py — bateria de validação dos dois modelos
instance_generator.py — gera as instâncias sintéticas
run.py                — execução standalone das duas etapas
```

## Arquivo de entrada (Excel)

| Aba | Cabeçalho | Conteúdo |
|-----|-----------|----------|
| `Produtividade` | linha 2 | `MODELO`, `TIPO`, colunas por máquina (kg/h) |
| `Demanda` | linha 2 | `MODELO`, `TIPO`, uma coluna por **semana** (`AAAA-MM-DD`, segunda-feira); demanda **total** |
| `Estoque` | linha 2 | `MODELO`, `TIPO`, coluna única com o saldo antes do horizonte |
| `Custos` | linha 1 | `MODELO`, `TIPO`, `CUSTO_UNITARIO`, `PRECO_VENDA` |
| `Disponibilidade de maquinas` | linha 1 | `DATA` (semana), colunas por máquina; célula = fração [0, 1] |
| `Pedidos` | linha 1 | `PEDIDO_ID`, `CLIENTE`, `DATA_EMISSAO`, `DATA_VENCIMENTO` |
| `Itens_Pedido` | linha 1 | `PEDIDO_ID`, `MODELO`, `TIPO`, `COR`, `QUANTIDADE` |
| `Estoque_Cor` | linha 1 | `MODELO`, `TIPO`, `COR`, `ESTOQUE_INICIAL` |
| `De_Para_Cores` | linha 1 | matriz COR × COR: célula = horas de setup; vazia = transição **proibida** |
| `De_Para_Formas` | linha 1 | matriz `MODELO-TIPO` × `MODELO-TIPO`: horas de setup de forma; diagonal = 0 |
| `Lote_Minimo` | linha 1 | `MODELO`, `TIPO`, `LOTE_MINIMO_KG` |

Um pedido pode conter itens de balões e cores diferentes; a data de vencimento é do **pedido**.
A carteira é a parcela já confirmada da demanda total: o modelo usa **previsão líquida**
(`demanda total − carteira`), sem dupla contagem.

## As três camadas de demanda

| Camada | Falta | Penalidade unitária |
|--------|-------|---------------------|
| Carteira firme | *backlog* transportado adiante | `order_backlog_multiplier × margem`, cobrada a cada semana em atraso |
| Previsão líquida | venda perdida, não recuperável | `margem` |
| Meta de cobertura (α semanas à frente) | folga da restrição | `coverage_weight × margem` |

Nenhuma camada é rígida: o modelo permanece viável sob qualquer capacidade e a prioridade emerge dos
preços. Sob aperto de capacidade a degradação segue a ordem cobertura → previsão → carteira.

## Custos

Três parâmetros distintos, todos em R$:

- **`CUSTO_UNITARIO`** (`v_i`) — valor unitário do estoque, base do custo de carregamento.
- **`PRECO_VENDA − CUSTO_UNITARIO`** (`m_i`) — margem de contribuição, base das penalidades de falta.
- **`setup_hourly_cost`** — custo direto do setup por hora (mão de obra, energia, composto
  descartado na limpeza). O custo de oportunidade do setup **não** é cobrado à parte: as horas de
  setup já consomem capacidade e a produção perdida reaparece como falta penalizada.

Custo de carregamento: `(θ / 52) × v_i × estoque médio da semana`, com `θ` (`annual_holding_rate`)
decomposto em custo de capital (WACC) + armazenagem + seguro/impostos + obsolescência. A faixa
usual reportada na literatura é 20–30 % ao ano.

## Modelo por turno

Bucket = turno; dentro de cada turno há `positions_per_shift` posições, que definem a sequência.

- Uma **forma** por máquina-turno: dentro do turno só a cor muda. A troca de forma ocorre na
  fronteira de turno e consome horas do turno seguinte.
- Produção mais setup **cabem no turno** (restrição dura) — nenhuma ordem atravessa o turno.
- O estado da máquina (forma e cor montadas) **sobrevive a turnos ociosos**: um turno parado não
  zera o setup acumulado.
- Transições de cor proibidas na matriz DE-PARA nunca aparecem em posições consecutivas.
- Lote mínimo exigido em toda posição que **inicia** uma nova corrida de cor.

O modelo é resolvido como formulado, sem heurística de resolução: o solver recebe o MILP
completo e um tempo limite. Não há relax-and-fix, fixação parcial nem redução do conjunto de
SKUs candidatos — o que se reporta é o que o modelo entrega.

Uma propriedade da formulação mantém o número de binárias baixo: apenas $\nu_{kjsn}$ (SKU na
posição) é declarada binária. As variáveis de configuração — forma montada, máquina ativa,
trocas de forma e de cor, estado de cor — são contínuas em [0, 1] e assumem valor inteiro por
consequência das restrições. O KPI `max_fractional_deviation` reporta o desvio máximo dessas
variáveis frente ao inteiro mais próximo, e `tests/test_models.py` verifica que ele é nulo.

`hit_time_limit` nos KPIs indica que o limite de tempo foi atingido — PuLP+CBC reportam `Optimal`
mesmo quando a busca é truncada, então esse campo é o indicador confiável. Quando ele é verdadeiro,
o resultado é a melhor solução encontrada, não o ótimo provado.

Escala medida com CBC, 3 posições/turno, 1 semana congelada (18 turnos), limite de 900 s:

| Instância | Binárias | Status | Tempo | Limite atingido |
|---|---|---|---|---|
| `micro` (P2 M3) | 540 | Optimal | 65 s | não |
| `pequeno` (P4 M6) | 1.944 | Optimal | 900 s | sim |
| `medio` (P8 M12) | 8.262 | Optimal | 902 s | sim |
| `grande` (P12 M20) | 14.850 | Not Solved | 924 s | — |
| `real` (P17 M28) | 28.728 | Not Solved | 145 s | — |

A partir de `grande` o CBC não encontra solução inteira dentro do limite. Ver `TODO.md`.

## Como usar

### Gerar instâncias

```bash
python instance_generator.py
```

Cinco perfis (`micro`, `pequeno`, `medio`, `grande`, `real`). A fração da demanda já confirmada em
carteira decai ao longo do horizonte (`φ(t) = φ₀·e^{−t/τ}`): perto do início quase tudo é pedido
firme, no fim quase tudo é previsão. Isso é característica da **instância**, não do sistema.

### Rodar sem interface

```bash
python run.py [arquivo.xlsx]
```

Roda as duas etapas e grava `results.json`.

### Testes

```bash
python tests/test_models.py
```

Valida invariantes das instâncias, a hierarquia de preços do semanal (balanço, capacidade, lote
mínimo, decomposição de custo) e o sequenciamento do diário (transições proibidas, tempos da matriz,
carryover através de turnos ociosos, capacidade do turno).

### Interface web

Backend (sobe o túnel e registra no Worker):

```bash
./init.sh      # macOS / Linux
init.bat       # Windows
```

Desenvolvimento do frontend contra um backend local:

```bash
cd frontend/app
npm install
VITE_PROXY_TARGET=http://127.0.0.1:8000 VITE_SHARED_SECRET=<segredo> npm run dev
```

`VITE_SHARED_SECRET` faz o proxy do Vite injetar o header de autorização que o Worker normalmente
adiciona. Sem ele, aponte `VITE_PROXY_TARGET` para o Worker publicado.

Para rodar o backend sem túnel, defina `TUNNEL_ENABLED=false` em `backend/.env`.

## Abas da interface

- **Plano semanal** — estoque projetado × meta de cobertura, natureza da produção (contra pedido /
  previsão / estoque), composição do custo e tabela semanal.
- **Programação por turno** — Gantt máquina × turno (produção e setup, com o tipo de setup
  hachurado), horas por máquina e a tabela de operações (data, turno, máquina, posição, balão, cor,
  quantidade, horas de produção e de setup, natureza).
- **Carteira** — atendimento pedido a pedido por turno, com atraso e venda perdida.
- **Comparação de cenários** — histórico das execuções, com os KPIs das duas etapas lado a lado.

O custo do plano semanal e o custo da semana congelada **não se somam**: o diário re-precifica, em
detalhe de turno, a mesma semana que já está dentro do plano semanal.
