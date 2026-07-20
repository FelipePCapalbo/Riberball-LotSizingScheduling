# Plano de evolução da dissertação — descrição do problema, granularidade e alinhamento com a literatura

Documento de planejamento para a reescrita do `ModelagemAlgebrica.tex`, tendo como referência estrutural a dissertação de Mateus Carmesim Marques (FEUP, 2026), *A Mathematical Optimisation Framework to Medium-Term Production Planning in the Metal Packaging Industry*.

Referências adicionais de modelagem (formulações LTPlabs da mesma empresa da tese, no repositório): `weekly_planning.tex` (tático semanal com abastecimento multi-filial), `daily_operationbased.tex` (curto prazo por turno, baseado em operações, setup por características) e `daily_jobscheduling.tex` (sequenciamento intra-turno). Juntas, formam uma hierarquia real de três níveis — semanal → diário/turno → sequenciamento — que valida a arquitetura proposta na Seção 2. O que dessas formulações já foi incorporado está nas Seções 2 e 5; o que fica como oportunidade a avaliar está no Apêndice A.

---

## 1. Diagnóstico: o que a tese de referência faz e o documento atual ainda não faz

### 1.1 Comparação estrutural

| Elemento da tese de referência | Situação no `.tex` atual |
|---|---|
| **Problem statement guiado por pain points**: 5 dores concretas levantadas com stakeholders (previsão com 50–60% de acerto, política de estoque fragmentada, compras decididas só por preço, lead times sem visibilidade, lotes pequenos com setups frequentes), cada uma retomada depois pelos módulos da solução | Introdução e Contextualização vazias; a motivação existe apenas implícita na seção de planejamento tático |
| **Figura de arquitetura de decisão com granularidade anotada**: cada módulo carrega horizonte e frequência (8 meses/semanal, 15 dias/diário/turno) e as setas mostram o que flui entre módulos | Não existe visão de arquitetura; o leitor não sabe que há (nem haverá) níveis de decisão distintos |
| **Escopo e premissas explícitos**: seção "Scope of the Project" + lista numerada de 11 premissas simplificadoras (demanda determinística, setups independentes de sequência no nível semanal, calendário de turnos como parâmetro, backordering penalizado, capacidade de armazém rígida...) | Premissas espalhadas e implícitas no texto corrido; nada é declarado como simplificação consciente |
| **Capítulo "The Problem" completo**: contexto industrial → processo produtivo → abordagem proposta → estrutura dos dados → preparação de dados → **EDA quantitativa** (ABC-SEIL, sazonalidade 3:1 pico/vale, complexidade da BOM) → síntese. A EDA *dimensiona* o problema antes de qualquer equação | Existe apenas a seção "Processo produtivo" (boa, com fluxograma TikZ) e um parágrafo de planejamento tático; não há caracterização quantitativa do portfólio, da sazonalidade nem dos setups |
| **Formulação apresentada didaticamente**: tabelas de conjuntos/parâmetros/variáveis; restrições agrupadas (A: estoque/fluxo, B: capacidade, C: carteira) e **cada equação seguida de um parágrafo de prosa** explicando papel e consequências | Tabelas de notação ✓; mas as 5 restrições são explicadas em dois parágrafos condensados, sem agrupamento temático |
| **Demanda em camadas de prioridade**: pedidos confirmados (restrição cumulativa C1, penalidade máxima) > demanda prevista > estoque de segurança > estoque de ciclo — tudo *soft constraint* com pesos configuráveis, garantindo viabilidade sob capacidade apertada | O modelo trata uma demanda única `d_it`; a carteira firme não aparece; o estoque de segurança é restrição **rígida** (risco de inviabilidade) |
| **Resultados em dois planos**: (i) qualidade do plano As-Is vs. Otimizado (nº de setups, horas de setup, OEE, tamanho médio de lote, com exemplos de produtos específicos realocados); (ii) resultados computacionais (dimensões do MIP antes/depois do presolve, tempo, gap, estratégia de solução em duas fases) | Não existem capítulos de resultados |
| **Granularidade temporal definida**: bucket = semana, horizonte móvel de 32 semanas, re-execução semanal (rolling horizon) declarados desde o abstract | **Indefinida**: `T` são "períodos" genéricos; `D_t ⊆ D` insinua dias dentro de períodos, mas semana nunca é fixada; o leitor não sabe a cadência de replanejamento |

