# Sistema de Dimensionamento de Lotes

Sistema de otimização para planejamento de produção e estoques, focado em minimizar custos operacionais e maximizar o nível de serviço.

## Arquitetura e Estrutura

O sistema segue uma arquitetura modular simples, utilizando Flask para a interface web e API, e namespace packages para organização interna.

### Estrutura de Diretórios

- **app/**
  - `main.py`: Entrypoint da aplicação. Gerencia rotas da API e renderização do frontend.
  - **modules/etl/**: Tratamento de dados.
    - `loader.py`: Responsável por carregar CSVs e normalizar chaves de produto (Modelos/Tipos) para garantir consistência entre Demanda e Produtividade.
  - **modules/optimization/**: Motor de cálculo.
    - `solver.py`: Implementação do modelo de otimização matemática (MILP) utilizando biblioteca PuLP.
  - **static/** e **templates/**: Interface do usuário.

- **data/**: Repositório de dados de entrada (CSV).
- **tests/**: Scripts de teste e benchmark de performance.

## Componentes Principais

### ETL (`app/modules/etl`)
- **Normalização de Produtos**: Implementa lógica heurística para alinhar nomenclaturas divergentes entre fontes de dados (ex: remove prefixos "FESTA", mapeia "GF 6.5" para "GF 65"). Isso elimina "produção fantasma" ou ociosidade indevida causada por falhas de correspondência.
- **Extensão de Demanda**: Replica a demanda histórica ou projeta baseada no último período para garantir horizonte de planejamento contínuo.

### Otimização (`app/modules/optimization`)
- **Solver (Mixed-Integer Linear Programming)**:
  - **Função Objetivo**: Minimizar custos de vendas perdidas (K), backlog (B), violação de cobertura (V) e penalidades de nível de serviço.
  - **Variáveis de Decisão**: Quantidade a produzir (blocos de 6h inteiros), Nível de Estoque, Backlog, Setup de Máquina (variável binária).
  - **Restrições**: 
    - Capacidade de máquina (Horas produtivas + Setup).
    - Balanço de massa de estoque e fluxo de atendimento.
    - Cobertura de estoque mínima (Target Turnover).
    - Janelas de tempo para Backlog.
    - **Detecção de Setup Aprimorada**: Considera setup tanto para mudança de estado final da máquina quanto para qualquer produção iniciada que não corresponda ao estado anterior ("Carry-over").

### Interface e Relatórios
- **Resumo Mensal**: KPIs agregados de estoque, utilização e atendimento. O cálculo de utilização considera estritamente o tempo de setup incorrido (variável binária de decisão) somado às horas de produção, garantindo consistência com as restrições de capacidade do modelo.
- **Produção Detalhada**: Tabela granular de horas e quantidades produzidas por máquina/produto.
- **Relatório de Setups**: Visualização detalhada de todas as trocas (setups) ocorridas, indicando o produto de origem (estado anterior da máquina) e o produto destino, permitindo análise fina de perdas por troca.
- **Favicon**: Implementado via Data URI (base64) diretamente no HTML para evitar requisições 404 desnecessárias e manter a estrutura de arquivos limpa.

## Performance e Limitações

A complexidade computacional do problema é dominada pela combinação de variáveis inteiras (`H_steps`) e binárias (`Y`), ligadas por restrições de "Big-M" (`H <= M * Y`).

- **Setup de Máquina**: Utiliza variáveis binárias (`Y`) para impor custo/tempo de setup sempre que uma máquina é utilizada.
- **Produção Discreta**: A produção é restrita a múltiplos de 6 horas (blocos inteiros).
- **Otimização "Tight Big-M"**:
  - Para melhorar a performance sem sacrificar a restrição de blocos de 6h, foi implementada uma lógica de limites variáveis ("Tight Big-M").
  - O valor de `M` para cada variável de decisão é calculado dinamicamente como `min(Capacidade, Demanda Restante)`.
  - Isso fortalece o relaxamento linear do problema, reduzindo o espaço de busca do solver e melhorando significativamente o tempo de convergência (redução de ~50% no tempo de resolução em benchmarks).

## Como Executar

### Pré-requisitos
- Python 3.10+
- Dependências listadas em `requirements.txt`

### Comandos
Linux/Mac:
```bash
./run.sh
```
Windows:
```cmd
run.bat
```
Acesse: http://127.0.0.1:5000
