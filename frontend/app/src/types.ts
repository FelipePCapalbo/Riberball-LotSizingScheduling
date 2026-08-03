export interface Settings {
  start_period: string | null;
  end_period: string | null;
  coverage_months: number;
  shifts_per_day: number;
  hours_per_shift: number;
  days_per_week: number;
  active_machines: string[];
  high_setup_machines: string[];
  setup_time_high: number;
  setup_time_low: number;
  solver_name: string;
  time_limit: number;
  color_method: string;
  color_solver_name: string;
  color_time_limit: number;
}

export interface InitData {
  periods: string[];
  machines: string[];
}

export interface DataFiles {
  files: string[];
  active: string | null;
}

export interface Kpis {
  total_cost: number;
  service_level: number;
  avg_inventory: number;
  inventory_turnover: number;
}

export interface InventoryRow {
  Period: string;
  Product: string;
  Inventory: number;
}

export interface DemandRow {
  Period: string;
  Product: string;
  Demand: number;
  Met: number;
  Lost: number;
}

export interface ProductionRow {
  Period: string;
  Machine: string;
  Product: string;
  Kg: number;
  Hours: number;
}

export interface SetupRow {
  Period: string;
  Machine: string;
  Day: number;
  From: string;
  To: string;
  Cost: number;
}

export interface MachineStopRow {
  Period: string;
  Machine: string;
  DaysStopped: number;
  TotalDays: number;
}

export interface SummaryRow {
  Period: string;
  Inventory: number;
  Utilization: number;
  Demand: number;
  Lost: number;
  Production: number;
}

export interface RunResult {
  status: string;
  message?: string;
  inventory?: InventoryRow[];
  demand?: DemandRow[];
  production?: ProductionRow[];
  setups?: SetupRow[];
  machine_stops?: MachineStopRow[];
  summary?: SummaryRow[];
  kpis?: Kpis;
  run_id?: string;
  duration_seconds?: number;
  data_file?: string | null;
}

export interface ColorScheduleRow {
  machine: string;
  day: number;
  product: string;
  color: string;
  kg: number;
  hours: number;
}

export interface ColorSetupRow {
  machine: string;
  day: number;
  product: string;
  from_color: string;
  to_color: string;
  setup_time: number;
  cost: number;
}

export interface ColorOrderRow {
  sku: string;
  product: string;
  color: string;
  due_day: number;
  quantity: number;
  delayed_qty: number;
}

export interface ColorKpis {
  total_cost: number;
  delay_cost: number;
  setup_cost: number;
  service_level: number;
  total_setups: number;
}

export interface ColorRunResult {
  status: string;
  message?: string;
  method?: 'milp' | 'heuristic';
  color_schedule?: ColorScheduleRow[];
  color_setups?: ColorSetupRow[];
  orders?: ColorOrderRow[];
  kpis?: ColorKpis;
  run_id?: string | null;
  duration_seconds?: number;
  data_file?: string | null;
}

export interface HistoryRun {
  id: string;
  timestamp: string;
  label: string;
  duration_seconds: number;
  kpis: Kpis;
  color_kpis?: ColorKpis;
  color_duration_seconds?: number;
  color_method?: 'milp' | 'heuristic';
  start_period: string;
  end_period: string;
  solver_name: string;
  active_machines_count: number;
}

export interface HistoryRecord {
  id: string;
  timestamp: string;
  label: string;
  duration_seconds: number;
  data_file: string;
  inputs: Settings;
  kpis: Kpis;
  result: RunResult;
  color_kpis?: ColorKpis;
  color_duration_seconds?: number;
  color_result?: ColorRunResult;
}

export interface BackendStatus {
  connected: boolean;
  machine_label?: string;
  public_url?: string | null;
  since?: number;
  last_heartbeat_at?: number;
}
