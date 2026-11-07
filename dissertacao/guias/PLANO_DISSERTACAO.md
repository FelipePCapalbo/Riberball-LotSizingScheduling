# Plano da dissertação

Estado em 2026-11-06. Este plano registra o que está decidido, o que falta e o que depende do usuário. Ele não
repete o conteúdo do texto.

## Fontes de verdade

- Texto e formulação: `dissertacao/ModelagemAlgebrica.tex`.
- Estilo de escrita, notação, ABNT e o que nunca entra no texto: `dissertacao/guias/CLAUDE_WRITER.md`.
- Implementação e convenções de dados (lacunas, estados fictícios, guardas de viabilidade): `optimization/README.md`.
  Nada disso entra no `.tex`.
- Pendências de dados e de engenharia: `TODO.md`.

Cada conceito tem um único lugar no texto; a seção a jusante que precisa dele referencia a de montante com `\ref`, sem repetir. Toda mudança no `.tex` passa por aprovação do usuário. Quando mexe na formulação, a sessão que implementa o código
é avisada com os labels afetados.

## 1. Estado do texto

| Seção | Estado |
|---|---|
| Pré-textuais (ABNT, classe `abntex2`, visual do TCC) | Escritos. Resumo e abstract são rascunho, sem a frase de resultados. Dedicatória, agradecimentos e epígrafe com marcador. Ficha catalográfica (BCo) e folha de aprovação a inserir. |
| 1 Introdução | Contextualização, mercado, desafios (dificuldade mecânica e de decisão), objetivos, justificativa, organização. Falta o panorama mercadológico (marcador). |
| 2 Revisão de literatura | Hierárquico; problemas de lot sizing (CLSP, integrados, carryover/crossover, setups em duas escalas, síntese); MTO/MTS; custo de estoque; indústria de processo; posicionamento (único ponto da revisão que fala do modelo). Marcadores: modelos MTS com estoque de segurança e atraso; outras justificativas do custo de estoque. Falta a revisão de conteúdo pelo usuário e pelo orientador. |
| 3 Processo produtivo | Fluxo, máquinas e setups, planejamento tático e operacional (sem decisões de modelo). Marcadores: as-is de cada nível; símbolos da figura a rever. |
| 4 Demanda | Natureza, carteira e previsão (único lugar que define as classes e MTS/MTO como atributo do SKU), dados históricos, caracterização da série (resultados dos testes em marcador). |
| 5 Previsão de demanda | Modelo hierárquico com nível variável (RLS, sazonalidade só com dois ciclos), medida do erro com origem rolante e comparadores, avaliação na base M5 (quadro e duas figuras em pgfplots, gerados por `scripts/forecast_comparison.py`). |
| 6 Modelo de otimização | Arquitetura em dois níveis (escalas, horizonte rolante, o que desce e sobe), premissas, notação comum, semanal, operacional, sequenciamento. |
| 7 Resultados | 7.1 Previsão da demanda da fábrica (quadro contra a previsão praticada). Faltam os experimentos de otimização. |
| Conclusão | Não iniciada. |

## 2. Decisões de modelagem fechadas

Ficam registradas para que nenhuma sessão as reabra sem o usuário.

- Arquitetura em três etapas:
  - o semanal, agregado por balão;
  - o operacional por turno, que aloca sem sequenciar;
  - o sequenciamento das corridas por heurística.
  - O único vínculo entre o semanal e o operacional é a meta de estoque ao fim de cada semana detalhada, `Î_it = I_it`
    para balão com SKU MTS e zero para os demais.
- Agregação: o semanal planeja por balão porque a troca de forma domina e a previsão agregada erra menos. A cor e o
  destino do estoque ficam no operacional. As duas razões são hipóteses a demonstrar nos Resultados.
- Demanda em duas classes sobre estoque único:
  - a carteira, cujo atraso é transportado, com `b_0` como dado inicial;
  - a previsão líquida da carteira, sem fronteira de consumo, cuja falta é venda perdida.
  - MTS/MTO é atributo do SKU.
- Objetivo lexicográfico com trava exata entre estágios: atraso, venda perdida (só no semanal), meta ou estoque
  mínimo, e por fim custo de *setup* e de carregamento. O atendimento nunca é trocado por custo.
- Estoque mínimo nos balões com SKU MTS: uma semana de consumo médio do horizonte vezes `(1 + MAPE)`, como meta
  suave.
- Capacidade do armazém `Ω` nos dois níveis. A composição do estoque é decisão do modelo.
- Carregamento `h_i = (θ/52) v_i` sobre o estoque de fim de período.
- Operacional:
  - a forma é tratada como fluxo entre turnos, com o arco que a mantém;
  - parâmetros por SKU herdados do balão;
  - reserva de cor conservadora, o pior tempo de entrada;
  - troca de forma que atravessa turnos (`w_js`, *crossover*);
  - lote mínimo por corrida;
  - horizonte de várias semanas, `T^O`.
