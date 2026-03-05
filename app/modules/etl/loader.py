import pandas as pd
import os
from app.config import Config
from typing import Dict, List, Tuple

# Constantes
PRODUCT_TYPES = ['PLATINO', 'NEON', 'PEROLA', 'METAL', 'CRISTAL', 'SALPICADO', 'LISO']
DEFAULT_TYPE = 'LISO'

def _read_sheet(sheet_name: str, header: int = 0) -> pd.DataFrame:
    """Lê uma aba do arquivo Excel centralizado de inputs."""
    file_path = Config.DATA_FILE
    if not os.path.exists(file_path):
        return pd.DataFrame()
    return pd.read_excel(file_path, sheet_name=sheet_name, header=header)

def _normalize_date_col(col_val) -> str:
    """
    Normaliza cabeçalhos de data para o formato interno 'YYYY-MM-DD HH:MM:SS'.
    Aceita formatos legíveis como 'MM/AAAA' (ex: '01/2024') ou timestamps completos.
    """
    s = str(col_val).strip()
    # Formato MM/AAAA (ex: "01/2024" ou "1/2024")
    import re
    match = re.fullmatch(r'(\d{1,2})/(\d{4})', s)
    if match:
        month, year = int(match.group(1)), int(match.group(2))
        return str(pd.Timestamp(year=year, month=month, day=1))
    # Tenta conversão genérica (timestamps, ISO, etc.)
    try:
        return str(pd.to_datetime(s))
    except Exception:
        return s

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
    # Linha 1 do Excel é título, linha 2 é o cabeçalho real (header=1)
    df = _read_sheet('Produtividade', header=1)
    if df.empty:
        return {}

    machine_map = {c: str(int(float(c))) for c in df.columns if c not in ['MODELO', 'TIPO'] and str(c).replace('.', '', 1).isdigit()}
    productivity = {}

    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')):
            continue

        key = parse_product_string(f"{row['MODELO']} {row.get('TIPO', '')}")
        productivity.setdefault(key, {})

        for col, m_id in machine_map.items():
            rate = row.get(col)
            if pd.notna(rate) and rate > 0:
                productivity[key][m_id] = float(rate)

    return productivity

def load_costs() -> Dict[Tuple[str, str], float]:
    """Carrega custos unitários."""
    # Aba Custos não tem linha de título — header direto na linha 1 (header=0)
    df = _read_sheet('Custos', header=0)
    costs = {}
    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')):
            continue
        key = parse_product_string(f"{row['MODELO']} {row.get('TIPO', '')}")
        try:
            costs[key] = float(str(row.get('CUSTO_UNITARIO', 0)).replace(',', '.'))
        except ValueError:
            continue
    return costs

def load_demand() -> Tuple[List[str], Dict]:
    """Carrega previsão de demanda e estende 12 meses com sazonalidade do ano anterior."""
    # Linha 1 do Excel é título, linha 2 é o cabeçalho real (header=1)
    df = _read_sheet('Demanda', header=1)
    if df.empty:
        return [], {}

    dates = [_normalize_date_col(c) for c in df.columns if str(c) != 'PRODUTO']
    demand = {}

    for _, row in df.iterrows():
        if pd.isna(row.get('PRODUTO')):
            continue
        key = parse_product_string(row['PRODUTO'])
        demand[key] = {d: float(v) for d, v in zip(dates, list(row)[1:]) if pd.notna(v)}

    dates = _extend_dates_with_seasonality(dates, demand)
    return dates, demand

def _extend_dates_with_seasonality(dates: List[str], demand: Dict, months_ahead: int = 12) -> List[str]:
    """Projeta datas futuras usando dados históricos (ano anterior)."""
    if not dates:
        return dates

    last_dt = pd.to_datetime(dates[-1])
    new_dates = dates[:]

    for i in range(months_ahead):
        future_dt = last_dt + pd.DateOffset(months=i + 1)
        future_str = str(future_dt)
        hist_dt = future_dt - pd.DateOffset(years=1)
        hist_str = hist_dt.strftime('%Y-%m')

        # Encontra data correspondente no histórico (match parcial de Y-m)
        hist_match = next((d for d in dates if pd.to_datetime(d).strftime('%Y-%m') == hist_str), None)

        for key, vals in demand.items():
            vals[future_str] = vals.get(hist_match, vals.get(new_dates[-(i + 1)], 0))

        new_dates.append(future_str)

    return new_dates

def load_inventory() -> Tuple[List[str], Dict]:
    """Carrega saldos de estoque."""
    # Linha 1 do Excel é título, linha 2 é o cabeçalho real (header=1)
    df = _read_sheet('Estoque', header=1)
    if df.empty:
        return [], {}

    dates = [_normalize_date_col(c) for c in df.columns if str(c) != 'PRODUTO']
    inventory = {}

    for _, row in df.iterrows():
        if pd.isna(row.get('PRODUTO')):
            continue
        key = parse_product_string(row['PRODUTO'])
        inventory[key] = {d: float(v) for d, v in zip(dates, list(row)[1:]) if pd.notna(v)}

    return dates, inventory
