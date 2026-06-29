"""
Processamento de dados: leitura do Excel de inputs, montagem do cenário para o
solver e transformação de intervalos de parada em índices de dias.

SKUs são identificados no formato MODELO-TIPO em todas as abas.
  - Produtividade e Custos: colunas separadas MODELO e TIPO, chave = "MODELO-TIPO"
  - Demanda e Estoque: coluna PRODUTO já no formato "MODELO-TIPO"
"""
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT_DIR, 'data', 'inputs.xlsx')


# ── Leitura do Excel ───────────────────────────────────────────────────────

def _read_sheet(sheet_name: str, header: int = 0) -> pd.DataFrame:
    """Lê uma aba do arquivo Excel centralizado de inputs."""
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    return pd.read_excel(DATA_FILE, sheet_name=sheet_name, header=header)


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


def load_productivity() -> Dict[str, Dict[str, float]]:
    """Carrega matriz de produtividade. Chave: 'MODELO-TIPO'."""
    df = _read_sheet('Produtividade', header=1)
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


def load_costs() -> Dict[str, float]:
    """Carrega custos unitários. Chave: 'MODELO-TIPO'."""
    df = _read_sheet('Custos', header=0)
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


def load_demand() -> Tuple[List[str], Dict]:
    """Carrega previsão de demanda e estende 12 meses com sazonalidade do ano anterior."""
    df = _read_sheet('Demanda', header=1)
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


def load_inventory() -> Tuple[List[str], Dict]:
    """Carrega saldos de estoque. Chave: 'MODELO-TIPO'."""
    df = _read_sheet('Estoque', header=1)
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


# ── Montagem do cenário ─────────────────────────────────────────────────────

class DataService:
    """Carrega os dados do Excel uma única vez e prepara cenários para o solver."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all_data()
        return cls._instance

    def _load_all_data(self):
        self.productivity = load_productivity()
        self.demand_dates, self.demand = load_demand()
        _, self.inventory = load_inventory()
        self.costs = load_costs()

    def get_initial_data(self) -> Dict:
        """Períodos disponíveis e lista de máquinas para a interface."""
        machines = {m for p_map in self.productivity.values() for m in p_map.keys()}
        return {
            "periods": self.demand_dates,
            "machines": sorted(list(machines), key=lambda x: int(x) if x.isdigit() else 999)
        }

    def get_scenario_data(self, start_period: str, end_period: Optional[str] = None) -> Tuple[Dict, Dict, Dict, Dict]:
        """Prepara demanda, estoque inicial, produtividade e custos para o solver."""
        if not self.demand:
            return {}, {}, {}, {}

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

        return local_demand, initial_inventory, self.productivity, self.costs


# ── Transformações para o solver ────────────────────────────────────────────

def ranges_to_day_indices(ranges_by_machine, periods, days_per_period) -> set:
    """
    Converte intervalos de datas {machine: [{start, end}, ...]} em set de
    (machine, day_index) compatível com o solver.

    Cada período (mês) tem n_t dias úteis indexados sequencialmente. Uma data
    calendário dentro do mês é mapeada ao dia útil proporcional.
    """
    stop_set = set()
    if not ranges_by_machine or not periods:
        return stop_set

    period_info = []
    cum_day = 0
    for t in periods:
        date_str = t.split(' ')[0]
        year, month = int(date_str[:4]), int(date_str[5:7])
        next_month_start = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        month_start = datetime(year, month, 1)
        cal_days = (next_month_start - month_start).days
        n_t = days_per_period.get(t, 30)
        period_info.append({'month_start': month_start, 'cal_days': cal_days, 'n_t': n_t, 'cum_day': cum_day})
        cum_day += n_t

    for machine, ranges in ranges_by_machine.items():
        for rng in ranges or []:
            try:
                r_start = datetime.strptime(rng['start'], '%Y-%m-%d')
                r_end = datetime.strptime(rng['end'], '%Y-%m-%d')
            except (ValueError, KeyError):
                continue
            if r_end < r_start:
                r_start, r_end = r_end, r_start

            for pi in period_info:
                ms = pi['month_start']
                me = ms + timedelta(days=pi['cal_days'] - 1)
                overlap_start = max(r_start, ms)
                overlap_end = min(r_end, me)
                if overlap_start > overlap_end:
                    continue
                for day_offset in range((overlap_end - overlap_start).days + 1):
                    cal_date = overlap_start + timedelta(days=day_offset)
                    day_in_month = (cal_date - ms).days
                    working_day = min(int(day_in_month * pi['n_t'] / pi['cal_days']), pi['n_t'] - 1)
                    stop_set.add((machine, pi['cum_day'] + working_day))

    return stop_set