### 1.2 O que o documento atual já tem de bom (preservar e valorizar)

- **Fluxograma do processo produtivo** em TikZ — análogo direto da Figure 3.1 da tese; falta apenas anotar onde ocorre a diferenciação por cor (mistura/pigmentação) e onde ocorrem os setups longos (troca de formas na moldagem).
- **Modelo próprio de previsão de demanda** (hierárquico top-down com RLS) — a tese de referência *recebe* a previsão pronta de outro módulo; ter modelagem própria de demanda é um diferencial da dissertação e merece capítulo próprio bem conectado ao restante.
- **Apêndice com exemplo numérico** completo da previsão — a tese de referência não tem nada equivalente; manter.

### 1.3 Problemas técnicos do modelo algébrico atual (corrigir na reescrita)

1. **Produto bilinear na restrição de balanço** (`eq:balanco`): o termo `(h_jd − t^s_j·δ_ijd)·s_ijd·p_ij` multiplica duas binárias (`δ·s`). A implementação (`optimization/solver.py`) já usa a forma **linear** `(h_jd·s_ijd − t^s_j·δ_ijd)·p_ij` — o documento deve adotar essa forma (válida porque setup implica estado ativo).
2. **Estoque de segurança rígido** (`eq:seguranca`): com capacidade apertada o modelo fica inviável. Adotar o padrão da tese: variável de folga penalizada na FO, com peso menor que o da demanda. (Detalhe da implementação a documentar: para a cobertura funcionar nos últimos períodos, a demanda é estendida além do horizonte repetindo a sazonalidade do ano anterior — `_extend_dates_with_seasonality`.)
3. **Setup na fronteira entre períodos**: `δ_ijd ≥ s_ijd − s_ij,d−1` precisa de definição para o primeiro dia do horizonte e para a emenda entre semanas quando o modelo for particionado (setup carryover). Hoje o código encadeia os dias de forma contígua entre períodos, o que resolve dentro de uma rodada mas não entre rodadas do rolling horizon.
4. **Demanda única**: separar `d_it` em carteira firme e previsão (ver Seção 2).
5. **Variável `z_jd` inerte**: existe no `.tex` e no código (`Z_day`), mas nada a penaliza nem a força — o solver a deixa sempre em 0 e as paradas reais entram via `h_jd = 0`. Ou ela ganha papel de decisão (parada endógena, com custo/motivo) ou sai da formulação e do texto.
6. **"Período" não é o que o texto sugere**: na implementação `T` são **meses** (colunas `MM/AAAA` da planilha de demanda) e `D_t` são ~30 dias genéricos de 24 h — não há calendário real. O texto fala em "plano semanal" no planejamento tático, mas o modelo roda mensal. Essa incoerência entre texto, modelo e código é exatamente a dor de granularidade que a Seção 2 ataca.
7. **Nomenclatura enganosa na config**: `coverage_months` (o α) chega ao solver como argumento `safety_stock_pct`, mas é contagem de períodos, não percentual — renomear quando o código for tocado.

---

## 2. Arquitetura de decisão hierárquica proposta

### Ponto de partida: o que a implementação faz hoje

Resumo do estado atual (PuLP MILP único, `optimization/solver.py` + `optimization/planner.py`):

- **Bucket tático = mês** (demanda, estoque `I[(p,t)]`, venda perdida `K[(p,t)]`, cobertura α em meses via `coverage_months`); **scheduling = dia** (`S_state[(m,p,d)]`, `Delta_Setup[(m,p,d)]`), com cada mês expandido em `round(7 × 4.33) = 30` dias uniformes de `3 turnos × 8 h = 24 h` (`config/capacity.json`). Não há calendário real: disponibilidade mensal fracionária vira dias inteiros parados **no início** do mês.
- **Não existe variável contínua de quantidade**: a produção do dia é implícita (`S_state × horas do dia × produtividade`) — a máquina produz o dia inteiro ou nada.
- **Setup por máquina em dois níveis** (`setup_time_high` = 7 h só para a máquina 17, `setup_time_low` = 3 h para as demais, `config/machines.json`); não depende do par de produtos. O `TODO.md` já registra a intenção de generalizar.
- **Objetivo = custo de oportunidade** (receita perdida em setup + vendas perdidas), sem custo de estoque — coerente entre código e `.tex`.
- **Sem cores em lugar nenhum** do código; produto = `MODELO-TIPO` (formato+acabamento), como o `.tex` declara.
- O modelo de previsão de demanda do `.tex` **não está implementado**; o código lê demanda pronta do Excel.

