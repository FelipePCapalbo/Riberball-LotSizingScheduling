export interface Settings {
  start_week: string | null;
  weeks_in_plan: number;
  frozen_weeks: number;
  coverage_weeks: number;
  shifts_per_day: number;
  hours_per_shift: number;
  working_days_per_week: number;
  active_machines: string[];
  setup_hourly_cost_default: number;
  setup_hourly_cost_by_machine: Record<string, number>;
  annual_holding_rate: number;
  order_backlog_multiplier: number;
  coverage_weight: number;
  weekly_solver_name: string;
  weekly_time_limit: number;
  daily_solver_name: string;
  daily_time_limit: number;
  positions_per_shift: number;
  threads: number | null;
}

export interface InitData {
  weeks: string[];
  machines: string[];
  products: string[];
  orders: number;
}

export interface DataFiles {
  files: string[];
  active: string | null;
}

export interface WeeklyKpis {
  total_cost: number;
  solver_objective: number;
  backlog_cost: number;
  lost_sales_cost: number;
  coverage_cost: number;
  setup_cost: number;
  holding_cost: number;
  order_service_level: number;
  forecast_service_level: number;
  avg_inventory: number;
  inventory_turnover: number;
  setup_hours: number;
  solve_seconds: number;
  hit_time_limit: boolean;
}

export interface WeeklyProductionRow {
  week: string;
  machine: string;
  product: string;
  kg: number;
  hours: number;
  setup_hours: number;
}

export interface WeeklyInventoryRow {
  week: string;
  product: string;
  inventory: number;
  target: number;
  slack: number;
}

export interface WeeklyDemandRow {
  week: string;
  product: string;
  orders: number;
  forecast: number;
  delivered_orders: number;
  backlog: number;
  delivered_forecast: number;
  lost: number;
}

export interface WeeklyResult {
  status: string;
  message?: string;
  weeks?: string[];
  production?: WeeklyProductionRow[];
  inventory?: WeeklyInventoryRow[];
  demand?: WeeklyDemandRow[];
  targets?: Record<string, Record<string, number>>;
  kpis?: WeeklyKpis;
  run_id?: string;
  duration_seconds?: number;
  data_file?: string | null;
}

export interface DailyKpis {
  total_cost: number;
  backlog_cost: number;
  lost_sales_cost: number;
  coverage_cost: number;
  setup_cost: number;
  holding_cost: number;
  order_service_level: number;
  forecast_service_level: number;
  form_setup_hours: number;
  color_setup_hours: number;
  total_setups: number;
  solve_seconds: number;
  hit_time_limit: boolean;
  max_fractional_deviation: number;
}

export interface ScheduleRow {
  date: string;
  shift: number;
  shift_index: number;
  machine: string;
  position: number;
  product: string;
  color: string;
  sku: string;
  kg: number;
  production_hours: number;
  form_setup_hours: number;
  color_setup_hours: number;
  previous_form: string;
  previous_color: string;
}

export interface DailyOrderRow {
  sku: string;
  product: string;
  color: string;
  shift_index: number;
  date: string;
  shift: number;
  orders: number;
  forecast: number;
  delivered_orders: number;
  delivered_forecast: number;
  backlog: number;
  lost: number;
  inventory: number;
}

export interface DailyTargetRow {
  product: string;
  target: number;
  final_stock: number;
  slack: number;
}

export interface DailyResult {
  status: string;
  message?: string;
  schedule?: ScheduleRow[];
  orders?: DailyOrderRow[];
  targets?: DailyTargetRow[];
  shifts?: number;
  kpis?: DailyKpis;
  run_id?: string | null;
  duration_seconds?: number;
  data_file?: string | null;
}

export interface HistoryRun {
  id: string;
  timestamp: string;
  label: string;
  data_file: string;
  start_week: string;
  weeks_in_plan: number;
  machines: number;
  weekly_kpis: WeeklyKpis;
  weekly_duration: number;
  daily_kpis: DailyKpis | null;
  daily_duration: number | null;
}

export interface HistoryRecord {
  id: string;
  timestamp: string;
  label: string;
  data_file: string;
  inputs: Settings;
  weekly: {
    status: string;
    duration_seconds: number;
    kpis: WeeklyKpis;
    weeks: string[];
    production: WeeklyProductionRow[];
    inventory: WeeklyInventoryRow[];
    demand: WeeklyDemandRow[];
    targets: Record<string, Record<string, number>>;
  };
  daily: {
    status: string;
    duration_seconds: number;
    kpis: DailyKpis;
    shifts: number;
    schedule: ScheduleRow[];
    orders: DailyOrderRow[];
    targets: DailyTargetRow[];
  } | null;
}

export interface BackendStatus {
  connected: boolean;
  machine_label?: string;
}
