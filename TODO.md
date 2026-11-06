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

- Feito: `scripts/input_adjuster.py` converte `data/brutos/input_asis.xlsx` para `data/input_asis_ajustado.xlsx`
  no contrato semanal.
- Levantar em campo as quatro dimensoes que a operacao nao registra e que hoje sao sinteticas no
  arquivo ajustado: mix de cores por balao, carteira de pedidos, matrizes de setup (cor e forma) e
  lote minimo. Enquanto forem sinteticas, os custos absolutos do ajustado nao sao comparaveis ao
  realizado — so a estrutura da solucao e'.
- Confirmar com a operacao a regra de sequenciamento de cor assumida (clarear caro, escurecer
  barato, `PRETO -> BRANCO` proibido) e o calendario de paradas (preventivas, coletiva, carnaval),
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

## Dissertacao

- Verificar em biblioteca os dados bibliograficos que a busca nao confirmou:
  Richardson (1995) volume/numero/paginas; Timme & Williams-Timme (2003) volume/paginas;
  Azzi et al. (2014) paginas; Stadtler & Fleischmann (2012) paginas do capitulo;
  edicao do Stock & Lambert que traz a regra dos 25%.
- Capitulo de Resultados: As-Is vs. Otimizado sobre o conjunto completo de instancias.
- Diferenciar no texto a terminologia de setup de forma (MODELO-TIPO) e de cor (MODELO-TIPO-COR).