Ou seja: o modelo atual já é **híbrido mensal/diário num MILP só** — mistura os dois níveis e por isso a granularidade parece indefinida no texto. A proposta abaixo reparticiona em níveis explícitos (e move o bucket tático de mês para **semana**), a ser apresentada no documento com uma figura de arquitetura no estilo da Figure 1.1 da tese (cada caixa com horizonte e granularidade anotados).

### 2.0 Nível 0 — Previsão de demanda (existente)

- Horizonte: meses/semanas à frente; granularidade: balão (formato+acabamento).
- Saídas para o nível tático: **duas correntes de demanda** — a previsão `d̂_it` (modelo hierárquico já formulado) e a **carteira firme** `o_it` (pedidos confirmados, vinda do comercial, não modelada estatisticamente).
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
- **O que deixa de existir neste nível**: índice de dia, cores, sequenciamento. A capacidade semanal da máquina vira `H_jt = Σ_d h_jd` menos paradas programadas.
- **Implicação de dados da migração mês→semana**: a demanda hoje entra mensal (colunas `MM/AAAA` do Excel); será preciso definir a desagregação mensal→semanal (uniforme, por dias úteis, ou já prever por semana no Nível 0) e substituir o calendário genérico de 30 dias × 24 h por um calendário real de dias úteis/turnos por semana. A conversão de disponibilidade fracionária em dias inteiros parados no início do mês também deve ser repensada nessa passagem.
- **Ganho de tratabilidade**: sem o índice diário, este nível dispensa as binárias `S_state` por dia — a alocação vira binária semanal (máquina×balão×semana) com variável contínua de horas/quantidade, um CLSP clássico bem menor que o MILP atual.

### 2.2 Nível 2 — Programação operacional diária (scheduling + cores)

- **Horizonte**: 1–2 semanas; **bucket**: dia (ou turno). Congela a primeira semana do plano tático e a detalha.
- **Recebe do tático**: quantidades semanais por balão×máquina (metas), alocações máquina↔formato.
- **Decide**: desagregação da quantidade semanal **por cor**; em que dia produzir cada cor; sequência dentro da máquina, com **setup/limpeza dependente da troca de cor**.
- **Carteira também aqui**: os pedidos firmes têm datas e cores; a desagregação por cor deve priorizar as cores da carteira antes das cores estimadas do mix de previsão.
- **Três variantes de formulação** (o documento pode apresentar as três e justificar a escolha; decisão em aberto):

| | **2a — MILP com sequenciamento embutido** | **2b — MILP diário + heurística de sequenciamento** | **2c — MILP diário por atributos + MILP de sequenciamento (padrão LTPlabs)** |
|---|---|---|---|
| Formulação | Tipo GLSP/CLSD: microperíodos ou variáveis de sequência por máquina-dia | MILP small-bucket decide *quanto de cada cor por dia/máquina* (sem ordem); heurística ordena dentro do dia | MILP diário conta o setup por **características ativas no bucket** (sem ordem), como `daily_operationbased.tex`; um segundo MILP pequeno sequencia dentro do dia/turno, como `daily_jobscheduling.tex` |
| Setups de cor | Exatos, dependentes de sequência | Aproximados no MILP (nº de cores ativas × tempo de limpeza); ordem real dada pela heurística (claro→escuro, estilo *block planning*) | Aproximados no MILP diário (paga-se 1 setup por característica ativa não herdada do dia anterior); **exatos** no MILP de sequenciamento (caminho tipo ATSP por máquina, custo de transição = características novas exigidas) |
| Custo computacional | Alto (binárias de sequência explodem com cores×dias×máquinas) | Baixo; MILP pequeno + regra O(n log n) | Médio; o sequenciamento decompõe por máquina-dia (instâncias minúsculas, resolvidas de forma independente) |
| Aderência à prática | Ótimo teórico | Reflete a regra que a fábrica já usa; fácil de validar | Padrão usado em produção real na indústria de embalagens (LTPlabs); mantém otimalidade local na sequência sem inflar o modelo diário |
| Na dissertação | Boa contribuição metodológica se resolver em tempo aceitável | Boa justificativa de engenharia | Melhor dos dois mundos e permite comparação experimental 2b vs. 2c (heurística vs. sequenciamento exato) |

