# Plano de evolução da dissertação — descrição do problema, granularidade e alinhamento com a literatura

> **ATUALIZAÇÃO (2026-08-22) — a Seção 2 deste plano descreve uma arquitetura que foi substituída.**
> A reformulação para plano semanal + programação por turno foi implementada e validada. O que
> mudou frente ao que está escrito abaixo:
>
> | Item do plano | Estado |
> |---|---|
> | Bucket tático mensal com subperíodo diário | **Substituído** por bucket semanal puro (`optimization/weekly_model.py`) |
> | Acoplamento por janelas rígidas | **Substituído** pela meta de estoque de fim de semana, suave (§2.3 resolvida) |
> | Etapa 2 de cor a posteriori (MILP DLSP + heurística EDD) | **Removida**; sequenciamento embutido no modelo por turno (`optimization/daily_model.py`) |
> | Backlog 1 (granularidade da notação) | ✅ `t` semana, `s` turno, `n` posição, fixado no `.tex` |
> | Backlog 2 (demanda em duas camadas) | ✅ três camadas: carteira com atraso, previsão líquida com venda perdida, cobertura suave |
> | Backlog 3 (correções do modelo algébrico) | ✅ capítulo reescrito; `z_jd` eliminado |
> | Backlog 7 (modelo tático semanal) | ✅ formulado e implementado |
> | Backlog 8 (variante do nível de cor) | ✅ resolvido por GLSP com posições dentro do turno |
> | Backlog 14 (carryover de cor entre janelas) | ✅ carryover atravessa turnos e turnos ociosos |
> | Backlog 15 (absorver o `TODO.md`) | ✅ lote mínimo e contrato entre níveis implementados |
> | Apêndice A.2 (lote mínimo) | ✅ implementado nos dois níveis |
> | Apêndice A.4 (custo de estoque via WACC) | ✅ implementado; a linha "custo de oportunidade puro" saiu da `tab:gap` |
> | Apêndice A.7 (granularidade de turno) | ✅ adotada |
>
> **Ainda em aberto:** perecibilidade do látex (backlog 13), tratabilidade da instância `real` no
> modelo por turno, conversão do dado real de mensal para semanal, e o capítulo de Resultados.
>
> O plano de execução completo da reformulação está em `~/.claude/plans/elegant-waddling-pillow.md`.

Documento de planejamento para a reescrita do `ModelagemAlgebrica.tex`, tendo como referência estrutural a dissertação de Mateus Carmesim Marques (FEUP, 2026), *A Mathematical Optimisation Framework to Medium-Term Production Planning in the Metal Packaging Industry*.

Referências adicionais de modelagem (formulações LTPlabs da mesma empresa da tese, no repositório): `weekly_planning.tex` (tático semanal com abastecimento multi-filial), `daily_operationbased.tex` (curto prazo por turno, baseado em operações, setup por características) e `daily_jobscheduling.tex` (sequenciamento intra-turno). Juntas, formam uma hierarquia real de três níveis — semanal → diário/turno → sequenciamento — que valida a arquitetura proposta na Seção 2. O que dessas formulações já foi incorporado está na Seção 2; o que fica como oportunidade a avaliar está no Apêndice A.

---

## Como usar este documento

Este é um **documento vivo de consulta**, pensado para orientar **múltiplas sessões de chatbot** ao longo da evolução da dissertação. Cada sessão deve:

1. **Ler este plano antes de agir** — ele carrega o estado, as decisões já tomadas e as ainda pendentes.
2. **Respeitar as flags de cada tarefa** — quem pode executá-la (agente sozinho ou precisa do usuário) e o que já foi feito.
3. **Atualizar as flags de status** ao concluir ou avançar uma tarefa, para a próxima sessão encontrar o estado correto.

**Última sincronização com o `.tex` e com o código: 2026-07-30**, cobrindo os commits `7ca2218` (revisão de literatura no `.tex`) e `749d081` (etapa operacional de cores no código + reorganização do frontend). O `README.md` é a fonte autoritativa do estado da implementação; o `ModelagemAlgebrica.tex`, do estado do texto. Este plano só registra a distância entre os dois e o que falta decidir.

### Convenções de flags

Cada tarefa/tópico carrega até duas flags: uma de **natureza** (quem executa) e uma de **status** (implementação).

**Natureza — quem executa:**

- 🤖 **AUTÔNOMO** — um agente pode executar sozinho: pesquisa bibliográfica, redação de seções que não dependem de dado de negócio, formalização de um modelo já decidido, EDA sobre dados já existentes no repositório. Não requer decisão nem aprovação do usuário para começar.
- 🧑 **DECISÃO** — depende do usuário: informação da fábrica/negócio que só ele tem (pain points reais, dados operacionais, se a fábrica terceiriza, onde o balão vira cor-específico), **escolha entre alternativas de modelagem**, ou **aprovação manual** antes de seguir. Um agente pode *preparar* e *recomendar*, mas não deve fechar sozinho.

Tarefas mistas usam as duas em sequência (🤖→🧑 ou 🧑→🤖): ex. o usuário decide o esquema, o agente formaliza; ou o agente redige um rascunho e o usuário aprova o conteúdo factual.

**Status de implementação:**

- ⬜ **PENDENTE** — não iniciado.
- 🟨 **PARCIAL** — em andamento ou parcialmente feito (detalhar o que falta).
- ✅ **FEITO** — concluído (no texto e/ou no código, conforme a tarefa).

O registro mestre de tarefas com flags é a **Seção 5 (Backlog)**. Pontos de decisão espalhados pelo texto são marcados com 🧑 no local.

---

## 1. Diagnóstico: o que a tese de referência faz e o documento atual ainda não faz

### 1.1 Comparação estrutural

