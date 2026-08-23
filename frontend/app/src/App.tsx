import { useEffect, useState } from 'react';
import * as api from './api';
import BackendStatusBadge from './components/BackendStatusBadge';
import KpiBar from './components/KpiBar';
import Sidebar from './components/Sidebar/Sidebar';
import Tabs from './components/Tabs';
import GanttChart from './components/charts/GanttChart';
import InventoryTargetChart from './components/charts/InventoryTargetChart';
import MachineSetupChart from './components/charts/MachineSetupChart';
import NatureChart from './components/charts/NatureChart';
import ComparisonTable from './components/tables/ComparisonTable';
import OperationsTable from './components/tables/OperationsTable';
import OrdersTable from './components/tables/OrdersTable';
import WeeklyPlanTable from './components/tables/WeeklyPlanTable';
import { fmtN } from './format';
import type { DailyResult, HistoryRun, Settings, WeeklyResult } from './types';

const DEFAULT_SETTINGS: Settings = {
  start_week: null,
  weeks_in_plan: 13,
  frozen_weeks: 1,
  coverage_weeks: 2,
  shifts_per_day: 3,
  hours_per_shift: 8,
  working_days_per_week: 6,
  active_machines: [],
  setup_hourly_cost_default: 250,
  setup_hourly_cost_by_machine: {},
  annual_holding_rate: 0.25,
  order_backlog_multiplier: 2,
  coverage_weight: 0.25,
  weekly_solver_name: 'CBC',
  weekly_time_limit: 300,
  daily_solver_name: 'CBC',
  daily_time_limit: 600,
  positions_per_shift: 3,
  threads: null,
};

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dataFiles, setDataFiles] = useState<string[]>([]);
  const [activeDataFile, setActiveDataFile] = useState<string | null>(null);
  const [machines, setMachines] = useState<string[]>([]);
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

  const reloadInitData = async () => {
    const init = await api.getInitData();
    const loaded = await api.getSettings();
    setMachines(init.machines);
    setWeeks(init.weeks);
    setSettings((prev) => {
      const merged = { ...prev, ...loaded };
      if (!merged.active_machines || merged.active_machines.length === 0) {
        merged.active_machines = init.machines.slice();
      }
      if (!merged.start_week && init.weeks.length > 0) {
        merged.start_week = init.weeks[0];
      }
      return merged;
    });
  };

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const attemptInitialLoad = async () => {
      try {
        const files = await api.getDataFiles();
        if (cancelled) {
          return;
        }
        setDataFiles(files.files);
        setActiveDataFile(files.active);
        await reloadInitData();
        if (!cancelled) {
          setStatusText('');
        }
      } catch (err) {
        if (!cancelled) {
          setStatusText(`Aguardando backend conectar... (${(err as Error).message})`);
          setStatusTone('bad');
          timer = window.setTimeout(attemptInitialLoad, 5000);
        }
      }
    };

    attemptInitialLoad();
    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDataFileChange = async (file: string) => {
    setStatusText('Carregando arquivo...');
    setStatusTone('neutral');
    try {
      await api.setDataFile(file);
      setActiveDataFile(file);
      await reloadInitData();
      setStatusText('');
    } catch (err) {
      setStatusText(`Erro ao carregar arquivo: ${(err as Error).message}`);
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
    if (settings.active_machines.length === 0) {
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
        setStatusText(`Plano semanal: ${weeklyResult.status} — ${weeklyResult.message ?? ''}`);
        setStatusTone('bad');
        return;
      }
      setWeekly(weeklyResult);
      setMainTab('weekly');
      setStatusText('Etapa 2 de 2 — programando os turnos...');
      const dailyResult = await api.runDaily();
      if (dailyResult.status !== 'Optimal' && dailyResult.status !== 'Feasible') {
        setDaily(null);
        setStatusText(`Semanal OK; programação por turno: ${dailyResult.status}`);
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
      setWeekly({ ...record.weekly, data_file: record.data_file, duration_seconds: record.weekly.duration_seconds });
      setDaily(record.daily ? { ...record.daily, data_file: record.data_file } : null);
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
    { label: 'Input', value: weekly?.data_file ?? activeDataFile, small: true },
  ];

  const costBreakdown = wk
    ? [
        { label: 'Atraso de carteira', value: wk.backlog_cost },
        { label: 'Venda perdida', value: wk.lost_sales_cost },
        { label: 'Folga de cobertura', value: wk.coverage_cost },
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
        { label: 'Operações', value: `${dk.total_setups}` },
        { label: 'Tempo de solução', value: `${fmtN(dk.solve_seconds, 1)} s`, small: true },
      ]
    : [];

  return (
    <div className="app-shell">
      <Sidebar
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        dataFiles={dataFiles}
        activeDataFile={activeDataFile}
        onDataFileChange={handleDataFileChange}
        machines={machines}
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

      <main className="main-content">
        <div className="main-header">
          <h1>Planejamento de produção</h1>
          <BackendStatusBadge />
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
                      <div className="chart-title">Estoque projetado x meta de cobertura</div>
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
