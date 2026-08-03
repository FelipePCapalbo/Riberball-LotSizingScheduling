# Riberball — Dimensionamento de Lotes

Otimização de produção e estoques (MILP) com interface web.

A interface é um frontend estático hospedado permanentemente no Cloudflare Workers
(`riberball-lotsizingscheduling.felipecapalbo.workers.dev`). O backend (FastAPI) roda o
solver e pode ser iniciado em qualquer máquina; ele se conecta ao frontend por um
Cloudflare Quick Tunnel (`trycloudflare.com`, gratuito, sem domínio próprio nem login).
Apenas um backend pode estar conectado por vez — se um segundo for iniciado enquanto
outro já está ativo, ele falha ao subir com um erro explícito.

## Estrutura

```
optimization/
    solver.py       — modelo MILP (PuLP); granularidade diária dentro de períodos mensais
    planner.py      — orquestra leitura de dados, configuração e chamada ao solver
processing/
    data.py         — leitura do Excel e montagem do cenário para o solver
    settings.py     — persistência das configurações em JSON
    history.py      — registro e leitura de execuções passadas
backend/
    app.py               — servidor FastAPI; rotas finas, lógica nos módulos acima
    config.py            — variáveis de ambiente (backend/.env)
    lifecycle.py         — registro/heartbeat no Worker + start/stop do túnel, via lifespan do FastAPI
    registration_client.py — chamadas HTTP para /internal/backend/* no Worker
    tunnel.py             — sobe/derruba o processo `cloudflared` (Quick Tunnel) e extrai a URL pública
frontend/
    app/                — dashboard em React + Vite + TypeScript (build para app/dist/)
        src/api.ts, types.ts     — chamadas HTTP para /api/* e os tipos dos payloads do solver
        src/components/          — Sidebar (parametrização), KpiBar, Tabs, gráficos, tabelas
    worker/             — projeto Cloudflare Worker (serve app/dist/, proxy /api/*, lock de conexão única)
        src/index.ts              — roteamento: assets estáticos, proxy para o backend, status
        src/backend-coordinator.ts — Durable Object que garante um único backend conectado
config/
    scenario.json — horizonte de planejamento e cobertura de segurança
    capacity.json — turnos, horas por turno, dias por semana
    machines.json — máquinas ativas, setup alto/baixo e tempos de setup
    solver.json   — solver (CBC/Gurobi), tempo limite, threads
data/
    *.xlsx        — arquivo(s) de entrada (ver abas abaixo)
history/
    *.json        — resultados de execuções anteriores
init.sh / init.bat  — sobe o backend (e o túnel) em qualquer máquina, macOS/Linux e Windows
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

### Configuração inicial (uma vez só)

1. **cloudflared** — instale o binário (usado só para abrir o Quick Tunnel, não precisa de
   login nem de conta Cloudflare):
   ```bash
   brew install cloudflared          # macOS
   # Windows: choco install cloudflared
   # Linux: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
   ```

2. **Segredo compartilhado** — gere um valor e use em ambos os lados (Worker e backend):
   ```bash
   openssl rand -hex 32
   ```

3. **Worker (frontend)** — já publicado em `riberball-lotsizingscheduling.felipecapalbo.workers.dev`.
   Deploy manual (builda o React em `frontend/app/` e sobe os assets + o Worker):
   ```bash
   cd frontend/worker
   npm install
   npx wrangler login                      # uma vez, abre o navegador
   npx wrangler secret put SHARED_SECRET   # cole o valor gerado no passo 2
   npm run build                            # builda frontend/app/ -> frontend/app/dist/
   npx wrangler deploy
   ```
   Deploy automático (recomendado, um único setup manual no dashboard): Cloudflare →
   Workers & Pages → `riberball-lotsizingscheduling` → **Settings → Builds → Connect to Git**
   → repositório `FelipePCapalbo/Riberball-LotSizingScheduling`, branch `main` →
   **Root Directory: `frontend/worker`** (onde fica o `wrangler.jsonc`) → **Build command:
   `npm install && npm run build`** → Deploy command padrão (`wrangler deploy`). A partir
   daí, todo push em `main` builda e reimplanta sozinho.

4. **Backend** — copie `backend/.env.example` para `backend/.env` e preencha `SHARED_SECRET`
   (o mesmo do passo 2). `WORKER_BASE_URL` já aponta para o Worker publicado por padrão.

### Desenvolvimento do frontend (`frontend/app/`)

```bash
cd frontend/app
npm install
npm run dev
```

O Vite abre em `localhost:5173` e faz proxy de `/api/*` para o Worker publicado por padrão
(dados reais, sem precisar rodar um backend local) — veja `VITE_PROXY_TARGET` em
`vite.config.ts` para apontar para `http://localhost:8000` em vez disso.

Não é preciso domínio próprio, `cloudflared tunnel login`/`create`/`route dns`, nem arquivo de
credenciais — o backend abre um Quick Tunnel (`*.trycloudflare.com`) a cada start e informa a
URL gerada ao Worker automaticamente no registro.

### Dia a dia

Subir o backend (instala dependências, valida `cloudflared`, conecta o túnel e registra a
instância no Worker — falha com erro claro se outro backend já estiver conectado):

```bash
./init.sh      # macOS / Linux
init.bat       # Windows
```

Para rodar o backend localmente sem o túnel (ex: desenvolvimento), defina
`TUNNEL_ENABLED=false` em `backend/.env`.

> Quick Tunnel é gratuito e não exige domínio, mas a Cloudflare o recomenda para uso
> pontual/teste, não produção crítica — a URL muda a cada start e não há SLA formal. Se no
> futuro isso virar um problema, dá para trocar por um túnel nomeado com domínio próprio
> (mais estável); o Worker já lê a URL do backend dinamicamente, então a mudança fica
> contida em `backend/tunnel.py`.

Execução sem interface (lê `config/` e o primeiro `.xlsx` em `data/`, grava `results.json`):

```bash
python run.py
```