| Elemento da tese de referência | Situação no `.tex` atual |
|---|---|
| **Problem statement guiado por pain points**: 5 dores concretas levantadas com stakeholders (previsão com 50–60% de acerto, política de estoque fragmentada, compras decididas só por preço, lead times sem visibilidade, lotes pequenos com setups frequentes), cada uma retomada depois pelos módulos da solução | Introdução e Contextualização vazias; a motivação existe apenas implícita na seção de planejamento tático |
| **Figura de arquitetura de decisão com granularidade anotada**: cada módulo carrega horizonte e frequência (8 meses/semanal, 15 dias/diário/turno) e as setas mostram o que flui entre módulos | Não existe visão de arquitetura; o leitor não sabe que há (nem haverá) níveis de decisão distintos |
| **Escopo e premissas explícitos**: seção "Scope of the Project" + lista numerada de 11 premissas simplificadoras (demanda determinística, setups independentes de sequência no nível semanal, calendário de turnos como parâmetro, backordering penalizado, capacidade de armazém rígida...) | Premissas espalhadas e implícitas no texto corrido; nada é declarado como simplificação consciente |
| **Capítulo "The Problem" completo**: contexto industrial → processo produtivo → abordagem proposta → estrutura dos dados → preparação de dados → **EDA quantitativa** (ABC-SEIL, sazonalidade 3:1 pico/vale, complexidade da BOM) → síntese. A EDA *dimensiona* o problema antes de qualquer equação | Existe a seção "Processo produtivo" (boa, com fluxograma TikZ) e as subseções "Planejamento tático" e "Previsão de demanda"; a subseção **"Planejamento operacional" existe como cabeçalho vazio** — é exatamente onde o nível de cor já implementado no código precisa ser descrito. Não há caracterização quantitativa do portfólio, da sazonalidade nem dos setups |
| **Formulação apresentada didaticamente**: tabelas de conjuntos/parâmetros/variáveis; restrições agrupadas (A: estoque/fluxo, B: capacidade, C: carteira) e **cada equação seguida de um parágrafo de prosa** explicando papel e consequências | Tabelas de notação ✓; mas as 5 restrições são explicadas em dois parágrafos condensados, sem agrupamento temático |
| **Demanda em camadas de prioridade**: pedidos confirmados (restrição cumulativa C1, penalidade máxima) > demanda prevista > estoque de segurança > estoque de ciclo — tudo *soft constraint* com pesos configuráveis, garantindo viabilidade sob capacidade apertada | O modelo trata uma demanda única `d_it`; a carteira firme não aparece; o estoque de segurança é restrição **rígida** (risco de inviabilidade) |
| **Resultados em dois planos**: (i) qualidade do plano As-Is vs. Otimizado (nº de setups, horas de setup, OEE, tamanho médio de lote, com exemplos de produtos específicos realocados); (ii) resultados computacionais (dimensões do MIP antes/depois do presolve, tempo, gap, estratégia de solução em duas fases) | Não existem capítulos de resultados |
| **Granularidade temporal definida**: bucket = semana, horizonte móvel de 32 semanas, re-execução semanal (rolling horizon) declarados desde o abstract | **Indefinida**: `T` são "períodos" genéricos; `D_t ⊆ D` insinua dias dentro de períodos, mas semana nunca é fixada; o leitor não sabe a cadência de replanejamento |

### 1.2 O que o documento atual já tem de bom (preservar e valorizar)

- **Fluxograma do processo produtivo** em TikZ — análogo direto da Figure 3.1 da tese; falta apenas anotar onde ocorre a diferenciação por cor (mistura/pigmentação) e onde ocorrem os setups longos (troca de formas na moldagem).
- **Modelo próprio de previsão de demanda** (hierárquico top-down com RLS) — a tese de referência *recebe* a previsão pronta de outro módulo; ter modelagem própria de demanda é um diferencial da dissertação e merece capítulo próprio bem conectado ao restante.
- **Apêndice com exemplo numérico** completo da previsão — a tese de referência não tem nada equivalente; manter.

### 1.3 Problemas técnicos do modelo algébrico atual (corrigir na reescrita)

> Nota de notação: o `.tex` fixou **`b_jd`** para as horas produtivas disponíveis da máquina `j` no dia `d` (`\subsection*{Parâmetros}` do modelo de otimização). O código chama o mesmo objeto de `daily_capacity`/`h_jd`. Este plano usa `b_jd`, seguindo o `.tex`.

1. **Produto bilinear na restrição de balanço** (`eq:balanco`): o termo `(b_jd − t^s_j·δ_ijd)·s_ijd·p_ij` multiplica duas binárias (`δ·s`). A implementação (`optimization/solver.py`) já usa a forma **linear** `(b_jd·s_ijd − t^s_j·δ_ijd)·p_ij` — o documento deve adotar essa forma (válida porque setup implica estado ativo).
2. **Estoque de segurança rígido** (`eq:seguranca`): com capacidade apertada o modelo fica inviável. Adotar o padrão da tese: variável de folga penalizada na FO, com peso menor que o da demanda. (Detalhe da implementação a documentar: para a cobertura funcionar nos últimos períodos, a demanda é estendida além do horizonte repetindo a sazonalidade do ano anterior — `_extend_dates_with_seasonality` em `processing/data.py`, complementada por `_ensure_demand_coverage` em `optimization/solver.py`.)
3. **Setup na fronteira entre períodos**: `δ_ijd ≥ s_ijd − s_ij,d−1` precisa de definição para o primeiro dia do horizonte e para a emenda entre semanas quando o modelo for particionado (setup carryover). Hoje o código encadeia os dias de forma contígua entre períodos, o que resolve dentro de uma rodada mas não entre rodadas do rolling horizon.
4. **Demanda única**: separar `d_it` em carteira firme e previsão (ver Seção 2).
5. **Variável `z_jd` inerte**: existe no `.tex` e no código (`Z_day`), mas nada a penaliza nem a força — o solver a deixa sempre em 0 e as paradas reais entram via `h_jd = 0`. Ou ela ganha papel de decisão (parada endógena, com custo/motivo) ou sai da formulação e do texto.
6. **"Período" não é o que o texto sugere**: na implementação `T` são **meses** (colunas `MM/AAAA` da planilha de demanda) e `D_t` são ~30 dias genéricos de 24 h — não há calendário real. O texto fala em "plano semanal" no planejamento tático, mas o modelo roda mensal. Essa incoerência entre texto, modelo e código é exatamente a dor de granularidade que a Seção 2 ataca.
7. **Nomenclatura enganosa na config**: `coverage_months` (o α) chega ao solver como argumento `safety_stock_pct` (`optimization/planner.py`), mas é contagem de períodos, não percentual — renomear quando o código for tocado.
8. **Restrição redundante e prosa trocada**: `eq:estado_unico` (`Σ_i s_ijd ≤ 1`) é dominada por `eq:capacidade` (`Σ_i s_ijd ≤ 1 − z_jd`); as duas coexistem no `.tex` e no código (`solver.py`). Além disso, o parágrafo que explica "cada máquina produz no máximo um tipo de balão por dia ativo" referencia `eq:capacidade` quando deveria referenciar `eq:estado_unico`, e o parágrafo seguinte repete o mesmo conteúdo. Resolver junto com o destino de `z_jd` (item 5): removida a variável, sobra uma única restrição e um único parágrafo.
9. **Premissa não declarada da disponibilidade fracionária**: a disponibilidade mensal `avail_jt ∈ [0,1]` é convertida em **dias inteiros parados no início do período** (`_precompute_daily_capacity` em `solver.py`) — não há calendário nem posicionamento real das paradas. O `.tex` só diz que `b_jd = 0` impede ativação. Declarar como premissa simplificadora ou substituir por calendário real na migração mês→semana.