- **Mecanismo de setup por características** (incorporado de `daily_operationbased.tex` / `daily_jobscheduling.tex`, e um encaixe natural para os balões): cada produção exige um conjunto de características de setup — **formato/forma** (tipo de setup longo) e **cor do composto** (tipo de setup curto, de limpeza) — e a transição paga apenas as características exigidas que a máquina ainda não tem: `d_ij = Σ γ(tipo)` sobre as características de `j` ausentes em `i` (abandonar uma característica é grátis, logo o custo é direcional — exatamente a assimetria claro→escuro vs. escuro→claro da limpeza de pigmento). Isso unifica os dois tipos de setup do problema num único formalismo, com um tempo `γ` por tipo, em vez de duas modelagens ad hoc.
- **Carryover de estado de setup entre dias** (idem): a máquina permanece configurada (forma + última cor) ao atravessar dias e até dias inativos — variáveis de estado de fim de dia (`endState`/`lastState` na referência) definem a "origem" do dia seguinte, e produzir a mesma configuração no dia seguinte não paga novo setup. Resolve formalmente o item 3 da Seção 1.3 (fronteira entre períodos), tanto no nível diário quanto na emenda com o rolling horizon.

### 2.3 Acoplamento entre níveis

- Metas do tático entram no diário como alvos com **folga penalizada** (não como igualdade rígida) — desvios são possíveis, mas custam; isso evita propagar inviabilidade para baixo. Mecanismo concreto (incorporado de `daily_operationbased.tex`): um parâmetro de **estoque objetivo ao fim do horizonte diário** (`ObjectiveStock_p`, definido pelo plano semanal) com variável de falta penalizada — o diário persegue o estado que o tático planejou para o fim da janela, em vez de replicar quantidades semana a semana.
- Do sequenciamento para cima (incorporado de `daily_jobscheduling.tex`): a duração do dia/turno **não é restrição de viabilidade no sequenciador** — se a sequência ótima estourar o turno, o excedente (*overrun*) é reportado como *feedback* ao nível diário, que reage na rodada seguinte. Evita inviabilidades artificiais em cascata.
- O realizado/replanejado do diário realimenta o tático na re-execução seguinte (rolling horizon): estoques atualizados, carteira consumida, paradas ocorridas, estado de setup herdado (forma + cor montadas em cada máquina).
- No documento: uma subseção "Coordenação hierárquica" explicando esse contrato entre níveis (a tese faz isso ao descrever como o Módulo B alimenta C e D).

---

## 3. Alinhamento com a literatura (posicionamento do problema)

Vocabulário e referências para a Revisão de Literatura e para dar nome preciso ao problema.

### 3.1 Classes de problema

- **Nível tático ≈ CLSP** (*Capacitated Lot Sizing Problem*, big-bucket) em **máquinas paralelas heterogêneas** (unrelated: `p_ij` distintos, compatibilidades próprias), com custos/tempos de setup e **vendas perdidas** (lost sales). Surveys: Karimi, Fatemi Ghomi & Wilson (2003); Jans & Degraeve (2008); Buschkühl et al. (2010).
- **Nível diário ≈ lot sizing and scheduling small-bucket**: GLSP (Fleischmann & Meyr, 1997), CLSD (Haase, 1996), PLSP — família com **setups dependentes de sequência**, que é o caso das trocas de cor. Survey de modelos integrados: Copil, Wörbelauer, Meyr & Tempelmeier (2017); Drexl & Kimms (1997).
- **Estrutura em níveis ≈ Hierarchical Production Planning**: Hax & Meal (1975), Bitran & Hax (1977) — o esquema clássico *família → item* corresponde exatamente a *formato+acabamento → cor*. Citar também a Supply Chain Planning Matrix (Stadtler, 2005) para ancorar tático vs. operacional, como faz o cap. 2 da tese de referência.
- **Analogia industrial mais próxima: bebidas/refrigerantes** — problema de dois níveis xarope↔envase é estruturalmente idêntico a composto pigmentado↔moldagem: Ferreira, Morabito & Rangel (2009, 2010); Toledo et al. (2012). Literatura brasileira, abundante e diretamente comparável.
- **Sequência natural de limpeza** (claro→escuro) ≈ *block planning* em indústrias de processo (Günther, Grunow & Neuhaus, 2006 — indústria de iogurte/laticínios, onde sabores seguem ordem fixa de contaminação).

