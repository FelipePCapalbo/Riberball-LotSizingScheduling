export interface Settings {
  start_week: string | null;
  weeks_in_plan: number;
  frozen_weeks: number;
  shifts_per_day: number;
  hours_per_shift: number;
  working_days_per_week: number;
  warehouse_capacity_kg: number | null;
  annual_holding_rate: number;
  weekly_solver_name: string;
  weekly_time_limit: number;
  daily_solver_name: string;
  daily_time_limit: number;
  threads: number | null;
}

export interface InitData {
  weeks: string[];
  machines: string[];
  active_machines: string[];
  products: string[];
  orders: number;
  source: string | null;
  snapshot_id: number | null;
}

export interface SnapshotRow {
  snapshot_id: number;
  created_at: string;
  source_file: string;
  sheets: string[];
}

export interface Snapshots {
  snapshots: SnapshotRow[];
  active: number | null;
}

export type ChangeType = 'update' | 'delete';
export type ChangeDecision = 'pending' | 'approved' | 'rejected';

export interface MasterConflict {
  change_id: number;
  table_name: string;
  record_key: Record<string, string>;
  change_type: ChangeType;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  decision: ChangeDecision;
}

export interface UploadReview {
  upload_id: number;
  created_at: string;
  source_file: string;
  status: 'pending' | 'applied' | 'discarded';
  snapshot_id: number | null;
  snapshot_sheets: string[];
  insert_counts: Record<string, number>;
  conflicts: MasterConflict[];
}

export interface UploadOutcome {
  status: string;
  applied: number;
  rejected: number;
  snapshot_id: number | null;
}

export interface WeeklyKpis {
  total_cost: number;
  backlog_cost: number;
  lost_sales_cost: number;
  floor_slack_cost: number;
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
  stock_minimum: number;
  floor_slack: number;
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

export interface StageReport {
  stage: number;
  status: 'Optimal' | 'Feasible' | 'Infeasible' | 'Not Solved';
  objective: number | null;
  bound: number | null;
  gap: number | null;
  hit_time_limit: boolean;
  seconds: number;
}

export interface WeeklyResult {
  status: string;
  message?: string;
  weeks?: string[];
  production?: WeeklyProductionRow[];
  inventory?: WeeklyInventoryRow[];
  demand?: WeeklyDemandRow[];
  targets?: Record<string, Record<string, number>>;
  stage_objectives?: number[];
  stage_reports?: StageReport[];
  warehouse_capacity?: number | null;
  stock_minimum?: Record<string, number>;
  kpis?: WeeklyKpis;
  run_id?: string;
  duration_seconds?: number;
  source?: string | null;
}

export interface DailyKpis {
  total_cost: number;
  backlog_cost: number;
  target_slack_cost: number;
  setup_cost: number;
  holding_cost: number;
  order_service_level: number;
  form_setup_hours: number;
  color_setup_hours: number;
  total_setups: number;
  solve_seconds: number;
  hit_time_limit: boolean;
  anticipated_kg?: number;
  sequencing_seconds?: number;
}

export interface SequencingReportRow {
  machine: string;
  shift_index: number;
  date: string;
  shift: number;
  form: string;
  production_hours: number;
  color_setup_hours: number;
  form_setup_hours: number;
  available_hours: number;
  idle_hours: number;
  seq_capacidade: number;
  seq_forma: number;
  seq_lote: number;
}

export interface SequencingViolations {
  seq_capacidade: number;
  seq_forma: number;
  seq_lote: number;
  seq_antecipacao: number;
  seq_armazem: number;
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
  delivered_orders: number;
  backlog: number;
  inventory: number;
}

export interface DailyTargetRow {
  product: string;
  week: string;
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
  stage_objectives?: number[];
  stage_reports?: StageReport[];
  shifts?: number;
  kpis?: DailyKpis;
  mip_kpis?: DailyKpis;
  sequencing_report?: SequencingReportRow[];
  sequencing_violations?: SequencingViolations;
  run_id?: string | null;
  duration_seconds?: number;
  source?: string | null;
}

export interface HistoryRun {
  id: string;
  timestamp: string;
  label: string;
  source: string;
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
  snapshot_id: number | null;
  source: string;
  inputs: Settings & { machines: string[] };
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

export type BackendState = 'unknown' | 'starting' | 'connected' | 'disconnected';

export interface BackendStatus {
  state: BackendState;
  connected: boolean;
  machine_label?: string;
}
