import pandas as pd
import os
from app.config import Config

# Tipos de produtos conhecidos para normalização
PRODUCT_TYPES = ['PLATINO', 'NEON', 'PEROLA', 'METAL', 'CRISTAL']
DEFAULT_TYPE = 'LISO'

def normalize_product_key(raw_str: str) -> tuple[str, str]:
    """
    Normaliza a string crua do produto para extrair Modelo e Tipo.
    Ex: 'BALAO NEON 9' -> ('BALAO 9', 'NEON')
    """
    product_str = str(raw_str).upper().strip()
    
    found_type = DEFAULT_TYPE
    for t in PRODUCT_TYPES:
        if t in product_str:
            found_type = t
            product_str = product_str.replace(t, '').strip()
            break
    
    model = ' '.join(product_str.split())
    return model, found_type

def apply_specific_mappings(model: str, product_type: str) -> tuple[str, str]:
    """
    Aplica regras de negócio específicas para corrigir nomes de modelos legados ou inconsistentes.
    """
    model_mappings = {
        'CORACAO': 'COR',
        'GF 6.5': 'GF 65',
    }
    
    prefixes_to_strip = ['FESTA ']
    
    for prefix in prefixes_to_strip:
        if model.startswith(prefix):
            model = model[len(prefix):].strip()
    
    for old, new in model_mappings.items():
        model = model.replace(old, new)
    
    # Agrupamento por família
    family_prefixes = ['TOP', 'MAXI', 'FAT BALL']
    for prefix in family_prefixes:
        if model.startswith(prefix):
            model = prefix
            break
    
    return model, product_type

def parse_product_string(product_str: str) -> tuple[str, str]:
    """
    Pipeline completo de normalização de nome de produto.
    """
    model, product_type = normalize_product_key(product_str)
    return apply_specific_mappings(model, product_type)

def load_productivity() -> dict:
    """
    Carrega a matriz de produtividade (Taxa de produção por máquina).
    Retorna: dict -> {(Modelo, Tipo): {MachineID: Rate}}
    """
    file_path = Config.get_file_path('Matriz_Produtividade_Planilha1.csv')
    
    try:
        df = pd.read_csv(file_path, header=1)
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em {file_path}")
        return {}
    
    machine_map = {}
    for col in df.columns:
        if col not in ['MODELO', 'TIPO']:
            try:
                # Tenta identificar colunas numéricas como IDs de máquina
                m_id = str(int(float(col)))
                machine_map[col] = m_id
            except ValueError:
                pass
    
    productivity = {}
    
    for _, row in df.iterrows():
        if pd.isna(row['MODELO']):
            continue

        model = str(row['MODELO']).strip().upper()
        p_type = str(row['TIPO']).strip().upper()
        
        key = (model, p_type)
        if key not in productivity:
            productivity[key] = {}
        
        for col, m_id in machine_map.items():
            rate = row[col]
            if pd.notna(rate) and rate > 0:
                productivity[key][m_id] = float(rate)
    
    return productivity

def load_costs() -> dict:
    """
    Carrega a tabela de custos unitários dos produtos.
    Retorna: dict -> {(Modelo, Tipo): CustoFloat}
    """
    file_path = Config.get_file_path('Custos_Produtos.csv')
    costs = {}
    
    if not os.path.exists(file_path):
        return costs

    try:
        # Assume separador ';' para compatibilidade com Excel PT-BR
        df = pd.read_csv(file_path, sep=';')
        for _, row in df.iterrows():
            model = str(row['MODELO']).strip().upper()
            p_type = str(row['TIPO']).strip().upper()
            # Trata vírgula decimal
            cost = float(str(row['CUSTO_UNITARIO']).replace(',', '.'))
            
            key = (model, p_type)
            costs[key] = cost
    except Exception as e:
        print(f"Erro ao carregar custos: {e}")
        
    return costs

def load_demand() -> tuple[list, dict, dict]:
    """
    Carrega a previsão de demanda.
    Retorna: (Lista de Datas, Dict de Demanda, Dict de Nomes de Exibição)
    """
    file_path = Config.get_file_path('Prod_Fat_e_Saldos_Estoque_Previsto.csv')
    
    try:
        df = pd.read_csv(file_path, header=1)
    except FileNotFoundError:
        return [], {}, {}
    
    dates = [c for c in df.columns if c != 'PRODUTO']
    demand = {}
    display_names = {}
    
    for _, row in df.iterrows():
        raw_prod = row['PRODUTO']
        if pd.isna(raw_prod):
            continue
        
        model, p_type = parse_product_string(raw_prod)
        key = (model, p_type)
        display_names[key] = str(raw_prod).strip()
        
        if key not in demand:
            demand[key] = {}
        
        for date in dates:
            val = row[date]
            demand[key][date] = float(val) if pd.notna(val) else 0.0

    dates = _extend_dates_with_seasonality(dates, demand)
    
    return dates, demand, display_names

def _extend_dates_with_seasonality(dates: list, demand: dict, months_ahead: int = 12) -> list:
    """
    Projta datas futuras replicando a demanda do ano anterior (Sazonalidade) ou repetindo o último valor.
    Garante que o horizonte de planejamento seja longo o suficiente.
    """
    if not dates:
        return dates
    
    try:
        last_date_str = dates[-1]
        last_dt = pd.to_datetime(last_date_str)
        start_gen_dt = last_dt + pd.DateOffset(months=1)
        
        for i in range(months_ahead):
            future_dt = start_gen_dt + pd.DateOffset(months=i)
            future_date_str = str(future_dt)
            dates.append(future_date_str)
            
            # Busca data correspondente no ano anterior
            hist_dt = future_dt - pd.DateOffset(years=1)
            hist_key = hist_dt.strftime('%Y-%m')
            
            found_hist_date = None
            sample_key = next(iter(demand)) if demand else None
            
            if sample_key:
                for d_str in demand[sample_key]:
                    if pd.to_datetime(d_str).strftime('%Y-%m') == hist_key:
                        found_hist_date = d_str
                        break
            
            # Preenche demanda futura
            for key in demand:
                val = demand[key].get(found_hist_date, 0) if found_hist_date else demand[key].get(last_date_str, 0)
                demand[key][future_date_str] = float(val)
    except Exception as e:
        print(f"Aviso ao estender datas: {e}")
    
    return dates

def load_inventory() -> tuple[list, dict]:
    """
    Carrega saldos de estoque inicial.
    Retorna: (Lista de Datas, Dict de Inventário)
    """
    file_path = Config.get_file_path('Prod_Fat_e_Saldos_Estoque_Saldos_Estoque.csv')
    
    try:
        df = pd.read_csv(file_path, header=1)
    except FileNotFoundError:
        return [], {}
    
    dates = [c for c in df.columns if c != 'PRODUTO']
    inventory = {}
    
    for _, row in df.iterrows():
        raw_prod = row['PRODUTO']
        if pd.isna(raw_prod):
            continue
        
        model, p_type = parse_product_string(raw_prod)
        key = (model, p_type)
        
        if key not in inventory:
            inventory[key] = {}
        
        for date in dates:
            val = row[date]
            inventory[key][date] = float(val) if pd.notna(val) else 0.0
    
    return dates, inventory
