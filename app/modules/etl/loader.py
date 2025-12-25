import pandas as pd
import os
from app.config import Config
from typing import Dict, List, Tuple

# Constantes
PRODUCT_TYPES = ['PLATINO', 'NEON', 'PEROLA', 'METAL', 'CRISTAL', 'SALPICADO', 'LISO']
DEFAULT_TYPE = 'LISO'

def _read_csv(filename: str, **kwargs) -> pd.DataFrame:
    """Helper genérico para leitura de CSV."""
    file_path = Config.get_file_path(filename)
    if not os.path.exists(file_path):
        return pd.DataFrame()
    return pd.read_csv(file_path, **kwargs)

def parse_product_string(raw_str: str) -> Tuple[str, str]:
    """Extrai Modelo e Tipo e aplica correções."""
    s = str(raw_str).upper().strip()
    found_type = DEFAULT_TYPE
    
    for t in PRODUCT_TYPES:
        if t in s:
            found_type = t
            s = s.replace(t, '').strip()
            break
            
    # Mapeamentos específicos
    s = s.replace('CORACAO', 'COR').replace('GF 6.5', 'GF 65')
    for prefix in ['FESTA ', 'TOP', 'MAXI', 'FAT BALL']:
        if s.startswith(prefix):
            s = prefix.strip() if prefix in ['TOP', 'MAXI', 'FAT BALL'] else s.replace(prefix, '')
            break
            
    return ' '.join(s.split()), found_type

def load_productivity() -> Dict[Tuple[str, str], Dict[str, float]]:
    """Carrega matriz de produtividade."""
    df = _read_csv('Matriz_Produtividade_Planilha1.csv', header=1)
    if df.empty: return {}

    machine_map = {c: str(int(float(c))) for c in df.columns if c not in ['MODELO', 'TIPO'] and c.replace('.','',1).isdigit()}
    productivity = {}

    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')): continue
        
        key = parse_product_string(f"{row['MODELO']} {row.get('TIPO', '')}")
        productivity.setdefault(key, {})
        
        for col, m_id in machine_map.items():
            rate = row.get(col)
            if pd.notna(rate) and rate > 0:
                productivity[key][m_id] = float(rate)
                
    return productivity

def load_costs() -> Dict[Tuple[str, str], float]:
    """Carrega custos unitários."""
    df = _read_csv('Custos_Produtos.csv', sep=';')
    costs = {}
    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')): continue
        key = parse_product_string(f"{row['MODELO']} {row.get('TIPO', '')}")
        try:
            costs[key] = float(str(row.get('CUSTO_UNITARIO', 0)).replace(',', '.'))
        except ValueError:
            continue
    return costs

def load_demand() -> Tuple[List[str], Dict, Dict]:
    """Carrega previsão de demanda."""
    df = _read_csv('Prod_Fat_e_Saldos_Estoque_Previsto.csv', header=1)
    if df.empty: return [], {}, {}
    
    dates = [c for c in df.columns if c != 'PRODUTO']
    demand = {}
    display_names = {}
    
    for _, row in df.iterrows():
        if pd.isna(row.get('PRODUTO')): continue
        key = parse_product_string(row['PRODUTO'])
        display_names[key] = str(row['PRODUTO']).strip()
        demand[key] = {d: float(row.get(d, 0)) for d in dates if pd.notna(row.get(d))}
            
    dates = _extend_dates_with_seasonality(dates, demand)
    return dates, demand, display_names

def _extend_dates_with_seasonality(dates: List[str], demand: Dict, months_ahead: int = 12) -> List[str]:
    """Projeta datas futuras usando dados históricos (ano anterior)."""
    if not dates: return dates
    
    last_dt = pd.to_datetime(dates[-1])
    new_dates = dates[:]
    
    for i in range(months_ahead):
        future_dt = last_dt + pd.DateOffset(months=i+1)
        future_str = str(future_dt)
        hist_dt = future_dt - pd.DateOffset(years=1)
        hist_str = hist_dt.strftime('%Y-%m')
        
        # Encontra data correspondente no histórico (match parcial de Y-m)
        hist_match = next((d for d in dates if pd.to_datetime(d).strftime('%Y-%m') == hist_str), None)
        
        for key, vals in demand.items():
            vals[future_str] = vals.get(hist_match, vals.get(new_dates[-(i+1)], 0))
            
        new_dates.append(future_str)
        
    return new_dates

def load_inventory() -> Tuple[List[str], Dict]:
    """Carrega saldos de estoque."""
    df = _read_csv('Prod_Fat_e_Saldos_Estoque_Saldos_Estoque.csv', header=1)
    if df.empty: return [], {}
    
    dates = [c for c in df.columns if c != 'PRODUTO']
    inventory = {}
    
    for _, row in df.iterrows():
        if pd.isna(row.get('PRODUTO')): continue
        key = parse_product_string(row['PRODUTO'])
        inventory[key] = {d: float(row.get(d, 0)) for d in dates if pd.notna(row.get(d))}
            
    return dates, inventory
