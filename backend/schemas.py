from typing import List, Optional

from pydantic import BaseModel


class SettingsPayload(BaseModel):
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    coverage_months: Optional[int] = None
    shifts_per_day: Optional[float] = None
    hours_per_shift: Optional[float] = None
    days_per_week: Optional[float] = None
    active_machines: Optional[List[str]] = None
    high_setup_machines: Optional[List[str]] = None
    setup_time_high: Optional[float] = None
    setup_time_low: Optional[float] = None
    solver_name: Optional[str] = None
    time_limit: Optional[int] = None
    color_method: Optional[str] = None
    color_solver_name: Optional[str] = None
    color_time_limit: Optional[int] = None


class RunRequest(BaseModel):
    settings: SettingsPayload
    label: str = ""


class ColorRunRequest(BaseModel):
    color_method: Optional[str] = None


class DataFileRequest(BaseModel):
    file: str