### 3.2 O que o problema dos balões tem de particular (a contribuição)

- Perecibilidade do látex (recebimento diário, estoque em tanques) — restrição de matéria-prima incomum na literatura de CLSP.
- Dois tipos de setup em escalas de tempo muito diferentes: troca de forma (horas–dias, decidida no tático) vs. troca de cor (limpeza, decidida no operacional) — motiva naturalmente a hierarquia.
- Função objetivo por **custo de oportunidade** (receita perdida em setup + vendas perdidas), sem custo de estoque explícito — diferenciar do CLSP canônico (setup + holding) e justificar.
- Integração previsão própria + otimização (o Nível 0 é do próprio trabalho).

---

## 4. Plano de reescrita do documento, capítulo a capítulo

Esqueleto alvo (espelha a tese de referência, adaptado a dissertação com modelagem própria de demanda):

| Cap. | Conteúdo | Estado atual | Prioridade |
|---|---|---|---|
| 1. Introdução | Contextualização (indústria de balões, empresa); **pain points** do planejamento atual (levantar 3–5 com a operação: como se planeja hoje, onde dói); objetivos; estrutura do documento | Vazio | Alta |
| 2. Revisão de literatura | Hierarquia de planejamento (Stadtler/Anthony); famílias de lot sizing (CLSP→GLSP/CLSD); HPP; aplicações em indústria de processo (bebidas, block planning); fecho conectando ao problema | Vazio | Alta |
| 3. Descrição do problema | Contexto industrial e de planejamento (MTS vs. carteira, quem decide o quê, cadência); processo produtivo (manter fluxograma, anotar diferenciação de cor e setups); **granularidade das decisões** (semana/dia — Seção 2 deste plano); **EDA**: ABC de produtos, sazonalidade (reaproveitar dados do apêndice), nº formatos×acabamentos×cores, tempos de setup forma vs. cor; síntese | Parcial (só processo produtivo) | **Máxima** — é a dor central apontada |
| 4. Modelo de demanda | Capítulo atual, quase pronto; conectar saídas às duas correntes (previsão + carteira) e ao α do tático | Bom | Baixa |
| 5. Metodologia (otimização) | Premissas numeradas; **modelo tático semanal** (notação em tabelas, FO, restrições agrupadas A/B/C e comentadas uma a uma); **modelo operacional diário** (variante 2a, 2b ou 2c, com setup por características e carryover de estado); coordenação hierárquica | Parcial (modelo monolítico defasado) | Alta |
| 6. Resultados | Instâncias do gerador (`instance_generator.ipynb`); As-Is vs. Otimizado (nº e horas de setup, atendimento da carteira, vendas perdidas, utilização); resultados computacionais (dimensões, tempo, gap; estratégia em fases se houver) | Vazio | Média (depende do modelo estabilizar) |
| 7. Conclusão | Síntese, limitações, trabalhos futuros | Vazio | Baixa |

### Recomendações de escrita extraídas da tese de referência

1. **Uma restrição por vez**: equação → parágrafo de prosa explicando papel, casos-limite e interação com as demais. Agrupar por tema (fluxo/estoque, capacidade, carteira).
2. **Premissas como lista numerada** em seção própria ("Model Features and Assumptions") — cada simplificação declarada e justificada.
3. **Granularidade anotada em toda figura de arquitetura** (horizonte + frequência em cada caixa).
4. **Resultados sempre As-Is vs. modelo**, com 2–3 exemplos concretos de decisões do modelo explicadas (a tese mostra produtos específicos realocados de máquina e o porquê) — isso demonstra que o autor entende o comportamento do modelo, não só o agregado.
5. **Motivar o horizonte com a sazonalidade** (a tese justifica 32 semanas pela amplitude sazonal 3:1) — o capítulo de demanda já fornece a razão pico/vale para esse argumento.
6. Declarar **rolling horizon** e cadência de re-execução desde a introdução.

---

## 5. Backlog priorizado (checklist de execução)

