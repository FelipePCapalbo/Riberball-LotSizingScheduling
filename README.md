# Sistema de Dimensionamento de Lotes

Sistema de otimização para planejamento de produção e estoques, focado em minimizar custos operacionais e maximizar o nível de serviço.

## Arquitetura e Estrutura

O sistema segue uma arquitetura modular simples, utilizando Flask para a interface web e API, e namespace packages para organização interna.

### Estrutura de Diretórios

- **app/**
  - `main.py`: Entrypoint da aplicação. Gerencia rotas da API e renderização do frontend.
  - **modules/etl/**: Tratamento de dados.
    - `loader.py`: Responsável por carregar CSVs e normalizar chaves de produto para garantir consistência entre Demanda e Produtividade.
  - **modules/optimization/**: Motor de cálculo.
    - `solver.py`: Implementação do modelo de otimização matemática (MILP) utilizando biblioteca PuLP.
  - **static/** e **templates/**: Interface do usuário.

- **data/**: Repositório de dados de entrada (CSV).
- **tests/**: Scripts de teste e benchmark de performance.
- `run_doe.py`: Script para execução de Design of Experiments (DOE) parametrizado.
- `doe_config.json`: Arquivo de configuração para os cenários do DOE.

## Componentes Principais

### ETL (`app/modules/etl`)
- **Normalização de Produtos**: Implementa lógica heurística para alinhar nomenclaturas divergentes entre fontes de dados.
- **Extensão de Demanda**: Replica a demanda histórica ou projeta baseada no último período para garantir horizonte de planejamento contínuo.

### Otimização (`app/modules/optimization`)
- **Solver (Mixed-Integer Linear Programming)**:
  - **Função Objetivo**: Minimizar custos de vendas perdidas (K) e setup de máquinas.
  - **Variáveis de Decisão**: 
    - Produção (Quantidade/Horas).
    - Estado da Máquina (Setup, Produzindo, Ociosa).
    - Estoque.
  - **Restrições**: 
    - Capacidade de máquina (Horas produtivas + Setup).
    - Balanço de massa de estoque e fluxo de atendimento.
    - Estoque de segurança mínimo.
    - **Lógica de Setup e Ociosidade**: O modelo gerencia explicitamente o estado da máquina, permitindo "carry-over" (manter setup) ou ociosidade forçada, evitando setups desnecessários.

### Interface e Relatórios
- **Parametrização Centralizada**: As configurações de Período, Cobertura de Estoque e Recursos Operacionais (Férias) estão organizadas na linha superior para acesso rápido.
- **Layout Flexível**: O painel de Configurações Gerais e o Painel de Máquinas possuem uma barra divisória ajustável, permitindo que o usuário personalize a largura de cada área conforme sua necessidade de visualização.
- **Resumo Mensal**: KPIs agregados de estoque, utilização e atendimento.
- **Produção Detalhada**: Tabela granular de horas e quantidades produzidas por máquina/produto.
- **Relatório de Setups**: Visualização detalhada de todas as trocas (setups) ocorridas.

### Automação de Experimentos (DOE)
O sistema permite rodar baterias de testes combinatórios para análise de sensibilidade e tuning de parâmetros.
- **Configuração (`doe_config.json`)**: Define variáveis fixas e listas de valores para variáveis experimentais (Ex: número de operadores, tipo de decisão, cobertura).
- **Execução (`run_doe.py`)**: Gera todas as combinações possíveis, executa o solver para cada cenário e exporta um CSV (`doe_results.csv`) contendo:
  - KPIs (Custo Total, Nível de Serviço, Estoque Médio).
  - Métricas de Solver (Lower Bound, Tempo de Execução, Status).

## Performance e Limitações

A complexidade computacional do problema é dominada pela combinação de variáveis inteiras (`H_steps`) e binárias (`Y`), ligadas por restrições de "Big-M" (`H <= M * Y`).

- **Setup de Máquina**: Utiliza variáveis binárias (`Y`, `Delta`) para impor custo/tempo de setup e rastrear mudanças de estado.
- **Otimização "Tight Big-M"**: O valor de `M` é calculado dinamicamente com base na demanda restante para fortalecer o relaxamento linear e acelerar a convergência.

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

### Executando o DOE
Para rodar os experimentos configurados em `doe_config.json`:
```bash
python run_doe.py
```
Os resultados serão salvos em `doe_results.csv`.
