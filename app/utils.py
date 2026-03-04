def calculate_hours_per_period(capacity_params: dict) -> float:
    """
    Calcula o total de horas disponíveis por máquina no período (mês médio).
    Fórmula: Turnos * Horas * Dias * 4.33 (semanas/mês)
    """
    if not capacity_params:
        return 720.0
        
    shifts = float(capacity_params.get('shifts_per_day', 3))
    hours_shift = float(capacity_params.get('hours_per_shift', 8))
    days_week = float(capacity_params.get('days_per_week', 7))
    
    return shifts * hours_shift * days_week * 4.33

def calculate_step_size(decision_type: str, bucket_hours: float, capacity_params: dict) -> tuple[float, bool]:
    """
    Define a granularidade da variável de decisão (tamanho do passo H) e se é inteira.
    """
    hours_shift = float(capacity_params.get('hours_per_shift', 8))
    
    decision_type = decision_type.lower()
    
    if decision_type == 'kg':
        return 1.0, False
    elif decision_type == 'hours':
        return float(bucket_hours), True
    elif decision_type == 'shifts':
        return hours_shift, True
    elif decision_type == 'days':
        shifts = float(capacity_params.get('shifts_per_day', 3))
        return hours_shift * shifts, True
    elif decision_type == 'weeks':
        shifts = float(capacity_params.get('shifts_per_day', 3))
        days_week = float(capacity_params.get('days_per_week', 7))
        return hours_shift * shifts * days_week, True
    
    return 1.0, True

def sanitize_name(name) -> str:
    """Helper to sanitize names for LP/Solver compatibility."""
    return str(name).replace(' ', '_').replace(':', '_').replace('-', '_')