---

## 2. Arquitetura de decisão hierárquica proposta

### Ponto de partida: o que a implementação faz hoje

Resumo do estado atual — **dois modelos encadeados**, não mais um MILP único (`optimization/planner.py` orquestra; ver `README.md` para o detalhe operacional):

**Etapa 1 — tático (`optimization/solver.py`)**

- **Bucket tático = mês** (demanda, estoque `I[(p,t)]`, venda perdida `K[(p,t)]`, cobertura α em meses via `coverage_months`); **scheduling = dia** (`S_state[(m,p,d)]`, `Delta_Setup[(m,p,d)]`), com cada mês expandido em `round(7 × 4.33) = 30` dias uniformes de `3 turnos × 8 h = 24 h` (`config/capacity.json`). Não há calendário real: disponibilidade mensal fracionária vira dias inteiros parados **no início** do mês.
- **Não existe variável contínua de quantidade**: a produção do dia é implícita (`S_state × horas do dia × produtividade`) — a máquina produz o dia inteiro ou nada.
- **Setup por máquina em dois níveis** (`setup_time_high` = 7 h só para a máquina 17, `setup_time_low` = 3 h para as demais, `config/machines.json`); não depende do par de produtos. O `TODO.md` já registra a intenção de generalizar para `n` tempos por máquina.
- **Objetivo = custo de oportunidade** (receita perdida em setup + vendas perdidas), sem custo de estoque — coerente entre código e `.tex`.
- Produto = `MODELO-TIPO` (formato+acabamento), como o `.tex` declara. Demanda única `d_it`, sem separação entre carteira e previsão.

**Etapa 2 — operacional por cor (`color_problem.py`, `scheduler_milp.py`, `scheduler_heuristic.py`)** — adicionada no commit `749d081`, posterior à última revisão deste plano:

- O tático define **janelas**: blocos de dias consecutivos com o mesmo `MODELO-TIPO` numa máquina. A etapa 2 **não altera as janelas**; subdivide cada uma entre as cores daquele produto, com a mesma produtividade e o mesmo custo unitário do nível tático.
- Dados próprios no mesmo Excel: `Demanda_Cor` (carteira de pedidos por `MODELO-TIPO-COR` com `PRAZO_ENTREGA`), `Estoque_Cor` (saldo inicial por SKU-cor) e `De_Para_Cores` (matriz de tempo de setup por transição, **célula vazia = transição proibida**). O `instance_generator.ipynb` gera as três abas garantindo por construção que `Σ_cor Demanda_Cor = Demanda` e `Σ_cor Estoque_Cor = Estoque`.
- Dois métodos intercambiáveis (`color_method` em `config/color.json`): **MILP** (uma cor por dia dentro da janela, variáveis de transição `Trans` entre dias consecutivos, balanço de estoque/atraso por pedido, FO = custo de setup de cor + custo de atraso da carteira) e **heurística gulosa EDD** (a cada dia escolhe a cor mais urgente que não viola a matriz DE-PARA).
- Na interface, a etapa 2 dispara automaticamente após a etapa 1 (`/api/run` → `/api/run-color`). Pela CLI, `run.py` descarta o solver tático e **não** roda a etapa 2 (bug conhecido, registrado no `README.md`).
- O modelo de previsão de demanda do `.tex` **continua não implementado**; o código lê demanda pronta do Excel.

Ou seja: a hierarquia de dois níveis proposta neste plano **já existe na implementação**, mas com três diferenças em relação ao que a Seção 2 descreve, e nenhuma delas está no `.tex` (a subseção "Planejamento operacional" está vazia):

1. o bucket tático é **mês**, não semana, e o nível tático continua híbrido mensal/diário num MILP só;
2. o acoplamento entre níveis é por **janelas fixas** (o operacional herda a alocação máquina↔produto e não pode alterá-la), não por metas com folga penalizada (ver §2.3);
3. o setup de cor é dado por **matriz DE-PARA explícita**, não pelo mecanismo de setup por características descrito em §2.2.

A proposta abaixo mantém o alvo (níveis explícitos, bucket tático semanal, figura de arquitetura no estilo da Figure 1.1 da tese, com horizonte e granularidade anotados por caixa), mas agora deve ser lida como **evolução de um sistema de dois níveis que já roda** — não como reparticionamento de um monólito.

### 2.0 Nível 0 — Previsão de demanda (existente)

- Horizonte: meses/semanas à frente; granularidade: balão (formato+acabamento).
- Saídas para o nível tático: **duas correntes de demanda** — a previsão `d̂_it` (modelo hierárquico já formulado) e a **carteira firme** `o_it` (pedidos confirmados, vinda do comercial, não modelada estatisticamente).
- **Estado atual (2026-07-30)**: a carteira já existe na implementação, mas só no nível de cor (`Demanda_Cor`, com quantidade e prazo por `MODELO-TIPO-COR`) e como *desagregação da própria previsão* — o gerador força `Σ_cor Demanda_Cor = Demanda`. Não é, portanto, uma segunda corrente independente; é a mesma demanda vista com granularidade maior. Fechar o item 2 do backlog exige decidir se a carteira passa a entrar como corrente própria (com quantidade e prazo vindos do comercial, podendo divergir da previsão) ou se o trabalho assume a versão atual e declara isso como premissa.
- No texto: conectar explicitamente o capítulo de demanda ao de otimização (hoje eles não conversam além do parâmetro α).

### 2.1 Nível 1 — Planejamento tático semanal (lot sizing agregado)

