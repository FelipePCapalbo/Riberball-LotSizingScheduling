import { useEffect, useState } from 'react';
import * as api from './api';
import BackendStatusBadge from './components/BackendStatusBadge';
import KpiBar from './components/KpiBar';
import Sidebar from './components/Sidebar/Sidebar';
import Tabs from './components/Tabs';
import UploadReviewPanel from './components/UploadReviewPanel';
import GanttChart from './components/charts/GanttChart';
import InventoryTargetChart from './components/charts/InventoryTargetChart';
import MachineSetupChart from './components/charts/MachineSetupChart';
import NatureChart from './components/charts/NatureChart';
import ComparisonTable from './components/tables/ComparisonTable';
import OperationsTable from './components/tables/OperationsTable';
import OrdersTable from './components/tables/OrdersTable';
import WeeklyPlanTable from './components/tables/WeeklyPlanTable';
import { ENVIRONMENT } from './environment';
import { fmtN } from './format';
import type {
  BackendState,
  ChangeDecision,
  DailyResult,
  HistoryRun,
  Settings,
  SequencingViolations,
  SnapshotRow,
  StageReport,
  UploadReview,
  WeeklyResult,
} from './types';

const BACKEND_POLL_INTERVAL_MS = 3000;

const SEQUENCING_CONSTRAINTS: { key: keyof SequencingViolations; label: string; unit: string; decimals: number }[] = [
  { key: 'seq_capacidade', label: 'Capacidade do turno', unit: 'h acima', decimals: 2 },
  { key: 'seq_forma', label: 'Produção sem a forma montada', unit: 'kg', decimals: 0 },
  { key: 'seq_lote', label: 'Lote mínimo', unit: 'kg abaixo', decimals: 0 },
  { key: 'seq_antecipacao', label: 'Produção acumulada abaixo do plano (total igual no último turno)', unit: 'kg·turno', decimals: 0 },
  { key: 'seq_armazem', label: 'Capacidade do armazém', unit: 'kg·turno acima', decimals: 0 },
];

const DEFAULT_SETTINGS: Settings = {
  start_week: null,
  weeks_in_plan: 13,
  frozen_weeks: 1,
  shifts_per_day: 3,
  hours_per_shift: 8,
  working_days_per_week: 6,
  warehouse_capacity_kg: null,
  annual_holding_rate: 0.25,
  weekly_solver_name: 'ORTOOLS',
  weekly_time_limit: 300,
  daily_solver_name: 'ORTOOLS',
  daily_time_limit: 600,
  threads: null,
};

