import { useEffect, useState } from 'react';
import * as api from './api';
import BackendStatusBadge from './components/BackendStatusBadge';
import KpiBar from './components/KpiBar';
import Sidebar from './components/Sidebar/Sidebar';
import Tabs from './components/Tabs';
import DemandChart from './components/charts/DemandChart';
import InventoryChart from './components/charts/InventoryChart';
import ProductionChart from './components/charts/ProductionChart';
import ComparisonTable from './components/tables/ComparisonTable';
import DetailedTable from './components/tables/DetailedTable';
import SetupsTable from './components/tables/SetupsTable';
import SummaryTable from './components/tables/SummaryTable';
import type { HistoryRun, Kpis, RunResult, Settings } from './types';

const DEFAULT_SETTINGS: Settings = {
  start_period: null,
  end_period: null,
  coverage_months: 0,
  shifts_per_day: 3,
  hours_per_shift: 8,
  days_per_week: 7,
  active_machines: [],
  high_setup_machines: [],
  setup_time_high: 7,
  setup_time_low: 3,
  solver_name: 'CBC',
  time_limit: 600,
};

function validateSettings(settings: Settings): string | null {
  let error = null;
  if (settings.end_period && settings.start_period && settings.end_period < settings.start_period) {
    error = 'Data de fim deve ser posterior ao início.';
  } else if (settings.active_machines.length === 0) {
    error = 'Selecione ao menos uma máquina.';
  }
  return error;
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dataFiles, setDataFiles] = useState<string[]>([]);
  const [activeDataFile, setActiveDataFile] = useState<string | null>(null);
  const [machines, setMachines] = useState<string[]>([]);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [scenarioLabel, setScenarioLabel] = useState('');
  const [running, setRunning] = useState(false);
  const [runStatusText, setRunStatusText] = useState('');
  const [runStatusColor, setRunStatusColor] = useState('#495057');
  const [result, setResult] = useState<RunResult | null>(null);
  const [kpis, setKpis] = useState<Kpis | undefined>(undefined);
  const [durationSeconds, setDurationSeconds] = useState<number | undefined>(undefined);
  const [resultDataFile, setResultDataFile] = useState<string | null | undefined>(undefined);
  const [mainTab, setMainTab] = useState('results');
  const [subTab, setSubTab] = useState('summary');
  const [historyRuns, setHistoryRuns] = useState<HistoryRun[]>([]);

  const reloadInitData = async () => {
    const init = await api.getInitData();
    const loaded = await api.getSettings();
    const dates = init.periods.map((p) => p.split(' ')[0]).sort();

    setMachines(init.machines);
    setSettings((prev) => {
      const merged = { ...prev, ...loaded };
      if (!merged.start_period && dates.length > 0) {
        merged.start_period = `${dates[0]} 00:00:00`;
      }
      if (!merged.end_period && dates.length > 0) {
        merged.end_period = `${dates[dates.length - 1]} 00:00:00`;
      }
      return merged;
    });
  };

  useEffect(() => {
    (async () => {
      try {
        const files = await api.getDataFiles();
        setDataFiles(files.files);
        setActiveDataFile(files.active);
        await reloadInitData();
      } catch {
        setRunStatusText('Erro ao carregar dados iniciais.');
        setRunStatusColor('#dc3545');
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDataFileChange = async (file: string) => {
    setRunStatusText('Carregando arquivo...');
    setRunStatusColor('#495057');
    await api.setDataFile(file);
    setActiveDataFile(file);
    await reloadInitData();
    setRunStatusText('');
  };

  const handleFieldChange = (patch: Partial<Settings>, save: boolean) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      if (save) {
        api.saveSettings(next);
      }
      return next;
    });
  };

  const applyResult = (
    runResult: RunResult,
    kpisValue: Kpis | undefined,
    duration: number | undefined,
    dataFile: string | null | undefined,
  ) => {
    setResult(runResult);
    setKpis(kpisValue);
    setDurationSeconds(duration);
    setResultDataFile(dataFile);
  };

  const handleRun = async () => {
    const validationError = validateSettings(settings);
    if (validationError) {
      setRunStatusText(validationError);
      setRunStatusColor('#dc3545');
    } else {
      setRunning(true);
      setRunStatusText('Processando...');
      setRunStatusColor('#495057');
      await api.saveSettings(settings);
      try {
        const runResult = await api.runOptimization(scenarioLabel.trim());
        if (runResult.status === 'Optimal' || runResult.status === 'Feasible') {
          const solverLabel = runResult.status === 'Optimal' ? 'Ótimo' : 'Viável';
          setRunStatusText(`${solverLabel} — ${settings.solver_name || 'CBC'}`);
          setRunStatusColor(runResult.status === 'Optimal' ? '#198754' : '#856404');
          applyResult(runResult, runResult.kpis, runResult.duration_seconds, runResult.data_file);
          setMainTab('results');
        } else {
          setRunStatusText(`Status: ${runResult.status || runResult.message}`);
          setRunStatusColor('#dc3545');
        }
      } catch (err) {
        setRunStatusText(`Erro: ${(err as Error).message}`);
        setRunStatusColor('#dc3545');
      } finally {
        setRunning(false);
      }
    }
  };

  const loadHistory = async () => {
    try {
      const runs = await api.getHistory();
      setHistoryRuns(runs);
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
    const record = await api.getHistoryRun(runId);
    if (record?.result) {
      applyResult(record.result, record.kpis, record.duration_seconds, record.data_file);
      setMainTab('results');
    }
  };

  const inventory = result?.inventory ?? [];
  const demand = result?.demand ?? [];
  const production = result?.production ?? [];
  const setups = result?.setups ?? [];
  const summary = result?.summary ?? [];

  return (
    <div className="app-shell">
      <Sidebar
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        dataFiles={dataFiles}
        activeDataFile={activeDataFile}
        onDataFileChange={handleDataFileChange}
        machines={machines}
        settings={settings}
        onFieldChange={handleFieldChange}
        scenarioLabel={scenarioLabel}
        onScenarioLabelChange={setScenarioLabel}
        onRun={handleRun}
        running={running}
        runStatusText={runStatusText}
        runStatusColor={runStatusColor}
      />

      <main className="main-content">
        <div className="main-header">
          <h1>Dimensionamento de Lotes</h1>
          <BackendStatusBadge />
        </div>

        <KpiBar visible={result !== null} kpis={kpis} durationSeconds={durationSeconds} dataFile={resultDataFile} />

        <Tabs
          variant="main"
          activeKey={mainTab}
          onChange={handleMainTabChange}
          tabs={[
            {
              key: 'results',
              label: 'Resultados',
              content: (
                <>
                  <div className="charts-grid">
                    <div className="chart-card">
                      <div className="chart-title">Perfil de Estoque (Kg)</div>
                      <div className="chart-box">
                        <InventoryChart data={inventory} />
                      </div>
                    </div>
                    <div className="chart-card">
                      <div className="chart-title">Atendimento da Demanda (Kg)</div>
                      <div className="chart-box">
                        <DemandChart data={demand} />
                      </div>
                    </div>
                  </div>
                  <div className="chart-card mt-2">
                    <ProductionChart data={production} />
                  </div>

                  <Tabs
                    variant="sub"
                    activeKey={subTab}
                    onChange={setSubTab}
                    tabs={[
                      { key: 'summary', label: 'Resumo Mensal', content: <SummaryTable data={summary} /> },
                      { key: 'detailed', label: 'Produção Detalhada', content: <DetailedTable data={production} /> },
                      { key: 'setups', label: 'Setups', content: <SetupsTable data={setups} /> },
                    ]}
                  />
                </>
              ),
            },
            {
              key: 'comparison',
              label: 'Comparação',
              content: <ComparisonTable runs={historyRuns} onRefresh={loadHistory} onSelectRun={handleSelectHistoryRun} />,
            },
          ]}
        />
      </main>
    </div>
  );
}