- **Horizonte**: N semanas (sugestão: 8–16, cobrindo ao menos um ciclo de sazonalidade relevante), rolling horizon com re-execução semanal.
- **Bucket**: semana. **Agregação de produto**: formato+acabamento (sem cor) — exatamente o conjunto `I` atual.
- **Decide**: alocação máquina↔balão por semana; quantidades de produção (lotes semanais); estoques; vendas perdidas; setups de troca de forma (os longos, entre formatos).
- **Demanda em duas camadas, seguindo o requisito do negócio** (carteira sempre prioritária; previsão atendida com a capacidade restante):
  - Carteira: restrição de atendimento **cumulativo** — estoque inicial + produção acumulada até a semana `t` ≥ carteira acumulada até `t` — com variável de falta `z^carteira_it` de penalidade máxima na FO. A forma cumulativa (restrição C1 da tese) permite antecipar produção para cobrir pedidos futuros, que é como o planejador age na prática.
  - Previsão: balanço de estoque com venda perdida `l_it` penalizada com peso menor. Decisão a declarar explicitamente no texto: falta de **carteira** é *backlog* (transportada adiante até ser atendida — a forma cumulativa faz isso naturalmente), enquanto falta de **previsão** é venda perdida (não recuperável). A referência `weekly_planning.tex` transporta a falta de demanda como backlog incremental (`zsp_w − zsp_{w−1}`); para balões (produto de prateleira, venda por oportunidade), venda perdida na previsão é mais fiel — justificar essa diferença na dissertação.
  - Estoque de cobertura α: terceira camada, folga penalizada com o menor peso.
  - Nenhuma camada é rígida → o modelo permanece viável sob capacidade apertada e a hierarquia é dada pelos pesos (declarar os pesos como parâmetros configuráveis, como α, β, γ, δ, ε na tese).
- **O que deixa de existir neste nível**: índice de dia, cores, sequenciamento. A capacidade semanal da máquina vira `B_jt = Σ_{d ∈ D_t} b_jd` menos paradas programadas.
- **Implicação de dados da migração mês→semana**: a demanda hoje entra mensal (colunas `MM/AAAA` do Excel); será preciso definir a desagregação mensal→semanal (uniforme, por dias úteis, ou já prever por semana no Nível 0) e substituir o calendário genérico de 30 dias × 24 h por um calendário real de dias úteis/turnos por semana. A conversão de disponibilidade fracionária em dias inteiros parados no início do mês também deve ser repensada nessa passagem.
- **Ganho de tratabilidade**: sem o índice diário, este nível dispensa as binárias `S_state` por dia — a alocação vira binária semanal (máquina×balão×semana) com variável contínua de horas/quantidade, um CLSP clássico bem menor que o MILP atual.

### 2.2 Nível 2 — Programação operacional diária (scheduling + cores)

- **Horizonte**: 1–2 semanas; **bucket**: dia (ou turno). Congela a primeira semana do plano tático e a detalha.
- **Recebe do tático**: quantidades semanais por balão×máquina (metas), alocações máquina↔formato.
- **Decide**: desagregação da quantidade semanal **por cor**; em que dia produzir cada cor; sequência dentro da máquina, com **setup/limpeza dependente da troca de cor**.
- **Carteira também aqui**: os pedidos firmes têm datas e cores; a desagregação por cor deve priorizar as cores da carteira antes das cores estimadas do mix de previsão.
- **O que já está implementado (commit `749d081`)**: a etapa 2 do código resolve exatamente este nível, com duas alternativas ligadas por configuração — a heurística EDD (essencialmente a variante **2b**) e um MILP que **não corresponde a nenhuma das três variantes abaixo**: bucket = dia, *uma cor por dia* dentro da janela (`Σ_cor Sc = 1`) e transições cobradas entre dias consecutivos via variáveis `Trans` — isto é, um modelo do tipo DLSP (*small-bucket* discreto), mais próximo de 2a que de 2c, porém restrito às janelas herdadas do tático e sem microperíodos dentro do dia.
- **Três variantes de formulação** — 🧑 **DECISÃO em aberto, mas reformulada**: não é mais "escolher entre três variantes no papel", e sim decidir se a dissertação (i) assume a variante DLSP já implementada, formaliza-a e usa a heurística EDD como *baseline* de comparação — caminho mais curto, já com código rodando; ou (ii) migra para 2c (MILP diário por características + sequenciador por máquina-dia), o que exige reimplementação. Um agente pode formalizar qualquer uma delas; a escolha é do usuário:

| | **2a — MILP com sequenciamento embutido** | **2b — MILP diário + heurística de sequenciamento** | **2c — MILP diário por atributos + MILP de sequenciamento (padrão LTPlabs)** |
|---|---|---|---|
| Formulação | Tipo GLSP/CLSD: microperíodos ou variáveis de sequência por máquina-dia | MILP small-bucket decide *quanto de cada cor por dia/máquina* (sem ordem); heurística ordena dentro do dia | MILP diário conta o setup por **características ativas no bucket** (sem ordem), como `daily_operationbased.tex`; um segundo MILP pequeno sequencia dentro do dia/turno, como `daily_jobscheduling.tex` |
| Setups de cor | Exatos, dependentes de sequência | Aproximados no MILP (nº de cores ativas × tempo de limpeza); ordem real dada pela heurística (claro→escuro, estilo *block planning*) | Aproximados no MILP diário (paga-se 1 setup por característica ativa não herdada do dia anterior); **exatos** no MILP de sequenciamento (caminho tipo ATSP por máquina, custo de transição = características novas exigidas) |
| Custo computacional | Alto (binárias de sequência explodem com cores×dias×máquinas) | Baixo; MILP pequeno + regra O(n log n) | Médio; o sequenciamento decompõe por máquina-dia (instâncias minúsculas, resolvidas de forma independente) |
| Aderência à prática | Ótimo teórico | Reflete a regra que a fábrica já usa; fácil de validar | Padrão usado em produção real na indústria de embalagens (LTPlabs); mantém otimalidade local na sequência sem inflar o modelo diário |
| Na dissertação | Boa contribuição metodológica se resolver em tempo aceitável | Boa justificativa de engenharia | Melhor dos dois mundos e permite comparação experimental 2b vs. 2c (heurística vs. sequenciamento exato) |