- O semanal desconta o *setup* pela mesma regra do operacional (`eq:setup_semanal`), para os dois níveis enxergarem
  a mesma capacidade.
- Sequenciamento:
  - critério lexicográfico: violação, depois *setup* de cor, depois antecipação;
  - a antecipação move só quantidade planejada e só para mais cedo, para qualquer máquina com a forma montada, sem
    criar troca de cor.
- Célula vazia da matriz de cores significa limpeza completa do circuito. O tratamento numérico dela fica no código.
- Notação:
  - `k` é o SKU e `a` a *feature* do modelo de demanda;
  - `n` é a posição na sequência;
  - as descrições das tabelas seguem a ordem dos índices.

## 3. Pendências

- Resultados:
  - O usuário autorizou que o gerador escreva a forma inicial de todas as máquinas. A sessão do código vai medir de
    novo a pequena e a grande, já com o `τ_i` alinhado.
  - Os experimentos estão no `TODO.md`:
    - *setup* de forma contra *setup* de cor;
    - erro da previsão por balão contra por SKU;
    - semanal agregado contra semanal por SKU;
    - variação de `Ω`;
    - variação de `|T^O|`.
  - Números a reportar: reserva de cor contra troca real e quantidade antecipada pelo sequenciamento.
- Máquinas de duas cores (decisão do usuário em 2026-11-06: só figura e texto por enquanto). Na máquina de uma cor a
  cadeia gira num plano vertical (eixo paralelo ao chão); na de duas cores gira num plano horizontal (eixo
  perpendicular ao chão), e cada lado do laço passa por um tanque próprio: duas cores ao mesmo tempo, mesmo formato.
  O modelo ainda trata toda máquina como um circuito único de cor. Para incorporar:
  - no operacional, os dois lados com metade da taxa da máquina, cada um com a sua corrida de cor, reserva e capacidade;
  - os dois lados de uma máquina compartilham o estado de forma, a troca de forma e o *crossover*;
  - o semanal não muda, desde que `p_ij` seja a taxa total da máquina;
  - os dados precisam do tipo de cada máquina (uma ou duas cores);
  - o sequenciamento passa a ordenar por lado.
- Posição da lavagem em água quente na sequência da máquina (desenhada depois da estufa): confirmar com o usuário.
- Resumo e abstract: acrescentar os resultados e revisar.
- Justificativa do trabalho, na Introdução: o planejamento atual da fábrica funciona corretamente, mas é feito sem
  automatização; o trabalho propõe um sistema de apoio à decisão que formaliza e automatiza esse planejamento. A
  frase entra na seção de objetivo ou numa seção própria de justificativa, sem desqualificar a prática atual.
- Citar a dissertação de Marques (FEUP, 2026), *A Mathematical Optimisation Framework to Medium-Term Production
  Planning in the Metal Packaging Industry*, que serviu de referência estrutural. Entra no `referencias.bib` como
  `@mastersthesis` e é citada onde a estrutura ou a abordagem a acompanha (Revisão, aplicações em indústria de
  processo). Confirmar com o usuário a grafia do nome do autor e os dados da referência.
- Confirmar com o PPGEP se o programa já adota a NBR 14724:2024.
- Pseudocódigo da heurística: depende de instalar `algorithm2e` localmente.

## 4. Backlog para revisão do usuário

Ideias de planos anteriores, mantidas para o usuário revisar. Nenhuma está no texto como compromisso.

1. Análise exploratória dos dados no capítulo de processo: curva ABC dos balões, sazonalidade, número de formatos,
   acabamentos e cores, tempos de troca de forma contra cor. Parte disso coincide com os testes do desenho de
   agregação.
2. Figura da arquitetura de decisão, com o horizonte e o *bucket* de cada etapa anotados.
3. Formato dos Resultados:
   - comparação entre o plano realizado (As-Is) e o otimizado: número e horas de *setup*, atendimento, utilização;
   - resultados computacionais: dimensões, tempo, gap por estágio;
   - dois ou três exemplos concretos de decisões do modelo, explicados.
4. Ler o texto completo de Camargo, Toledo e Almada-Lobo (2012). A Revisão descreve a formulação desse artigo a
   partir do relato do artigo de 2014, sem verificação no original.
5. Oportunidades levantadas nos modelos LTPlabs, a decidir se entram como limitação ou trabalho futuro:
   - mistura e pigmentação como estágio próprio, com o gabarito do MSGLSP;
   - estoque intermediário que adia a diferenciação por cor;
   - capacidade externa;
   - múltiplas plantas;
   - restrição de equipe;
   - precedências entre máquinas.
6. Dados reais: conversão da demanda mensal para semanal e calendário real de paradas. Hoje estão no `TODO.md`.