1. [ ] Fixar a granularidade na notação: `t` = semana, `d` = dia, `D_t` = dias da semana `t`; declarar horizonte e cadência de replanejamento no texto — e decidir a desagregação da demanda mensal→semanal.
2. [ ] Separar a demanda em carteira firme `o_it` (restrição cumulativa, prioridade máxima) e previsão `d̂_it` (venda perdida penalizada); tornar o estoque de segurança soft.
3. [ ] Adotar no `.tex` a forma linear do balanço (a que o código já usa), definir o setup na fronteira do horizonte/semana e decidir o destino de `z_jd` (dar papel real ou remover).
4. [ ] Escrever a Seção "Granularidade das decisões" no cap. de Descrição do problema (base: Seção 2 deste plano) + figura de arquitetura com horizontes anotados.
5. [ ] Levantar 3–5 pain points reais do planejamento atual com a operação e escrever a Introdução.
6. [ ] Escrever a Revisão de Literatura (base: Seção 3 deste plano).
7. [ ] Formular o modelo tático semanal completo no novo padrão (tabelas + restrições comentadas).
8. [ ] Escolher a variante do nível diário — 2a, 2b ou 2c (ou comparar 2b vs. 2c como experimento) — e formular o modelo diário de cores com setup por características e carryover de estado.
9. [ ] Montar a EDA do cap. 3 com dados reais/gerados (ABC, sazonalidade, setups forma vs. cor).
10. [ ] Planejar experimentos e métricas do capítulo de Resultados (As-Is vs. Otimizado + computacional).
11. [ ] Avaliar as oportunidades do Apêndice A e decidir quais entram no escopo da dissertação (registrar as descartadas como premissas/limitações).

---

## Apêndice A — Oportunidades conceituais identificadas nos modelos LTPlabs (avaliar)

Padrões presentes em `weekly_planning.tex`, `daily_operationbased.tex` e `daily_jobscheduling.tex` que **não** foram incorporados ao plano principal, mas merecem avaliação caso a caso. Critério para promover ao plano: o fenômeno existe e restringe de fato a operação dos balões; caso contrário, registrar como premissa simplificadora consciente (lista numerada do cap. de Metodologia).

### A.1 Mistura/pigmentação como estágio próprio (fluxo por operações com WIP)
`daily_operationbased.tex` modela roteiros com operações encadeadas e balanço de WIP entre elas (`wip_{p,r,o,s}`), permitindo que uma etapa a montante restrinja a etapa gargalo. Para os balões, a preparação do composto pigmentado (pré-vulcanização + pigmentação) poderia ser uma operação própria alimentando a moldagem — capturando tanques limitados, bateladas de mistura e a disponibilidade de cor como restrição real (nº de cores simultaneamente ativas). É a materialização da analogia xarope↔envase da literatura de refrigerantes (Seção 3). **Avaliar**: a mistura restringe de fato (tanques, tempo de preparo, perecibilidade do látex)? Se não, manter estágio único e declarar premissa.

### A.2 Lote mínimo com continuação entre dias
O padrão `MinLotSize` + variável de continuação (`cont`) garante batelada mínima mesmo quando o lote atravessa a fronteira de dias (lotes de dias adjacentes contam juntos). Relevante se a pigmentação tiver batelada mínima/fixa de mistura. **Avaliar**: existe lote mínimo econômico ou físico por cor? (Na pesquisa inicial esse fator não foi apontado como relevante.)

### A.3 Estoque em dois estágios / postponement da diferenciação
`weekly_planning.tex` permite que estoque do intermediário ainda-universal (folhas Type 03, via `Multiplier`) conte para a cobertura de serviço do produto final. Análogo para balões: estoque de composto não pigmentado, ou de balão a granel antes da embalagem, como estoque "coringa" que posterga a diferenciação por cor/apresentação. Poderia reduzir estoque de segurança por cor no nível diário. **Avaliar**: em que ponto do processo o balão se torna irreversivelmente cor-específico, e há estoque intermediário na prática?

### A.4 Custo de manutenção de estoque via custo de capital
A referência semanal cobra `WACC/52 × custo unitário × estoque médio` na FO. O modelo dos balões hoje não tem custo de estoque (objetivo puro de custo de oportunidade) — o estoque só é limitado indiretamente. Adicionar o termo WACC evitaria acúmulo gratuito quando há capacidade sobrando e daria fundamento financeiro ao trade-off setup×estoque, aproximando o modelo do CLSP canônico. **Avaliar**: manter a tese do custo de oportunidade puro (diferencial do trabalho, Seção 3.2) ou hibridizar com holding cost? Bom candidato a análise de sensibilidade no cap. de Resultados.

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