- **Mecanismo de setup: divergência a reconciliar.** O código foi por **matriz DE-PARA explícita** (`De_Para_Cores`: tempo por par de cores, célula vazia = transição proibida, `load_color_setup_matrix`), que já entrega a assimetria claro→escuro e ainda permite proibir transições — algo que a formulação por características não expressa naturalmente. A alternativa por características, descrita a seguir, é mais compacta (um `γ` por tipo, em vez de `|C|²` células) e unifica formato e cor num só formalismo, mas não está implementada. 🧑 **Decidir qual das duas vai para o `.tex`**; se a escolha for a matriz, este bullet vira justificativa da escolha e não proposta de mudança.
- **Mecanismo de setup por características** (incorporado de `daily_operationbased.tex` / `daily_jobscheduling.tex`, e um encaixe natural para os balões): cada produção exige um conjunto de características de setup — **formato/forma** (tipo de setup longo) e **cor do composto** (tipo de setup curto, de limpeza) — e a transição paga apenas as características exigidas que a máquina ainda não tem: `d_ij = Σ γ(tipo)` sobre as características de `j` ausentes em `i` (abandonar uma característica é grátis, logo o custo é direcional — exatamente a assimetria claro→escuro vs. escuro→claro da limpeza de pigmento). Isso unifica os dois tipos de setup do problema num único formalismo, com um tempo `γ` por tipo, em vez de duas modelagens ad hoc.
- **Carryover de estado de setup entre dias** (idem): a máquina permanece configurada (forma + última cor) ao atravessar dias e até dias inativos — variáveis de estado de fim de dia (`endState`/`lastState` na referência) definem a "origem" do dia seguinte, e produzir a mesma configuração no dia seguinte não paga novo setup. Resolve formalmente o item 3 da Seção 1.3 (fronteira entre períodos), tanto no nível diário quanto na emenda com o rolling horizon.
  - ⚠️ **Texto e código divergem hoje**: a Revisão de Literatura do `.tex` (subseção 2.3) já promete o carryover como "o mecanismo desta literatura reaproveitado no nível operacional diário do modelo proposto", mas o MILP de cor implementado **não faz carryover entre janelas** — todo primeiro dia de janela paga `setup_time_color_default`, ignorando qual cor a máquina tinha montada. Dentro da janela o carryover funciona (dia sem troca não paga setup). Ou o código passa a herdar a última cor da janela anterior naquela máquina, ou a promessa sai do `.tex` (ver backlog item 14).

### 2.3 Acoplamento entre níveis

**Acoplamento implementado hoje (a descrever ou substituir, não ignorar)**: o operacional recebe do tático as **janelas** — blocos de dias consecutivos com o mesmo `MODELO-TIPO` numa máquina — e as trata como **rígidas**: não pode mudar a alocação máquina↔produto, nem mover produção entre dias fora da janela, nem alterar quanto se produz no total; só decide a repartição da janela entre cores. É um acoplamento por *fixação*, não por meta com folga. Vantagem: consistência automática entre os níveis e um subproblema pequeno. Custo: toda inviabilidade de prazo da carteira de cor vira atraso penalizado, sem possibilidade de reação do nível superior — não há realimentação do operacional para o tático. O `TODO.md` registra a intenção do usuário de rever esse contrato ("modelo diário deve receber puramente o input do modelo semanal"). 🧑 **Decidir**: manter a fixação por janelas (simples, já roda, e vira premissa declarada) ou migrar para o esquema de metas com folga descrito abaixo.

- Metas do tático entram no diário como alvos com **folga penalizada** (não como igualdade rígida) — desvios são possíveis, mas custam; isso evita propagar inviabilidade para baixo. Mecanismo concreto (incorporado de `daily_operationbased.tex`): um parâmetro de **estoque objetivo ao fim do horizonte diário** (`ObjectiveStock_p`, definido pelo plano semanal) com variável de falta penalizada — o diário persegue o estado que o tático planejou para o fim da janela, em vez de replicar quantidades semana a semana.
- Do sequenciamento para cima (incorporado de `daily_jobscheduling.tex`): a duração do dia/turno **não é restrição de viabilidade no sequenciador** — se a sequência ótima estourar o turno, o excedente (*overrun*) é reportado como *feedback* ao nível diário, que reage na rodada seguinte. Evita inviabilidades artificiais em cascata.
- O realizado/replanejado do diário realimenta o tático na re-execução seguinte (rolling horizon): estoques atualizados, carteira consumida, paradas ocorridas, estado de setup herdado (forma + cor montadas em cada máquina).
- No documento: uma subseção "Coordenação hierárquica" explicando esse contrato entre níveis (a tese faz isso ao descrever como o Módulo B alimenta C e D).

---

## 3. Alinhamento com a literatura (posicionamento do problema)

> ✅ **FEITO (2026-07-20)**: a Revisão de Literatura está escrita, revisada e compilando sem erros no `ModelagemAlgebrica.tex` (seção "Revisão de literatura", subseções 2.1–2.5: HPP, CLSP, dimensionamento+sequenciamento integrado, aplicações em indústria de processo e **Posicionamento** — subseção renomeada de "Síntese e posicionamento" no commit `749d081`), com 23 referências verificadas em `referencias.bib`. **O `.tex` é a fonte autoritativa** para a classificação do problema, as referências-chave e a tabela de posicionamento (`tab:gap`) — este plano não duplica mais esse conteúdo; o que segue abaixo é só o que ainda está em aberto. Pendente: revisão de conteúdo/adequação ao programa pelo usuário (🧑) antes de considerar o capítulo fechado.

### 3.0 Decisões que o `.tex` já fechou de facto

Ao escrever a Revisão de Literatura, o `.tex` assumiu compromissos que este plano ainda tratava como decisões em aberto. Eles não são reversíveis de graça: mexer neles agora exige reescrever trechos do capítulo 2. Registrados aqui para que as sessões seguintes não os reabram por engano — e para que os capítulos 3 e 5 não os contradigam:

- **Venda perdida, sem *backorder*, na camada de previsão** — afirmado na subseção 2.2 e na linha correspondente de `tab:gap`. Fecha a direção da decisão do backlog item 2; o que resta em aberto é apenas o tratamento da falta de **carteira** (atraso penalizado, como o código já faz no nível de cor).
- **Custo de oportunidade puro, sem custo de estoque** — declarado em `tab:gap` como diferencial do trabalho. O Apêndice A.4 deixa de ser decisão de escopo e passa a ser candidato a análise de sensibilidade nos Resultados.
- **Setup direcional (assimétrico)** — declarado em `tab:gap` como característica do problema, e já implementado (matriz DE-PARA). Não é mais hipótese a validar.
- **Arquitetura hierárquica família→item** — a subseção 2.1 já declara, via Hax e Meal, que formato+acabamento é a família decidida no tático e a cor é o item desagregado no operacional, justificando a fronteira pelos dois tipos de setup. A Seção 2 deste plano, portanto, não é mais "proposta": é o compromisso assumido no texto, que os capítulos 3 e 5 precisam honrar.

### 3.0.1 Promessa do `.tex` sem contrapartida no modelo: perecibilidade do látex

