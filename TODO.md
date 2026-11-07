# Pendencias

## Tratabilidade do modelo por turno (prioridade)

Modelo resolvido como formulado, sem heuristica de resolucao. Medicoes anteriores, feitas com CBC
(hoje removido), mostravam que a partir de `grande` nao havia solucao inteira em 900 s.

- Remedir a escala nas cinco instancias com Gurobi e OR-Tools (SCIP): binarias, status, tempo,
  gap e `hit_time_limit`, 3 posicoes/turno, 1 semana congelada.

Se a escala continuar insuficiente, o caminho e' de **formulacao**, nao de heuristica de resolucao:

- apertar os limitantes big-M da restricao de lote minimo por turno (hoje `p_ij * b_js`);
- buscar desigualdades validas para a estrutura de posicoes contiguas;
- avaliar se `positions_per_shift = 2` preserva as solucoes relevantes.

Reportar no capitulo de Resultados o status e o gap de cada instancia, nao apenas o custo.

## Dados

- Levantar em campo quais máquinas são de duas cores. Hoje o arquivo ajustado marca 7 das 28 de forma sintética
  (1, 3, 5, 10, 13, 16, 19), e o tipo pode ser trocado pela interface.

- Feito: `scripts/input_adjuster.py` converte `data/brutos/input_asis.xlsx` para `data/input_asis_ajustado.xlsx`
  no contrato semanal.
- Levantar em campo as quatro dimensoes que a operacao nao registra e que hoje sao sinteticas no
  arquivo ajustado: mix de cores por balao, carteira de pedidos, matrizes de setup (cor e forma) e
  lote minimo. Enquanto forem sinteticas, os custos absolutos do ajustado nao sao comparaveis ao
  realizado — so a estrutura da solucao e'.
- Confirmar com a operacao a regra de sequenciamento de cor assumida (clarear caro, escurecer
  barato, `PRETO -> BRANCO` so com limpeza completa do circuito; celula vazia da DE-PARA = limpeza completa, com o maior tempo registrado na matriz) e o calendario de paradas (preventivas, coletiva, carnaval),
  que hoje substitui a disponibilidade constante de 1,0 da extracao original.
- `CUSTO_UNITARIO` vem 10 R$/kg para todos os 17 balões na extracao original — e' um valor de
  preenchimento, nao um custo apurado. Sem custo real por balao o custo de carregamento nao
  diferencia produto.

## Modelo

- Avaliar setup de forma dependente da maquina (hoje `De_Para_Formas` e' independente de maquina;
  a diferenciacao por equipamento esta no custo horario de setup).
- Perecibilidade do latex: modelar (tanque, validade, recebimento diario) ou rebaixar a premissa
  simplificadora no `.tex`. Hoje esta declarada no Posicionamento e ausente do modelo.
- Realimentacao do turno para a semana dentro de uma mesma execucao (hoje so entre execucoes,
  em horizonte rolante).
- Provar o desenho de agregacao do semanal (por balao, sem cor), hoje afirmado como hipotese no `.tex`:
  - setup de forma domina o de cor: comparar `tau^F` e `tau^C` nas matrizes reais e as horas de
    setup de cada tipo na solucao;
  - previsao por balao erra menos que por SKU: MAPE e vies nos dois niveis sobre `T^v`;
  - semanal agregado + operacional contra semanal por SKU nas cinco instancias: custo, servico por
    classe (atraso, venda perdida, estoque minimo) e tempo de solucao.
- Demonstrar no capitulo de Resultados, com testes computacionais:
  - capacidade do armazem `Omega` de apertada a folgada: antecipacao de carteira, atraso, violacao do
    estoque minimo e horas de setup, nos dois niveis;
  - numero de semanas detalhadas `|T^O|`: producao das semanas alem da primeira quando as metas de
    estoque ja estao cobertas.

## Dissertacao

- Verificar em biblioteca os dados bibliograficos que a busca nao confirmou:
  Richardson (1995) volume/numero/paginas; Timme & Williams-Timme (2003) volume/paginas;
  Azzi et al. (2014) paginas; Stadtler & Fleischmann (2012) paginas do capitulo;
  edicao do Stock & Lambert que traz a regra dos 25%.
- Capitulo de Resultados: As-Is vs. Otimizado sobre o conjunto completo de instancias.
- Diferenciar no texto a terminologia de setup de forma (MODELO-TIPO) e de cor (MODELO-TIPO-COR).