function failedStageText(stageReports: StageReport[] | undefined): string {
  let text = '';
  if (stageReports) {
    for (const report of stageReports) {
      if (text === '' && report.status !== 'Optimal' && report.status !== 'Feasible') {
        text = ` (estágio ${report.stage}: ${report.status})`;
      }
    }
  }
  return text;
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [snapshots, setSnapshots] = useState<SnapshotRow[]>([]);
  const [activeSnapshotId, setActiveSnapshotId] = useState<number | null>(null);
  const [dataSource, setDataSource] = useState<string | null>(null);
  const [machines, setMachines] = useState<string[]>([]);
  const [activeMachines, setActiveMachines] = useState<string[]>([]);
  const [twoColorMachines, setTwoColorMachines] = useState<string[]>([]);
  const [uploadReview, setUploadReview] = useState<UploadReview | null>(null);
  const [uploading, setUploading] = useState(false);
  const [applyingUpload, setApplyingUpload] = useState(false);
  const [weeks, setWeeks] = useState<string[]>([]);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [scenarioLabel, setScenarioLabel] = useState('');
  const [running, setRunning] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [statusTone, setStatusTone] = useState('neutral');
  const [weekly, setWeekly] = useState<WeeklyResult | null>(null);
  const [daily, setDaily] = useState<DailyResult | null>(null);
  const [mainTab, setMainTab] = useState('weekly');
  const [historyRuns, setHistoryRuns] = useState<HistoryRun[]>([]);
  const [backendState, setBackendState] = useState<BackendState>('unknown');
  const [backendMachine, setBackendMachine] = useState<string | undefined>(undefined);

  const reloadInitData = async () => {
    const snapshotList = await api.getSnapshots();
    const init = await api.getInitData();
    const loaded = await api.getSettings();
    setSnapshots(snapshotList.snapshots);
    setActiveSnapshotId(snapshotList.active);
    setDataSource(init.source);
    setMachines(init.machines);
    setActiveMachines(init.active_machines);
    setTwoColorMachines(init.two_color_machines);
    setWeeks(init.weeks);
    setSettings((prev) => {
      const merged = { ...prev, ...loaded };
      if (init.weeks.length > 0 && (!merged.start_week || !init.weeks.includes(merged.start_week))) {
        merged.start_week = init.weeks[0];
      }
      if (!merged.start_week && init.weeks.length > 0) {
        merged.start_week = init.weeks[0];
      }
      const allowedSolverNames: string[] = [];
      for (const solverOption of ENVIRONMENT.solverOptions) {
        allowedSolverNames.push(solverOption.value);
      }
      if (!allowedSolverNames.includes(merged.weekly_solver_name)) {
        merged.weekly_solver_name = allowedSolverNames[0];
      }
      if (!allowedSolverNames.includes(merged.daily_solver_name)) {
        merged.daily_solver_name = allowedSolverNames[0];
      }
      return merged;
    });
  };

  useEffect(() => {
    let cancelled = false;
    let loaded = false;
    let loadInFlight = false;

    const pollBackend = async () => {
      let backendIsReady = false;
      try {
        const status = await api.getBackendStatus();
        if (!cancelled) {
          setBackendState(status.state);
          setBackendMachine(status.machine_label);
          backendIsReady = status.state === 'connected';
          if (!loaded && !backendIsReady) {
            if (status.state === 'starting') {
              setStatusText(`Backend registrado em ${status.machine_label}, aguardando o túnel ficar pronto...`);
              setStatusTone('warn');
            } else {
              setStatusText('Nenhum backend conectado. Rode init.sh na máquina do backend.');
              setStatusTone('bad');
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          setBackendState('disconnected');
          if (!loaded) {
            setStatusText(`Sem resposta do Worker... (${(err as Error).message})`);
            setStatusTone('bad');
          }
        }
      }

      if (backendIsReady && !loaded && !loadInFlight && !cancelled) {
        loadInFlight = true;
        try {
          if (!cancelled) {
            await reloadInitData();
          }
          loaded = true;
          if (!cancelled) {
            setStatusText('');
            setStatusTone('neutral');
          }
        } catch (err) {
          if (!cancelled) {
            setStatusText(`Backend conectado, carregando dados... (${(err as Error).message})`);
            setStatusTone('warn');
          }
        }
        loadInFlight = false;
      }
    };

    pollBackend();
    const intervalId = window.setInterval(pollBackend, BACKEND_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSnapshotChange = async (snapshotId: number) => {
    setStatusText('Carregando fotografia...');
    setStatusTone('neutral');
    try {
      await api.setActiveSnapshot(snapshotId);
      await reloadInitData();
      setStatusText('');
    } catch (err) {
      setStatusText(`Erro ao carregar fotografia: ${(err as Error).message}`);
      setStatusTone('bad');
    }
  };

  const handleUploadFile = async (file: File) => {
    setUploading(true);
    setStatusText(`Lendo ${file.name}...`);
    setStatusTone('neutral');
    try {
      setUploadReview(await api.uploadWorkbook(file));
      setStatusText('');
    } catch (err) {
      setStatusText(`Erro ao ler o Excel: ${(err as Error).message}`);
      setStatusTone('bad');
    } finally {
      setUploading(false);
    }
  };

  const handleApplyUpload = async (decisions: Record<string, ChangeDecision>) => {
    if (uploadReview) {
      setApplyingUpload(true);
      try {
        const outcome = await api.applyUpload(uploadReview.upload_id, decisions);
        setUploadReview(null);
        await reloadInitData();
        setStatusText(`Upload aplicado: ${outcome.applied} mudanças gravadas, ${outcome.rejected} rejeitadas.`);
        setStatusTone('good');
      } catch (err) {
        setStatusText(`Erro ao aplicar o upload: ${(err as Error).message}`);
        setStatusTone('bad');
      } finally {
        setApplyingUpload(false);
      }
    }
  };

  const handleDiscardUpload = async () => {
    if (uploadReview) {
      try {
        await api.discardUpload(uploadReview.upload_id);
        setStatusText('Upload descartado; o cadastro não mudou.');
        setStatusTone('neutral');
      } catch (err) {
        setStatusText(`Erro ao descartar o upload: ${(err as Error).message}`);
        setStatusTone('bad');
      }
      setUploadReview(null);
    }
  };

  const handleMachineToggle = async (machine: string) => {
    const isActive = !activeMachines.includes(machine);
    const next: string[] = [];
    for (const candidate of machines) {
      if (candidate === machine) {
        if (isActive) {
          next.push(candidate);
        }
      } else if (activeMachines.includes(candidate)) {
        next.push(candidate);
      }
    }
    setActiveMachines(next);
    try {
      await api.setMachineActive(machine, isActive);
    } catch (err) {
      setStatusText(`Erro ao gravar a máquina: ${(err as Error).message}`);
      setStatusTone('bad');
    }
  };

  const handleTwoColorToggle = async (machine: string) => {
    const isTwoColor = !twoColorMachines.includes(machine);
    const next: string[] = [];
    for (const candidate of machines) {
      if (candidate === machine) {
        if (isTwoColor) {
          next.push(candidate);
        }
      } else if (twoColorMachines.includes(candidate)) {
        next.push(candidate);
      }
    }
    setTwoColorMachines(next);
    let colorSides = 1;
    if (isTwoColor) {
      colorSides = 2;
    }
    try {
      await api.setMachineColorSides(machine, colorSides);
    } catch (err) {
      setStatusText(`Erro ao gravar a máquina: ${(err as Error).message}`);
      setStatusTone('bad');
    }
  };

  const handleFieldChange = (patch: Partial<Settings>, save: boolean) => {
    const next = { ...settings, ...patch };
    setSettings(next);
    if (save) {
      api.saveSettings(next).catch(() => undefined);
    }
  };

  const handleRun = async () => {
    if (activeSnapshotId === null) {
      setStatusText('Suba um Excel com os dados antes de executar.');
      setStatusTone('bad');
      return;
    }
    if (activeMachines.length === 0) {
      setStatusText('Selecione ao menos uma máquina.');
      setStatusTone('bad');
      return;
    }
    setRunning(true);
    setDaily(null);
    setStatusText('Etapa 1 de 2 — resolvendo o plano semanal...');
    setStatusTone('neutral');
    try {
      const weeklyResult = await api.runWeekly(settings, scenarioLabel.trim());
      if (weeklyResult.status !== 'Optimal' && weeklyResult.status !== 'Feasible') {
        setStatusText(`Plano semanal: ${weeklyResult.status}${failedStageText(weeklyResult.stage_reports)} — ${weeklyResult.message ?? ''}`);
        setStatusTone('bad');
        return;
      }
      setWeekly(weeklyResult);
      setMainTab('weekly');
      setStatusText('Etapa 2 de 2 — programando os turnos...');
      const dailyResult = await api.runDaily(weeklyResult.run_id);
      if (dailyResult.status !== 'Optimal' && dailyResult.status !== 'Feasible') {
        setDaily(null);
        setStatusText(`Semanal OK; programação por turno: ${dailyResult.status}${failedStageText(dailyResult.stage_reports)}`);
        setStatusTone('warn');
        return;
      }
      setDaily(dailyResult);
      const truncated = weeklyResult.kpis?.hit_time_limit || dailyResult.kpis?.hit_time_limit;
      setStatusText(truncated ? 'Concluído — limite de tempo atingido, solução pode não ser ótima' : 'Concluído');
      setStatusTone(truncated ? 'warn' : 'good');
    } catch (err) {
      setStatusText(`Erro: ${(err as Error).message}`);
      setStatusTone('bad');
    } finally {
      setRunning(false);
    }
  };

  const loadHistory = async () => {
    try {
      setHistoryRuns(await api.getHistory());
    } catch {
      setHistoryRuns([]);
    }
  };

  const handleMainTabChange = (key: string) => {
    setMainTab(key);
    if (key === 'comparison') {
      loadHistory();
    }
  };

  const handleSelectHistoryRun = async (runId: string) => {
    try {
      const record = await api.getHistoryRun(runId);
      setWeekly({ ...record.weekly, source: record.source, run_id: record.id, duration_seconds: record.weekly.duration_seconds });
      setDaily(record.daily ? { ...record.daily, source: record.source, run_id: record.id } : null);
      setStatusText(`Cenário carregado: ${record.label}`);
      setStatusTone('neutral');
      setMainTab('weekly');
    } catch (err) {
      setStatusText(`Erro ao carregar cenário: ${(err as Error).message}`);
      setStatusTone('bad');
    }
  };

  const wk = weekly?.kpis;
  const dk = daily?.kpis;

  /* O custo semanal e o diario NAO se somam: o diario re-precifica, em detalhe de turno,
     a mesma semana congelada que ja esta dentro do plano semanal. Sao reportados lado a lado. */
  const kpiItems = [
    { label: `Custo do plano (${weekly?.weeks?.length ?? 0} sem.)`, value: wk ? `R$ ${fmtN(wk.total_cost, 0)}` : null },
    { label: 'Serviço — carteira', value: wk ? `${fmtN(wk.order_service_level, 2)}%` : null },
    { label: 'Serviço — previsão', value: wk ? `${fmtN(wk.forecast_service_level, 2)}%` : null },
    { label: 'Estoque médio', value: wk ? `${fmtN(wk.avg_inventory, 0)} kg` : null },
    { label: 'Giro', value: wk ? fmtN(wk.inventory_turnover, 2) : null },
    { label: 'Horas de setup (plano)', value: wk ? `${fmtN(wk.setup_hours, 1)} h` : null },
    { label: 'Input', value: weekly?.source ?? dataSource, small: true },
  ];

  const costBreakdown = wk
    ? [
        { label: 'Atraso de carteira', value: wk.backlog_cost },
        { label: 'Venda perdida', value: wk.lost_sales_cost },
        { label: 'Violação do estoque mínimo', value: wk.floor_slack_cost },
        { label: 'Setup', value: wk.setup_cost },
        { label: 'Estoque', value: wk.holding_cost },
      ]
    : [];

  const dailyKpiItems = dk
    ? [
        { label: 'Custo da semana congelada', value: `R$ ${fmtN(dk.total_cost, 0)}` },
        { label: 'Serviço — carteira', value: `${fmtN(dk.order_service_level, 2)}%` },
        { label: 'Setup de forma', value: `${fmtN(dk.form_setup_hours, 2)} h` },
        { label: 'Setup de cor', value: `${fmtN(dk.color_setup_hours, 2)} h` },
        { label: 'Reserva de cor do MIP', value: `${fmtN(daily?.mip_kpis?.color_setup_hours, 2)} h` },
        { label: 'Antecipado', value: `${fmtN(dk.anticipated_kg, 0)} kg` },
        { label: 'Operações', value: `${dk.total_setups}` },
        { label: 'Tempo do MIP', value: `${fmtN(dk.solve_seconds, 1)} s`, small: true },
        { label: 'Tempo do sequenciamento', value: `${fmtN(dk.sequencing_seconds, 2)} s`, small: true },
      ]
    : [];

  return (
    <div className="app-shell">
      <Sidebar
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        snapshots={snapshots}
        activeSnapshotId={activeSnapshotId}
        onSnapshotChange={handleSnapshotChange}
        onUploadFile={handleUploadFile}
        uploading={uploading}
        machines={machines}
        activeMachines={activeMachines}
        onMachineToggle={handleMachineToggle}
        twoColorMachines={twoColorMachines}
        onTwoColorToggle={handleTwoColorToggle}
        weeks={weeks}
        settings={settings}
        onFieldChange={handleFieldChange}
        scenarioLabel={scenarioLabel}
        onScenarioLabelChange={setScenarioLabel}
        onRun={handleRun}
        running={running}
        runStatusText={statusText}
        runStatusTone={statusTone}
      />

      {uploadReview && (
        <UploadReviewPanel
          key={uploadReview.upload_id}
          review={uploadReview}
          busy={applyingUpload}
          onApply={handleApplyUpload}
          onDiscard={handleDiscardUpload}
        />
      )}

      <main className="main-content">
        <div className="main-header">
          <h1>Planejamento de produção</h1>
          <BackendStatusBadge state={backendState} machineLabel={backendMachine} />
        </div>

        {weekly ? <KpiBar items={kpiItems} /> : null}

        <Tabs
          variant="main"
          activeKey={mainTab}
          onChange={handleMainTabChange}
          tabs={[
            {
              key: 'weekly',
              label: 'Plano semanal',
              content: weekly ? (
                <>
                  <div className="charts-grid">
                    <div className="chart-card">
                      <div className="chart-title">Estoque projetado x estoque mínimo</div>
                      <div className="chart-box">
                        <InventoryTargetChart data={weekly.inventory ?? []} />
                      </div>
                    </div>
                    <div className="chart-card">
                      <div className="chart-title">Natureza da produção</div>
                      <div className="chart-box">
                        <NatureChart demand={weekly.demand ?? []} production={weekly.production ?? []} />
                      </div>
                    </div>
                  </div>
                  <div className="chart-card mt-2">
                    <div className="chart-title">Composição do custo do plano semanal (R$)</div>
                    <div className="cost-breakdown">
                      {costBreakdown.map((item) => (
                        <div className="cost-item" key={item.label}>
                          <span className="cost-label">{item.label}</span>
                          <span className="cost-value">{fmtN(item.value, 0)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="chart-card mt-2">
                    <WeeklyPlanTable
                      demand={weekly.demand ?? []}
                      inventory={weekly.inventory ?? []}
                      production={weekly.production ?? []}
                    />
                  </div>
                </>
              ) : (
                <div className="empty-state">Execute para ver o plano semanal.</div>
              ),
            },
            {
              key: 'daily',
              label: 'Programação por turno',
              content: daily ? (
                <>
                  <KpiBar items={dailyKpiItems} />
                  <div className="chart-card mt-2">
                    <div className="chart-title">Máquina x turno</div>
                    <GanttChart
                      data={daily.schedule ?? []}
                      hoursPerShift={settings.hours_per_shift}
                      shiftsPerDay={settings.shifts_per_day}
                    />
                  </div>
                  {daily.sequencing_violations && (
                    <div className="chart-card mt-2">
                      <div className="chart-title">Restrições do sequenciamento (0 = respeitada)</div>
                      <div className="cost-breakdown">
                        {SEQUENCING_CONSTRAINTS.map((constraint) => (
                          <div className="cost-item" key={constraint.key}>
                            <span className="cost-label">
                              {constraint.label} ({constraint.key})
                            </span>
                            <span className="cost-value">
                              {fmtN(daily.sequencing_violations?.[constraint.key], constraint.decimals)} {constraint.unit}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="chart-card mt-2">
                    <div className="chart-title">Horas por máquina</div>
                    <div className="chart-box">
                      <MachineSetupChart data={daily.schedule ?? []} />
                    </div>
                  </div>
                  <div className="chart-card mt-2">
                    <OperationsTable data={daily.schedule ?? []} />
                  </div>
                </>
              ) : (
                <div className="empty-state">Sem programação por turno para o cenário atual.</div>
              ),
            },
            {
              key: 'orders',
              label: 'Carteira',
              content: daily ? (
                <div className="chart-card">
                  <OrdersTable data={daily.orders ?? []} />
                </div>
              ) : (
                <div className="empty-state">Sem dados de carteira para o cenário atual.</div>
              ),
            },
            {
              key: 'comparison',
              label: 'Comparação de cenários',
              content: (
                <ComparisonTable runs={historyRuns} onRefresh={loadHistory} onSelectRun={handleSelectHistoryRun} />
              ),
            },
          ]}
        />
      </main>
    </div>
  );
}