A subseção 2.5 (Posicionamento) eleva a **perecibilidade do látex** — recebimento diário, estoque em tanques — a uma das duas características do problema sem equivalente na literatura revisada. Não existe nenhuma restrição de matéria-prima no modelo, em nenhum dos dois níveis, nem item de backlog ou entrada no Apêndice A que a cubra. Como está, o texto anuncia uma contribuição que a formulação não entrega. 🧑 **Decidir**: modelar (estoque de látex com validade, capacidade de tanque, recebimento diário) ou rebaixar a menção no `.tex` a premissa simplificadora declarada — ver backlog item 13.

### 3.1 Achado ainda em aberto: analogia com a fiação têxtil

Camargo, Toledo & Almada-Lobo (2012, formulação MSGLSP; 2014, método de solução HOPS) formalizam um problema de dois estágios sincronizados — mistura de fibras alimentando máquinas de fiação em paralelo — estruturalmente mais próximo do composto pigmentado↔moldagem dos balões do que a literatura de bebidas já citada (já incorporado à Seção 2.4 e à tabela `tab:gap` do `.tex`). Duas tarefas do backlog decorrem desse achado: o Apêndice A.1 (mistura/pigmentação como estágio próprio) ganhou um gabarito formal pronto para adaptar, *se* a mistura de látex restringir de fato a operação — decisão do usuário; e o item 12 do backlog, buscar e ler o texto completo do artigo de 2012, hoje citado só por atribuição via o de 2014.

---

## 4. Plano de reescrita do documento, capítulo a capítulo

Esqueleto alvo (espelha a tese de referência, adaptado a dissertação com modelagem própria de demanda):

| Cap. | Conteúdo | Estado atual | Prioridade |
|---|---|---|---|
| 1. Introdução | Contextualização (indústria de balões, empresa); **pain points** do planejamento atual (levantar 3–5 com a operação: como se planeja hoje, onde dói); objetivos; estrutura do documento | Vazio | Alta |
| 2. Revisão de literatura | Hierarquia de planejamento (Stadtler/Anthony); famílias de lot sizing (CLSP→GLSP/CLSD); HPP; aplicações em indústria de processo (bebidas, fiação, block planning); posicionamento (`tab:gap`) | **Escrito** (2.1–2.5, 23 referências verificadas); falta revisão de conteúdo pelo usuário | Baixa |
| 3. Descrição do problema | Contexto industrial e de planejamento (MTS vs. carteira, quem decide o quê, cadência); processo produtivo (manter fluxograma, anotar diferenciação de cor e setups); **granularidade das decisões** (semana/dia — Seção 2 deste plano); **EDA**: ABC de produtos, sazonalidade (reaproveitar dados do apêndice), nº formatos×acabamentos×cores, tempos de setup forma vs. cor; síntese | Parcial (processo produtivo, planejamento tático e previsão de demanda escritos; **"Planejamento operacional" é um cabeçalho vazio**) | **Máxima** — é a dor central apontada |
| 4. Modelo de demanda | Capítulo atual, quase pronto; conectar saídas às duas correntes (previsão + carteira) e ao α do tático | Bom | Baixa |
| 5. Metodologia (otimização) | Premissas numeradas; **modelo tático semanal** (notação em tabelas, FO, restrições agrupadas A/B/C e comentadas uma a uma); **modelo operacional de cores** (a variante DLSP já implementada ou 2c, com o mecanismo de setup escolhido e carryover de estado); coordenação hierárquica (janelas vs. metas com folga) | Parcial (só o modelo monolítico defasado; a etapa 2 de cores, que já roda no código, não aparece no `.tex`) | Alta |
| 6. Resultados | Instâncias do gerador (`instance_generator.ipynb`); As-Is vs. Otimizado (nº e horas de setup, atendimento da carteira, vendas perdidas, utilização), com 2–3 exemplos concretos de decisões do modelo explicadas (produtos específicos realocados de máquina e por quê, não só o agregado); resultados computacionais (dimensões, tempo, gap; estratégia em fases se houver) | Vazio | Média (depende do modelo estabilizar) |
| 7. Conclusão | Síntese, limitações, trabalhos futuros | Vazio | Baixa |

Para estilo de escrita (frase, parágrafo, notação, equações, tabelas, citações), ver `CLAUDE_WRITTER.MD` — guia único e vinculante, não repetido aqui.

---

## 5. Backlog priorizado (checklist de execução)

Registro mestre de tarefas. Legenda: **natureza** 🤖 AUTÔNOMO / 🧑 DECISÃO · **status** ⬜ PENDENTE / 🟨 PARCIAL / ✅ FEITO (ver "Como usar este documento"). Ao avançar uma tarefa, atualize sua flag de status aqui.

