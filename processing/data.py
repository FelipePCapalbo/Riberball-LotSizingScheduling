"""
Processamento de dados: leitura do Excel de inputs, montagem do cenário para o
solver e transformação de intervalos de parada em índices de dias.

SKUs são identificados no formato MODELO-TIPO em todas as abas.
  - Produtividade e Custos: colunas separadas MODELO e TIPO, chave = "MODELO-TIPO"
  - Demanda e Estoque: coluna PRODUTO já no formato "MODELO-TIPO"
"""
import os
import re
from typing import Dict, List, Optional, Tuple
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(ROOT_DIR, 'data')


# ── Leitura do Excel ───────────────────────────────────────────────────────

def list_data_files() -> list:
    """Retorna os arquivos .xlsx disponíveis em data/."""
    return sorted(
        f for f in os.listdir(DATA_DIR)
        if f.endswith('.xlsx') and not f.startswith('~')
    )


def _read_sheet(data_file: str, sheet_name: str, header: int = 0) -> pd.DataFrame:
    """Lê uma aba do arquivo Excel indicado."""
    if not os.path.exists(data_file):
        return pd.DataFrame()
    return pd.read_excel(data_file, sheet_name=sheet_name, header=header)


def _normalize_date_col(col_val) -> str:
    """Normaliza cabeçalhos de data para 'YYYY-MM-DD HH:MM:SS'. Aceita 'MM/AAAA'."""
    s = str(col_val).strip()
    match = re.fullmatch(r'(\d{1,2})/(\d{4})', s)
    if match:
        month, year = int(match.group(1)), int(match.group(2))
        return str(pd.Timestamp(year=year, month=month, day=1))
    try:
        return str(pd.to_datetime(s))
    except Exception:
        return s


def load_productivity(data_file: str) -> Dict[str, Dict[str, float]]:
    """Carrega matriz de produtividade. Chave: 'MODELO-TIPO'."""
    df = _read_sheet(data_file, 'Produtividade', header=1)
    if df.empty:
        return {}

    machine_map = {c: str(int(float(c))) for c in df.columns
                   if c not in ['MODELO', 'TIPO'] and str(c).replace('.', '', 1).isdigit()}
    productivity = {}

    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')):
            continue
        sku = f"{row['MODELO']}-{row['TIPO']}"
        productivity.setdefault(sku, {})
        for col, m_id in machine_map.items():
            rate = row.get(col)
            if pd.notna(rate) and rate > 0:
                productivity[sku][m_id] = float(rate)

    return productivity


def load_costs(data_file: str) -> Dict[str, float]:
    """Carrega custos unitários. Chave: 'MODELO-TIPO'."""
    df = _read_sheet(data_file, 'Custos', header=0)
    costs = {}
    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')):
            continue
        sku = f"{row['MODELO']}-{row['TIPO']}"
        try:
            costs[sku] = float(str(row.get('CUSTO_UNITARIO', 0)).replace(',', '.'))
        except ValueError:
            continue
    return costs


def load_demand(data_file: str) -> Tuple[List[str], Dict]:
    """Carrega previsão de demanda e estende 12 meses com sazonalidade do ano anterior."""
    df = _read_sheet(data_file, 'Demanda', header=1)
    if df.empty:
        return [], {}

    dates = [_normalize_date_col(c) for c in df.columns if c not in ('MODELO', 'TIPO')]
    demand = {}
    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')):
            continue
        sku = f"{row['MODELO']}-{row['TIPO']}"
        demand[sku] = {d: float(v) for d, v in zip(dates, list(row)[2:]) if pd.notna(v)}

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
        hist_str = (future_dt - pd.DateOffset(years=1)).strftime('%Y-%m')
        hist_match = next((d for d in dates if pd.to_datetime(d).strftime('%Y-%m') == hist_str), None)
        for key, vals in demand.items():
            vals[future_str] = vals.get(hist_match, vals.get(new_dates[-(i + 1)], 0))
        new_dates.append(future_str)

    return new_dates


def load_inventory(data_file: str) -> Tuple[List[str], Dict]:
    """Carrega saldos de estoque. Chave: 'MODELO-TIPO'."""
    df = _read_sheet(data_file, 'Estoque', header=1)
    if df.empty:
        return [], {}

    dates = [_normalize_date_col(c) for c in df.columns if c not in ('MODELO', 'TIPO')]
    inventory = {}
    for _, row in df.iterrows():
        if pd.isna(row.get('MODELO')):
            continue
        sku = f"{row['MODELO']}-{row['TIPO']}"
        inventory[sku] = {d: float(v) for d, v in zip(dates, list(row)[2:]) if pd.notna(v)}

    return dates, inventory


def load_machine_availability(data_file: str) -> Dict[str, Dict[str, float]]:
    """
    Carrega disponibilidade mensal das máquinas.
    Retorna avail[machine_id][period_str] = fração em [0, 1].
    Período sem registro assume disponibilidade plena (1.0).
    """
    df = _read_sheet(data_file, 'Disponibilidade de maquinas', header=0)
    if df.empty:
        return {}

    machine_cols = [c for c in df.columns if c != 'DATA']
    avail: Dict[str, Dict[str, float]] = {}

    for col in machine_cols:
        m_id = str(int(float(col))) if str(col).replace('.', '', 1).isdigit() else str(col)
        avail[m_id] = {}
        for _, row in df.iterrows():
            if pd.isna(row.get('DATA')):
                continue
            period = _normalize_date_col(row['DATA'])
            val = row.get(col)
            avail[m_id][period] = float(val) if pd.notna(val) else 1.0

    return avail


# ── Montagem do cenário ─────────────────────────────────────────────────────

class DataService:
    """Carrega os dados do Excel e prepara cenários para o solver."""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self._load_all_data()

    def _load_all_data(self):
        self.productivity = load_productivity(self.data_file)
        self.demand_dates, self.demand = load_demand(self.data_file)
        _, self.inventory = load_inventory(self.data_file)
        self.costs = load_costs(self.data_file)
        self.machine_availability = load_machine_availability(self.data_file)

    def get_initial_data(self) -> Dict:
        """Períodos disponíveis e lista de máquinas para a interface."""
        machines = {m for p_map in self.productivity.values() for m in p_map.keys()}
        return {
            "periods": self.demand_dates,
            "machines": sorted(list(machines), key=lambda x: int(x) if x.isdigit() else 999)
        }

    def get_scenario_data(self, start_period: str, end_period: Optional[str] = None) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
        """Prepara demanda, estoque inicial, produtividade e custos para o solver."""
        if not self.demand:
            return {}, {}, {}, {}, {}

        local_demand = {k: v.copy() for k, v in self.demand.items()}

        # Estende datas se end_period ultrapassar o horizonte já carregado
        last_loaded = self.demand_dates[-1] if self.demand_dates else None
        if end_period and last_loaded and end_period > last_loaded:
            curr_dt = pd.to_datetime(last_loaded)
            target_dt = pd.to_datetime(end_period)
            while curr_dt < target_dt:
                curr_dt += pd.DateOffset(months=1)
                new_str = str(curr_dt)
                for vals in local_demand.values():
                    vals.setdefault(new_str, vals.get(last_loaded, 0))

        # Estoque inicial: último saldo disponível antes ou igual ao start_period
        initial_inventory = {}
        for sku, date_vals in self.inventory.items():
            valid_dates = [d for d in date_vals if d <= start_period]
            initial_inventory[sku] = date_vals[max(valid_dates)] if valid_dates else 0.0

        return local_demand, initial_inventory, self.productivity, self.costs, self.machine_availability


