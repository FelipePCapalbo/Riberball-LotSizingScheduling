# Riberball — Planejamento semanal e programação por turno

Otimização de produção em dois níveis hierárquicos, com interface web:

1. **Plano semanal** (MILP) — decide, por balão (`MODELO-TIPO`) e máquina, quanto produzir em cada
   semana, arbitrando entre **carteira firme** e **previsão de demanda**, com custo financeiro real
   (setup, estocagem, faltas).
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
    solver.py        — resolve o problema PuLP com Gurobi ou OR-Tools
processing/
    database.py   — esquema e conexão do banco SQLite (database/riberball.sqlite)
    data.py       — leitura do Excel e do banco para o dict de instância
    uploads.py    — upload do Excel: diferenças contra o cadastro, aprovação de conflitos, fotografias
    settings.py   — parâmetros de execução, gravados no banco
    history.py    — registro das execuções (semanal + diário no mesmo run_id), gravado no banco
backend/
    app.py               — FastAPI; rotas finas, lógica nos módulos acima
    config.py            — variáveis de ambiente (backend/.env)
    lifecycle.py         — registro/heartbeat no Worker + start/stop do túnel
    registration_client.py — chamadas HTTP para /internal/backend/* no Worker
    tunnel.py            — sobe/derruba o Quick Tunnel e extrai a URL pública
frontend/
    app/    — dashboard React + Vite + TypeScript; ambientes main e dev em src/environment.ts
    worker/ — Cloudflare Worker (serve o app, proxy /api/*, lock de conexão única); env dev no wrangler.jsonc
database/
    riberball.sqlite — cadastro mestre, fotografias, uploads e histórico (criado no primeiro uso, fora do git)
data/
    instance_*.xlsx           — instâncias sintéticas (ver abas abaixo)
    input_asis_ajustado.xlsx  — dado real da operação no contrato semanal
    brutos/input_asis.xlsx    — dado real da operação, mensal, fora do contrato
    brutos/legado/            — extrações originais da operação
    arquivo_mensal/           — instâncias da versão mensal, anterior ao contrato semanal
tests/
    test_models.py — bateria de validação dos dois modelos
scripts/
    instance_generator.py — gera as instâncias sintéticas
    input_adjuster.py     — converte brutos/input_asis.xlsx para input_asis_ajustado.xlsx
run.py                — execução standalone das duas etapas
dissertacao/
    ModelagemAlgebrica.tex — texto da dissertação
    apresentacao.tex       — slides (Beamer)
    referencias.bib        — bibliografia dos dois documentos
    figuras/               — imagens usadas nos documentos
    guias/                 — guias de escrita e de slides, plano da dissertação
referencias/
    camargo2014.pdf — artigo de referência
    ltp/            — formulações LTPlabs (semanal, diário, sequenciamento)
docs/
    reunioes/ — anotações de reuniões
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
| `De_Para_Cores` | linha 1 | matriz COR × COR: célula = horas de setup; vazia = limpeza completa, vale o maior tempo registrado na matriz |
| `De_Para_Formas` | linha 1 | matriz `MODELO-TIPO` × `MODELO-TIPO`: horas de setup de forma; diagonal = 0; vazia = maior tempo registrado na matriz |
| `Lote_Minimo` | linha 1 | `MODELO`, `TIPO`, `LOTE_MINIMO_KG` |

Abas opcionais:

| Aba | Cabeçalho | Conteúdo | Sem a aba |
|-----|-----------|----------|-----------|
| `Maquinas` | linha 1 | `MAQUINA`, `ATIVA` (`SIM`/`NAO`), `CUSTO_SETUP_HORA` (R$/h), `DUAS_CORES` (`SIM`/`NAO`, opcional) | máquinas da `Produtividade`, ativas, R$ 250/h, uma cor |
| `MTS_MTO` | linha 1 | `MODELO`, `TIPO`, `COR`, `CLASSE` (`MTS`/`MTO`); `COR` vazia = padrão do balão | todo SKU MTS |
| `Mix_Cores` | linha 1 | `MODELO`, `TIPO`, `COR`, `PARTICIPACAO` (soma 1 por balão) | mix da carteira; sem carteira, uniforme |
| `MAPE` | linha 1 | `MODELO`, `TIPO`, `MAPE` (%) | 0 |
| `Forma_Inicial` | linha 1 | `MAQUINA`, `MODELO`, `TIPO`, `COR` (opcional; cor montada no início do horizonte, do mesmo balão), `COR_LADO_2` (opcional; cor do segundo tanque da máquina de duas cores) | forma desconhecida: a primeira troca custa o maior tempo da `De_Para_Formas`; sem `COR`, o primeiro setup de cor custa o maior tempo da `De_Para_Cores` |
| `Previsao_Manual` | linha 2 | mesmo formato de `Demanda`; célula preenchida sobrepõe a previsão estatística | só a estatística |

Um pedido pode conter itens de balões e cores diferentes; a data de vencimento é do **pedido**.
A carteira é a parcela já confirmada da demanda total: o modelo usa **previsão líquida**
(`demanda total − carteira`), sem dupla contagem.

### Cadastro mestre e fotografias (SQLite)

A interface não lê arquivos de `data/`: o usuário sobe o Excel e o backend grava no banco
`database/riberball.sqlite`. O caminho pode ser trocado pela variável `DATABASE_PATH`.

As abas se dividem em dois grupos:

| Grupo | Abas | Tratamento |
|---|---|---|
| Cadastro mestre | `Produtividade`, `Custos`, `Lote_Minimo`, `MTS_MTO`, `Maquinas`, `De_Para_Formas`, `De_Para_Cores`, `Disponibilidade de maquinas` | comparado com o banco; registros novos entram direto, alterações e remoções são conflitos que o usuário aprova ou rejeita |
| Fotografia de planejamento | `Demanda`, `Previsao_Manual`, `MAPE`, `Mix_Cores`, `Pedidos`, `Itens_Pedido`, `Estoque`, `Estoque_Cor`, `Forma_Inicial` | gravada como uma nova fotografia datada, que passa a ser a ativa |

Regras da comparação:

- Aba ausente não altera o cadastro.
- Coluna ausente não altera o valor gravado.
- Remoção só é proposta quando a aba que define a tabela está presente. Por exemplo, um balão que some
  da `Produtividade` ou uma transição de cor que fica vazia na `De_Para_Cores`.
- Conflito não decidido é rejeitado: o cadastro mantém o valor atual.

Cada execução registra a fotografia que usou. A interface permite trocar a fotografia ativa e
ativar ou desativar máquinas e marcar as de duas cores, o que grava direto no cadastro. Os parâmetros de execução (horizonte,
capacidade, taxa de carregamento, solvers) também ficam no banco, editados pela barra lateral.

## As duas camadas de demanda

| Camada | Falta | Penalidade unitária |
|--------|-------|---------------------|
| Carteira firme | *backlog* transportado adiante | `margem`, cobrada **a cada semana** em atraso |
| Previsão líquida | venda perdida, não recuperável | `margem`, cobrada uma única vez |

As duas custam a mesma margem e mesmo assim a carteira é estritamente mais cara, sem multiplicador
nenhum: o atraso é cobrado a cada semana em que persiste **e** o quilograma atrasado continua no
balanço, ainda terá de ser produzido; a venda perdida é cobrada uma vez e sai do balanço, poupando a
produção. A hierarquia sai da estrutura da formulação, não de um peso calibrado por quem opera.

Nenhuma camada é rígida: o modelo permanece viável sob qualquer capacidade. Sob aperto de capacidade
a degradação segue a ordem previsão → carteira, verificada em `tests/test_models.py`.

Não há camada de cobertura. Uma meta semana a semana seria redundante com o horizonte — o modelo já
enxerga a demanda futura dentro de `weeks_in_plan` e antecipa produção sozinho quando a capacidade
aperta. O que ela evitaria é só o efeito de borda na última semana, e isso o horizonte rolante
(`frozen_weeks = 1`, replanejamento a cada execução) resolve sem introduzir parâmetro novo.

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
- Transição de cor vazia na matriz DE-PARA custa o maior tempo registrado na matriz (limpeza completa).
- Lote mínimo exigido em toda posição que **inicia** uma nova corrida de cor.
- Máquina de **duas cores**: a cadeia tem dois lados, cada um com o seu tanque, e os dois rodam a mesma forma.
  Cada lado produz com a taxa cadastrada (a máquina tem o dobro da vazão), tem a sua corrida de cor, a sua reserva
  de troca e a sua capacidade de turno; uma troca de cor num lado não para o outro. A troca de forma interrompe a máquina
  inteira e consome os dois lados. No semanal a capacidade é contada em horas-lado: `Σ x/p + (n·τF + τC)·y ≤ n·H`.

O modelo é resolvido como formulado, sem heurística de resolução: o solver recebe o MILP
completo e um tempo limite. Não há relax-and-fix, fixação parcial nem redução do conjunto de
SKUs candidatos — o que se reporta é o que o modelo entrega.

Uma propriedade da formulação mantém o número de binárias baixo: apenas $\nu_{kjsn}$ (SKU na
posição) é declarada binária. As variáveis de configuração — forma montada, máquina ativa,
trocas de forma e de cor, estado de cor — são contínuas em [0, 1] e assumem valor inteiro por
consequência das restrições. O KPI `max_fractional_deviation` reporta o desvio máximo dessas
variáveis frente ao inteiro mais próximo, e `tests/test_models.py` verifica que ele é nulo.

## Solvers

Os dois modelos são escritos em PuLP, usado só como camada de modelagem.
`optimization/solver.py` exporta o problema em MPS e o resolve com um de dois motores, escolhido
por etapa nos parâmetros de execução (`weekly_solver_name`, `daily_solver_name`):

| Valor | Motor | Observação |
|---|---|---|
| `ORTOOLS` | SCIP embutido no OR-Tools | padrão; gratuito, single-thread, ignora `threads` |
| `GUROBI` | Gurobi via `gurobipy` | exige licença para modelos acima do limite da licença restrita do pacote; respeita `threads` |

O status vem do próprio motor: `Optimal` (ótimo provado), `Feasible` (solução inteira encontrada
sem prova de otimalidade), `Infeasible` ou `Not Solved`. `hit_time_limit` nos KPIs indica que a
busca foi interrompida pelo tempo limite; nesse caso o resultado é a melhor solução encontrada,
não o ótimo provado.

A escala por instância ainda precisa ser medida nos dois motores. Ver `TODO.md`.

## Como usar

### Gerar instâncias

```bash
python scripts/instance_generator.py
```

Cinco perfis (`micro`, `pequeno`, `medio`, `grande`, `real`). A fração da demanda já confirmada em
carteira decai ao longo do horizonte (`φ(t) = φ₀·e^{−t/τ}`): perto do início quase tudo é pedido
firme, no fim quase tudo é previsão. Isso é característica da **instância**, não do sistema.

### Converter o dado real

```bash
python scripts/input_adjuster.py
```

Lê `data/brutos/input_asis.xlsx` (extração mensal da operação) e grava `data/input_asis_ajustado.xlsx`
no contrato semanal. O dado real é preservado; o que a operação não coletou é sintetizado.

| Aba | Origem |
|-----|--------|
| `Produtividade` | **real** — 17 balões × 28 máquinas, kg/h |
| `Demanda` | **real**, desagregada de mês para semana por dias úteis (total mensal preservado) |
| `Estoque` | **real** — saldo de abertura de 01/2024 |
| `Custos` | `CUSTO_UNITARIO` **real**; `PRECO_VENDA` sintético |
| `Disponibilidade de maquinas` | sintética — preventivas, parada coletiva e carnaval |
| `Pedidos`, `Itens_Pedido` | sintéticos — carteira com `φ(t) = 0,95·e^{−t/8}` |
| `Estoque_Cor` | **real** no total por balão, rateado pelo mix de cores |
| `De_Para_Cores` | sintética — clarear custa mais que escurecer |
| `De_Para_Formas` | sintética — família, calibre e troca de composto |
| `Lote_Minimo` | sintético — corrida mínima de ~2 h |
| `Maquinas` | sintética — todas ativas, R$ 250/h; 7 das 28 (25 %) de duas cores, sorteadas com semente fixa: 1, 3, 5, 10, 13, 16 e 19 |
| `Faturado`, `Produzido` | **reais**, mensais, mantidos como referência As-Is |

A operação não registra cor, carteira, matrizes de setup, lote mínimo nem o tipo de máquina: essas cinco dimensões
existem só no arquivo ajustado e devem ser levantadas em campo antes de qualquer leitura absoluta
dos custos.

O sequenciamento de cor segue a regra de limpeza do látex: escurecer é uma purga curta
(0,25 h + 0,08 h por degrau), clarear exige limpeza profunda (0,70 h + 0,45 h por degrau) e
`PRETO → BRANCO`, `PRETO → AMARELO` e `ROXO → BRANCO` ficam vazias na matriz: só com limpeza completa do
circuito, ao custo do maior tempo registrado. A troca de forma zera quando o `MODELO` não muda: `RED. 10-LISO → RED. 10-PLATINO`
custa só a troca de composto (1,5 h), contra 4,5–6,3 h entre famílias diferentes.

### Rodar sem interface

```bash
python run.py [arquivo.xlsx]
```

Lê o `.xlsx` direto de `data/`, sem passar pelo banco, roda as duas etapas e grava `results.json`.
Os parâmetros de execução vêm do banco (ou dos valores padrão, se o banco estiver vazio).

### Testes

```bash
python tests/test_models.py
```

Valida invariantes das instâncias, a hierarquia de preços do semanal (balanço, capacidade, lote
mínimo, decomposição de custo) e o sequenciamento do diário (lacunas da matriz, tempos da matriz,
carryover através de turnos ociosos, capacidade do turno).

### Experimentos de esforço computacional

Tudo é disparado por um único script, que roda em segundo plano (sobrevive ao fechamento do terminal):

```bash
python scripts/launch_experiments.py formulacao              # uma variante
python scripts/launch_experiments.py todas                   # todas as variantes, em ondas
python scripts/launch_experiments.py rf_tempo rf_maquina --paralelo 2 --rapido
python scripts/launch_experiments.py --situacao              # progresso de todas as rodadas
python scripts/launch_experiments.py --retomar experimentos/esforco_computacional/rodadas/<pasta>
python scripts/computational_experiments_analysis.py [--maquina <rotulo>]
```

| Variante | Código |
|---|---|
| `formulacao` | o repositório principal, modelo resolvido como formulado |
| `rf_tempo`, `rf_maquina`, `rf_produto` | worktrees `../Riberball-wt-rf-*`: relax-and-fix e fix-and-optimize por tempo, máquina e produto |
| `preprocessamento` | `../Riberball-wt-numba`: pré-processamento exato em numba (com `.venv` própria) |
| `warm_start` | `../Riberball-wt-warm-start`: heurística construtiva de solução inicial |
| `cascata` | `../Riberball-wt-cascata`: warm start sequencial por segmento de negócio |

A bateria de arquitetura compara o planejamento hierárquico com o modelo monolítico (worktree
`../Riberball-wt-monolitico`, um MILP só, por turno e posição de cor, sobre todo o horizonte), cada um sob as mesmas
técnicas, nas cinco instâncias sintéticas e na série de horizonte do ajustado (1, 2, 4, 8 e 13 semanas):

```bash
python scripts/launch_experiments.py todas --bateria arquitetura --apos experimentos/esforco_computacional/disparos/<disparo>.json
python scripts/launch_experiments.py monolitico_pura formulacao --bateria arquitetura --rapido
```

`--apos` deixa o disparo na fila: as ondas só começam quando todas as rodadas do disparo indicado terminam. As
variantes monolíticas são `monolitico_<tecnica>`, com `pura`, `desagregado`, `rf_tempo`, `rf_maquina`, `rf_produto`,
`preprocessamento`, `warm_start` e `cascata`.

O teste de classes de variáveis (`scripts/variable_class_test.py`, worktree `../Riberball-wt-classes-variaveis`) mede
quanto cada classe pesa no esforço, nos dois níveis, em `pequeno`, `medio` e `ajustado`, com 600 s por nível e as
sementes 0, 1 e 2: modelo como formulado, binárias relaxadas, 0 a 100% das binárias livres (o resto fixado na solução
base), todas fixadas com o tamanho variando (e o horizonte de 4, 8 e 13 semanas no ajustado) e, no diário, `z` binária.
Escreve `resultados.csv` (uma linha por configuração) e `regressao.csv` (elasticidades por MQO e correlação entre
segundos e `work`):

```bash
python scripts/launch_experiments.py classes_variaveis --bateria classes --threads 1
```

O worktree que faltar é criado a partir da sua branch `exp/*`. As variantes de uma onda rodam em paralelo
(`--paralelo`, padrão 3), cada uma com `--threads` do Gurobi (padrão 2). A comparação de tempo só vale entre rodadas
da mesma máquina; as unidades de trabalho do Gurobi (`work`) são determinísticas e são a resposta principal.

Cada disparo cria uma pasta por variante:

```
experimentos/esforco_computacional/
    plano.json                                  fatores, níveis, sementes e grades
    disparos/<data>_<maquina>.json              ondas e pastas de um disparo (e o .log do supervisor)
    rodadas/<data>_<maquina>_<variante>/
        ambiente.json                           máquina, CPU, memória, sistema, pacotes, branch, commit, limites
        plano.json                              cópia do plano usado
        execucoes/<id>.json                     registro completo de cada execução
        logs/<id>.log                           log do Gurobi
        resultados.csv                          uma linha por execução, refeito a cada execução
        bateria.log                             progresso
        saida.out                               saída do processo
    comparativo/                                tabelas entre variantes
```

O rótulo da máquina é o hostname, ou `EXPERIMENT_MACHINE_LABEL` se definido. `--rapido` roda a baseline e um nível
de cada fator com 30 s por nível, numa pasta com sufixo `_rapido` que fica fora do git. A bateria parte de
`data/input_asis_ajustado.xlsx` e varia um fator por vez (máquinas, balões, cores por balão, flexibilidade, demanda,
estoque inicial, capacidade, tempos de setup, máquinas de duas cores, horizonte e semanas congeladas), mais três
grades 4×4 de pares de fatores, com os limites da operação (300 s no semanal, 600 s no diário). Uma execução que já
tem JSON é pulada na retomada. A análise usa, por variante, a rodada mais recente e escreve os CSVs dos gráficos em
`dissertacao/dados/esforco/`.

### Interface web

Backend (prepara o ambiente, sobe o túnel e registra no Worker):

```bash
./init.sh      # macOS / Linux
init.bat       # Windows
```

Único pré-requisito na máquina: **Python 3.10 a 3.13, 64 bits**. No Windows, o instalador
padrão do python.org basta — não é preciso marcar "Add to PATH", porque o script localiza o
interpretador pelo launcher `py`. O resto o script resolve sozinho, sem instalar nada no
sistema nem alterar o PATH:

| Passo | O que faz |
|---|---|
| 1 | Localiza um Python compatível e valida versão, arquitetura, `venv` e `ensurepip` |
| 2 | Cria (ou recria, se estiver corrompida) a `.venv` dentro da pasta do projeto |
| 3 | Instala as dependências na `.venv`; reinstala só quando `requirements.txt` muda |
| 4 | Baixa o `cloudflared` para a própria pasta, se ainda não estiver lá |
| 5 | Abre o navegador na interface e sobe o backend |

Tudo o que é criado (`.venv/`, `cloudflared`) fica dentro da pasta e some ao apagá-la. O
interpretador é sempre invocado por caminho absoluto e com `-E -s`, e as variáveis `PYTHONHOME`,
`PYTHONPATH` e `PYTHONSTARTUP` são neutralizadas dentro do script — um Python, um Anaconda ou um
`PYTHONPATH` já existentes na máquina não interferem.

Se existir uma pasta `wheels/` ao lado do script, a instalação usa `--no-index --find-links wheels`
e roda sem rede. Para montar esse diretório a partir de qualquer sistema operacional:

```bash
pip download -r requirements.txt --platform win_amd64 --python-version 312 --only-binary=:all: -d wheels
```

O backend exige `backend/.env` com o `SHARED_SECRET` igual ao configurado no Worker. Na entrega a um
cliente, o arquivo já vai preenchido dentro do pacote.

Desenvolvimento do frontend contra um backend local:

```bash
cd frontend/app
npm install
VITE_PROXY_TARGET=http://127.0.0.1:8000 VITE_SHARED_SECRET=<segredo> npm run dev
```

`VITE_SHARED_SECRET` faz o proxy do Vite injetar o header de autorização que o Worker normalmente
adiciona. Sem `VITE_PROXY_TARGET`, o proxy aponta para o Worker do ambiente (`npm run dev` → dev,
`npm run dev:main` → main).

### Ambientes da interface

A interface é publicada em dois Workers independentes, cada um com seu próprio lock de conexão. O
backend é o mesmo código nos dois; cada máquina de backend se registra em um só Worker, escolhido
por `WORKER_BASE_URL` em `backend/.env`.

| Ambiente | Worker | Quem acessa | Motor do solver |
|---|---|---|---|
| `main` | `riberball-lotsizingscheduling.felipecapalbo.workers.dev` | cliente | só OR-Tools, sem seletor |
| `dev` | `riberball-lotsizingscheduling-dev.felipecapalbo.workers.dev` | desenvolvimento | OR-Tools ou Gurobi |

As diferenças entre os ambientes ficam em `frontend/app/src/environment.ts`, selecionadas pelo
`--mode` do Vite. Em `main`, se os parâmetros de execução gravados no banco trouxerem um motor fora
da lista permitida, a interface o troca por OR-Tools antes de salvar e rodar.

| Ação | `main` | `dev` |
|---|---|---|
| Build do app (`frontend/worker`) | `npm run build` | `npm run build:dev` |
| Deploy do Worker (`frontend/worker`) | `npm run deploy` | `npm run deploy:dev` |
| Saída do build | `frontend/app/dist/main` | `frontend/app/dist/dev` |

O Worker `dev` precisa do próprio segredo, igual ao `SHARED_SECRET` do backend que se registra nele:

```bash
cd frontend/worker
npx wrangler secret put SHARED_SECRET --env dev
```

### Fluxo de desenvolvimento

| Branch | Publica em | Uso |
|---|---|---|
| `dev` | Worker `dev` | todo desenvolvimento; push publica automaticamente |
| `main` | Worker `main` | o que o cliente acessa; recebe só por Pull Request de `dev` |

Os dois Workers são publicados pelo Workers Builds (integração Git da Cloudflare), cada um ligado
a uma branch, com diretório raiz `frontend/worker`:

| Worker | Branch de produção | Build | Deploy |
|---|---|---|---|
| `riberball-lotsizingscheduling` | `main` | `npm run build` | `npx wrangler deploy` |
| `riberball-lotsizingscheduling-dev` | `dev` | `npm run build:dev` | `npx wrangler deploy --env dev` |

Builds de branches que não são de produção ficam desligados nos dois Workers, para que um push em
`dev` não gere versões do Worker `main`.

Para rodar o backend sem túnel, defina `TUNNEL_ENABLED=false` em `backend/.env`.

### Estados da conexão

`/api/backend-status` devolve três estados, e a interface só libera as chamadas de dados no terceiro:

| Estado | Significado |
|---|---|
| `disconnected` | nenhum lease ativo no Worker — rode `init.sh` na máquina do backend |
| `starting` | backend registrado, mas o túnel ainda não responde: `/api/*` devolve 503 |
| `connected` | o Worker já tem a URL pública e o túnel respondeu `/api/health` |

O backend registra o lease, sobe o uvicorn e só então publica a URL do túnel, depois de confirmar
com uma sondagem em `/api/health` que ela já atravessa até a porta local. O heartbeat começa no
registro, então o lease não expira enquanto o `cloudflared` sobe.

## Abas da interface

- **Plano semanal** — estoque projetado, natureza da produção (contra pedido /
  previsão / estoque), composição do custo e tabela semanal.
- **Programação por turno** — Gantt máquina × turno (produção e setup, com o tipo de setup
  hachurado, uma linha por lado nas máquinas de duas cores), horas por máquina e a tabela de operações
  (data, turno, máquina, lado, posição, balão, cor,
  quantidade, horas de produção e de setup, natureza).
- **Carteira** — atendimento pedido a pedido por turno, com atraso e venda perdida.
- **Comparação de cenários** — histórico das execuções, com os KPIs das duas etapas lado a lado.

O custo do plano semanal e o custo da semana congelada **não se somam**: o diário re-precifica, em
detalhe de turno, a mesma semana que já está dentro do plano semanal.