1. 🧑 ⬜ **Granularidade da notação** — fixar `t` = semana, `d` = dia, `D_t` = dias da semana `t`; declarar horizonte e cadência de replanejamento. Contém **decisão do usuário**: o esquema de desagregação da demanda mensal→semanal (uniforme / por dias úteis / prever já por semana no Nível 0). Uma vez decidido, a redação da notação é 🤖.
2. 🧑 🟨 **Demanda em duas camadas** — separar carteira firme `o_it` (restrição cumulativa, prioridade máxima) de previsão `d̂_it` (venda perdida penalizada) e tornar o estoque de segurança soft. **Parcial**: a carteira já existe no código, mas só no nível de cor (`Demanda_Cor` com prazo, atraso penalizado no MILP) e como desagregação da própria previsão, não como corrente independente; no tático a demanda segue única e o estoque de segurança segue rígido. A decisão "venda perdida vs. backlog" **já foi fechada no `.tex`** a favor de venda perdida na camada de previsão (Seção 3.0), e o `TODO.md` já fixa a direção do resto: prioridade sempre para produção contra pedido, com custos de perda distintos e parâmetro exposto na interface. **Resta decidir** (🧑) se a carteira vira corrente própria no tático, podendo divergir da previsão. Formalização posterior é 🤖.
3. 🤖🧑 🟨 **Correções do modelo algébrico no `.tex`** — adotar a forma linear do balanço (a que o código já usa), definir o setup na fronteira do horizonte/semana, remover a redundância entre `eq:estado_unico` e `eq:capacidade` (com a prosa correspondente, hoje trocada e duplicada) e declarar a premissa da disponibilidade fracionária virando dias inteiros parados no início do período (todos 🤖 — Seção 1.3, itens 1, 3, 8 e 9). O **destino de `z_jd`** — dar papel de decisão real ou remover (item 5) — é 🧑 e destrava a limpeza da redundância.
4. 🤖 ⬜ **Seção "Granularidade das decisões"** no cap. de Descrição do problema (base: Seção 2 deste plano) + figura de arquitetura com horizontes anotados.
5. 🧑🤖 ⬜ **Introdução com pain points** — levantar 3–5 pain points reais do planejamento atual com a operação (🧑, só o usuário tem esse dado); a redação da Introdução a partir deles é 🤖.
6. 🤖 🟨 **Revisão de Literatura** — escrita no `ModelagemAlgebrica.tex` (seção "Revisão de literatura"), 5 subseções (2.1–2.5). Falta a revisão de conteúdo pelo usuário (🧑) — checar adequação ao programa, profundidade esperada, se falta alguma referência que o orientador queira ver citada. Sub-tarefas:
   - 6a. ✅ 2.1 Planejamento hierárquico de produção (HPP).
   - 6b. ✅ 2.2 Dimensionamento de lotes capacitado (CLSP) e taxonomia.
   - 6c. ✅ 2.3 Lot sizing com sequenciamento (small-bucket, setups seq-dependentes, carryover).
   - 6d. ✅ 2.4 Aplicações em indústria de processo (bebidas, block planning).
   - 6e. ✅ 2.5 Posicionamento (tabela de gap, `tab:gap` no `.tex`; subseção renomeada de "Síntese e posicionamento").
   - 6f. ✅ Verificar/consolidar as referências — 23 entradas em `referencias.bib`, verificadas por busca bibliográfica (autor/ano/veículo/páginas). Uma imprecisão do levantamento original foi corrigida no processo: Günther, Grunow & Neuhaus (2006) é sobre tintura de cabelo/*make-and-pack*, não iogurte (corrigido diretamente no `.tex`).
7. 🤖🧑 🟨 **Modelo tático semanal** — formular completo no novo padrão (tabelas + restrições comentadas). Depende das decisões dos itens 1 e 2; feita a decisão, a formalização é 🤖.
8. 🧑🤖 🟨 **Variante do nível operacional de cores** — **implementada no código, ausente do `.tex`**: já existem uma heurística EDD e um MILP tipo DLSP (uma cor por dia, transições entre dias consecutivos da janela), intercambiáveis por `color_method`. Decisões 🧑 restantes (Seção 2.2): assumir a variante implementada e usar a heurística como *baseline* de comparação, ou migrar para 2c; e escolher entre matriz DE-PARA (implementada) e setup por características. Feita a escolha, formalizar no `.tex` — inclusive preenchendo a subseção vazia "Planejamento operacional" — é 🤖.
9. 🤖 ⬜ **EDA do cap. 3** — ABC de produtos, sazonalidade (reaproveitar apêndice de demanda), nº formatos×acabamentos×cores, setups forma vs. cor. Autônoma sobre os dados já no repositório / gerados.
10. 🤖 ⬜ **Experimentos e métricas do cap. de Resultados** — desenhar As-Is vs. Otimizado + resultados computacionais.
11. 🧑 ⬜ **Escopo do Apêndice A** — avaliar as oportunidades e decidir quais entram na dissertação (todas são 🧑; registrar as descartadas como premissas/limitações). Um agente pode preparar a análise de cada uma, mas a decisão de escopo é do usuário.
12. 🤖 ⬜ **Buscar e ler o texto completo de Camargo, Toledo & Almada-Lobo (2012)** — *Journal of the Operational Research Society*, "Three time-based scale formulations for the two-stage lot sizing and scheduling in process industries". **Prioridade elevada**: o `.tex` (subseção 2.4) não só cita `camargo2012` como descreve sua formulação — a variável binária de qualidade que sincroniza as máquinas ativas num microperíodo — a partir do relato de segunda mão do artigo de 2014. Enquanto não se ler o original, o texto afirma conteúdo não verificado. Ver Seção 3.1 e Apêndice A.1.
13. 🧑 ⬜ **Perecibilidade do látex: modelar ou rebaixar** — o `.tex` a declara em `tab:gap`/Posicionamento como característica sem equivalente na literatura, e nenhum dos dois níveis do modelo a representa (Seção 3.0.1). Decidir entre formular (estoque de látex com validade, capacidade de tanque, recebimento diário) e declarar como premissa simplificadora, ajustando o texto do capítulo 2 conforme a escolha. A formalização, se houver, é 🤖.
14. 🤖🧑 ⬜ **Carryover de cor entre janelas** — a Revisão de Literatura promete carryover de estado no nível operacional, mas o MILP de cor paga `setup_time_color_default` em todo primeiro dia de janela, ignorando a cor montada na máquina (Seção 2.2). Implementar a herança da última cor da janela anterior por máquina (🤖) ou retirar a promessa do `.tex` (🧑 decide qual dos dois).
15. 🤖 ⬜ **Absorver o `TODO.md` de engenharia no plano de escrita** — quatro pontos do `TODO.md` têm consequência direta na dissertação: `n` tempos de setup por máquina em vez de alto/baixo (afeta a notação `t^s_j` e a premissa de setup independente do par de produtos); terminologia distinta para setup de `MODELO-TIPO` e de `MODELO-TIPO-COR` (afeta a notação dos dois níveis); lote mínimo (já promovido no Apêndice A.2, faltando só o usuário informar onde e de que tipo é o mínimo); e o contrato tático→diário (Seção 2.3). Refletir cada um na seção correspondente quando o código for tocado.

---

## Apêndice A — Oportunidades conceituais identificadas nos modelos LTPlabs (avaliar)

**Os itens deste apêndice são 🧑 DECISÃO** (backlog item 11): cada "Avaliar" depende de um fato da fábrica que só o usuário confirma. Um agente pode *preparar* a análise (o fenômeno existe? como modelar? custo/benefício), mas a decisão de incluir no escopo — ou registrar como premissa simplificadora — é do usuário. **Duas exceções desde 2026-07-30**: A.2 (lote mínimo) já foi promovido a pendência ativa pelo `TODO.md`, restando só o *como*; A.4 (custo de estoque) deixou de ser decisão de escopo, porque o `.tex` já fechou o custo de oportunidade puro, e virou candidato a análise de sensibilidade.

Padrões presentes em `weekly_planning.tex`, `daily_operationbased.tex` e `daily_jobscheduling.tex` que **não** foram incorporados ao plano principal, mas merecem avaliação caso a caso. Critério para promover ao plano: o fenômeno existe e restringe de fato a operação dos balões; caso contrário, registrar como premissa simplificadora consciente (lista numerada do cap. de Metodologia).

### A.1 Mistura/pigmentação como estágio próprio (fluxo por operações com WIP)
`daily_operationbased.tex` modela roteiros com operações encadeadas e balanço de WIP entre elas (`wip_{p,r,o,s}`), permitindo que uma etapa a montante restrinja a etapa gargalo. Para os balões, a preparação do composto pigmentado (pré-vulcanização + pigmentação) poderia ser uma operação própria alimentando a moldagem — capturando tanques limitados, bateladas de mistura e a disponibilidade de cor como restrição real (nº de cores simultaneamente ativas). É a materialização da analogia xarope↔envase da literatura de refrigerantes (Seção 3). **Avaliar**: a mistura restringe de fato (tanques, tempo de preparo, perecibilidade do látex)? Se não, manter estágio único e declarar premissa.

**Atualização (gabarito formal disponível)**: o MSGLSP de Camargo, Toledo & Almada-Lobo (2012, formulação; 2014, método de solução — ver Seção 3.1) é exatamente essa ideia já formalizada e publicada: um estágio de mistura único alimentando múltiplas máquinas paralelas, sincronizadas por uma variável binária de qualidade ($U_{trk}$) que obriga todas as máquinas ativas num microperíodo a compartilhar a mesma família de mistura. Isso não muda a pergunta em aberto (a mistura de látex restringe de fato?), mas muda o custo de avaliá-la: se a resposta for sim, existe um mecanismo de sincronização pronto para adaptar, em vez de ter que desenhar um do zero. Vale buscar o texto completo do artigo de 2012 antes de decidir.

### A.2 Lote mínimo com continuação entre dias
O padrão `MinLotSize` + variável de continuação (`cont`) garante batelada mínima mesmo quando o lote atravessa a fronteira de dias (lotes de dias adjacentes contam juntos). Relevante se a pigmentação tiver batelada mínima/fixa de mistura.

**Atualização (2026-07-30): promovido de "avaliar" a pendência ativa.** A pesquisa inicial não apontou o fator como relevante, mas o `TODO.md` passou a listar "acrescentar lote mínimo" como item de implementação — o que responde a pergunta em aberto pela afirmativa. Falta apenas o usuário informar **onde** o mínimo se aplica (por cor no operacional, por `MODELO-TIPO` no tático, ou nos dois) e se é físico (batelada de mistura) ou econômico; a formulação a partir daí é 🤖.

### A.3 Estoque em dois estágios / postponement da diferenciação
`weekly_planning.tex` permite que estoque do intermediário ainda-universal (folhas Type 03, via `Multiplier`) conte para a cobertura de serviço do produto final. Análogo para balões: estoque de composto não pigmentado, ou de balão a granel antes da embalagem, como estoque "coringa" que posterga a diferenciação por cor/apresentação. Poderia reduzir estoque de segurança por cor no nível diário. **Avaliar**: em que ponto do processo o balão se torna irreversivelmente cor-específico, e há estoque intermediário na prática?

### A.4 Custo de manutenção de estoque via custo de capital
A referência semanal cobra `WACC/52 × custo unitário × estoque médio` na FO. O modelo dos balões hoje não tem custo de estoque (objetivo puro de custo de oportunidade) — o estoque só é limitado indiretamente. Adicionar o termo WACC evitaria acúmulo gratuito quando há capacidade sobrando e daria fundamento financeiro ao trade-off setup×estoque, aproximando o modelo do CLSP canônico.

**Atualização (2026-07-30): deixou de ser decisão de escopo.** A `tab:gap` do `.tex` já declara o custo de oportunidade puro (sem *holding*) como diferencial do trabalho — hibridizar agora custaria reescrever o Posicionamento. O item permanece como **candidato a análise de sensibilidade** no capítulo de Resultados (rodar com e sem o termo WACC, mostrando o efeito no estoque médio e no giro), não como alternativa de modelagem em aberto.

### A.5 Capacidade externa (máquinas fantasma) com lead time
Terceirização modelada como "ghost machines" com roteiro de operação única, capacidade por turno e lead time de recebimento (`AvailProd` defasado em `L`), sem lógica de setup/equipe. **Avaliar**: a Riberball terceiriza ou tem capacidade externa contratável? Se sim, é um padrão limpo; se não, ignorar.

### A.6 Multi-localidade: transferências com lead time e ponto de reposição
`weekly_planning.tex` estende o tático com filiais de destino: variável de transferência `tr`, estoque no destino, demanda pré-processada por explosão retroativa, ponto de reposição soft e pedidos confirmados por filial (restrição cumulativa C2). **Avaliar**: existe CD/segunda planta/estoque avançado no caso dos balões? Se sim, este é o gabarito; se não, fora de escopo.

### A.7 Granularidade de turno em vez de dia no nível operacional
O modelo diário da LTPlabs usa turno (45 turnos = 15 dias × 3) como bucket, com abertura de turno por máquina (`l_{m,s}`) e o próprio `.tex` dos balões nota que trocas de forma ocorrem "no limite mínimo, entre turnos". A config atual já tem `shifts_per_day = 3`. **Avaliar**: as decisões operacionais reais (troca de forma, troca de cor, paradas) acontecem por turno ou por dia? O bucket deve refletir isso.

### A.8 Restrições de equipe por área
Equipes por área/turno limitando quantas máquinas operam simultaneamente (`Crew`, `CrewConsumption`). O dimensionamento de operadores foi **removido deliberadamente** do escopo em commits recentes do projeto — retomar apenas se a mão de obra for gargalo real de ativação de máquinas; caso contrário, declarar premissa ("operadores não restringem").

### A.9 Precedências entre máquinas no sequenciamento
`daily_jobscheduling.tex` herda precedências de produção do nível diário (arestas job→job), conecta máquinas em componentes e resolve cada componente de forma independente — com origem fictícia por máquina carregando o estado de setup do turno anterior. Relevante para a variante 2c se a batelada de composto de uma cor precisar anteceder, no mesmo dia, a moldagem dessa cor (liga-se a A.1). **Avaliar** junto com A.1.

### Ressalva geral
Os três documentos LTPlabs são formulações de trabalho (contêm notas de revisão e formulações abandonadas em anexo). Servem como fonte de **padrões**, não como gabarito a copiar: o problema dos balões é de BOM raso e estágio único (ou dois, se A.1 prosperar) — importar estrutura de roteiros/operações/BOM multinível sem necessidade real só inflaria o modelo e o texto. A régua é sempre o fenômeno físico da fábrica de balões.
