# Pendencias

## Tratabilidade do modelo por turno (prioridade)

Modelo resolvido como formulado, sem heuristica de resolucao. CBC, 3 posicoes/turno,
1 semana congelada (18 turnos), limite de 900 s no diario:

| Instancia | Binarias | Status | Tempo | Limite atingido |
|---|---|---|---|---|
| micro (P2 M3)    |    540 | Optimal    |  65 s | nao — otimo comprovado |
| pequeno (P4 M6)  |  1.944 | Optimal    | 900 s | sim — melhor encontrada |
| medio (P8 M12)   |  8.262 | Optimal    | 902 s | sim — melhor encontrada |
| grande (P12 M20) | 14.850 | Not Solved | 924 s | — |
| real (P17 M28)   | 28.728 | Not Solved | 145 s | — |

A partir de `grande` o CBC nao encontra solucao inteira dentro do limite. O caminho e' de
**formulacao**, nao de heuristica de resolucao:

- apertar os limitantes big-M da restricao de lote minimo por turno (hoje `p_ij * b_js`);
- buscar desigualdades validas para a estrutura de posicoes contiguas;
- avaliar se `positions_per_shift = 2` preserva as solucoes relevantes;
- testar Gurobi, que trata modelos deste porte melhor que o CBC.

Reportar no capitulo de Resultados o status e o gap de cada instancia, nao apenas o custo.

## Dados

- Converter `data/OLD_MENSAL/input_asis.xlsx` (dado real, mensal) para o contrato semanal:
  desagregar a demanda mensal por dias uteis da semana e montar as abas de carteira.

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
