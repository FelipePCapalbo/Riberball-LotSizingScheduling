import { useState } from 'react';
import type { Settings } from '../../types';
import AccordionSection from './AccordionSection';
import MachineGrid from './MachineGrid';

interface SidebarProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  dataFiles: string[];
  activeDataFile: string | null;
  onDataFileChange: (file: string) => void;
  machines: string[];
  periods: string[];
  settings: Settings;
  onFieldChange: (patch: Partial<Settings>, save: boolean) => void;
  scenarioLabel: string;
  onScenarioLabelChange: (label: string) => void;
  onRun: () => void;
  running: boolean;
  runStatusText: string;
  runStatusColor: string;
}

function toDateOnly(value: string | null): string {
  return value ? value.split(' ')[0] : '';
}

function toDateTime(value: string): string {
  return value ? `${value} 00:00:00` : '';
}

export default function Sidebar({
  sidebarOpen,
  onToggleSidebar,
  dataFiles,
  activeDataFile,
  onDataFileChange,
  machines,
  periods,
  settings,
  onFieldChange,
  scenarioLabel,
  onScenarioLabelChange,
  onRun,
  running,
  runStatusText,
  runStatusColor,
}: SidebarProps) {
  const [openSections, setOpenSections] = useState({
    data: true,
    horizon: true,
    capacity: true,
    machines: true,
    solver: false,
  });

  const toggleSection = (key: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const activeMachines = new Set(settings.active_machines);
  const highSetupMachines = new Set(settings.high_setup_machines);
  const periodDates = periods.map((p) => p.split(' ')[0]).sort();
  const minDate = periodDates.length > 0 ? periodDates[0] : undefined;
  const maxDate = periodDates.length > 0 ? periodDates[periodDates.length - 1] : undefined;
  const totalHoursPerMonth = (settings.shifts_per_day * settings.hours_per_shift * settings.days_per_week * 4.33).toFixed(2);

  return (
    <aside className={sidebarOpen ? 'sidebar' : 'sidebar sidebar-collapsed'}>
      <div className="sidebar-header">
        {sidebarOpen ? <span className="sidebar-brand">RIBERBALL</span> : null}
        <button className="sidebar-toggle" onClick={onToggleSidebar} title="Recolher painel">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>

      {sidebarOpen ? (
        <div className="sidebar-body">
          <AccordionSection title="Dados" open={openSections.data} onToggle={() => toggleSection('data')}>
            <div className="sb-field">
              <label>Arquivo de input</label>
              <select
                className="form-select form-select-sm"
                value={activeDataFile ?? ''}
                onChange={(e) => onDataFileChange(e.target.value)}
              >
                {dataFiles.map((file) => (
                  <option key={file} value={file}>
                    {file}
                  </option>
                ))}
              </select>
            </div>
          </AccordionSection>

          <AccordionSection title="Horizonte" open={openSections.horizon} onToggle={() => toggleSection('horizon')}>
            <div className="sb-field">
              <label>Início</label>
              <input
                type="date"
                className="form-control form-control-sm"
                min={minDate}
                max={maxDate}
                value={toDateOnly(settings.start_period)}
                onChange={(e) => onFieldChange({ start_period: toDateTime(e.target.value) }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-field">
              <label>Fim</label>
              <input
                type="date"
                className="form-control form-control-sm"
                min={minDate}
                value={toDateOnly(settings.end_period)}
                onChange={(e) => onFieldChange({ end_period: toDateTime(e.target.value) }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-field">
              <label>
                Estoque de Segurança <span className="text-muted fw-normal">(períodos α)</span>
              </label>
              <input
                type="number"
                className="form-control form-control-sm"
                step={1}
                min={0}
                value={settings.coverage_months}
                onChange={(e) => onFieldChange({ coverage_months: parseInt(e.target.value, 10) || 0 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
          </AccordionSection>

          <AccordionSection title="Capacidade" open={openSections.capacity} onToggle={() => toggleSection('capacity')}>
            <div className="sb-field-row">
              <div className="sb-field">
                <label>Turnos/dia</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  step={1}
                  min={1}
                  max={3}
                  value={settings.shifts_per_day}
                  onChange={(e) => onFieldChange({ shifts_per_day: parseFloat(e.target.value) || 0 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
              <div className="sb-field">
                <label>Hrs./turno</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  step={0.5}
                  min={1}
                  max={24}
                  value={settings.hours_per_shift}
                  onChange={(e) => onFieldChange({ hours_per_shift: parseFloat(e.target.value) || 0 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
              <div className="sb-field">
                <label>Dias/sem.</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  step={1}
                  min={1}
                  max={7}
                  value={settings.days_per_week}
                  onChange={(e) => onFieldChange({ days_per_week: parseFloat(e.target.value) || 0 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
            </div>
            <div className="sb-field">
              <label>Horas disponíveis/mês</label>
              <input type="text" className="form-control form-control-sm" readOnly value={totalHoursPerMonth} />
            </div>
          </AccordionSection>

          <AccordionSection title="Máquinas" open={openSections.machines} onToggle={() => toggleSection('machines')}>
            <p className="sb-label">Ativas / Inativas</p>
            <MachineGrid
              machines={machines}
              selected={activeMachines}
              toggledClassName="active"
              onToggle={(machine) => {
                const next = new Set(activeMachines);
                if (next.has(machine)) {
                  next.delete(machine);
                } else {
                  next.add(machine);
                }
                onFieldChange({ active_machines: Array.from(next) }, true);
              }}
            />
            <div className="machine-legend">
              <span>
                <span className="ldot ldot-active"></span>Ativa
              </span>
              <span>
                <span className="ldot ldot-off"></span>Inativa
              </span>
            </div>

            <hr className="sb-divider" />
            <p className="sb-label">Setup alto (máquinas)</p>
            <MachineGrid
              machines={machines}
              selected={highSetupMachines}
              toggledClassName="selected"
              containerClassName="high-setup-grid"
              onToggle={(machine) => {
                const next = new Set(highSetupMachines);
                if (next.has(machine)) {
                  next.delete(machine);
                } else {
                  next.add(machine);
                }
                onFieldChange({ high_setup_machines: Array.from(next) }, true);
              }}
            />
            <div className="sb-field-row mt-2">
              <div className="sb-field">
                <label>Tempo setup alto (h)</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  step={0.5}
                  min={0}
                  value={settings.setup_time_high}
                  onChange={(e) => onFieldChange({ setup_time_high: parseFloat(e.target.value) || 0 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
              <div className="sb-field">
                <label>Tempo setup baixo (h)</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  step={0.5}
                  min={0}
                  value={settings.setup_time_low}
                  onChange={(e) => onFieldChange({ setup_time_low: parseFloat(e.target.value) || 0 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
            </div>
          </AccordionSection>

          <AccordionSection title="Solver" open={openSections.solver} onToggle={() => toggleSection('solver')}>
            <p className="sb-label">Modelo Tático</p>
            <div className="sb-field">
              <label>Motor</label>
              <select
                className="form-select form-select-sm"
                value={settings.solver_name}
                onChange={(e) => onFieldChange({ solver_name: e.target.value }, true)}
              >
                <option value="CBC">CBC (Open-source)</option>
                <option value="GUROBI">Gurobi (Licença)</option>
              </select>
            </div>
            <div className="sb-field">
              <label>Tempo limite (s)</label>
              <input
                type="number"
                className="form-control form-control-sm"
                step={60}
                min={10}
                value={settings.time_limit}
                onChange={(e) => onFieldChange({ time_limit: parseInt(e.target.value, 10) || 0 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>

            <hr className="sb-divider" />
            <p className="sb-label">Modelo Operacional</p>
            <div className="sb-field">
              <label>Método de sequenciamento</label>
              <select
                className="form-select form-select-sm"
                value={settings.color_method}
                onChange={(e) => onFieldChange({ color_method: e.target.value }, true)}
              >
                <option value="heuristic">Heurística</option>
                <option value="milp">Modelo matemático</option>
              </select>
            </div>
            {settings.color_method === 'milp' ? (
              <>
                <div className="sb-field">
                  <label>Motor</label>
                  <select
                    className="form-select form-select-sm"
                    value={settings.color_solver_name}
                    onChange={(e) => onFieldChange({ color_solver_name: e.target.value }, true)}
                  >
                    <option value="CBC">CBC (Open-source)</option>
                    <option value="GUROBI">Gurobi (Licença)</option>
                  </select>
                </div>
                <div className="sb-field">
                  <label>Tempo limite (s)</label>
                  <input
                    type="number"
                    className="form-control form-control-sm"
                    step={60}
                    min={10}
                    value={settings.color_time_limit}
                    onChange={(e) => onFieldChange({ color_time_limit: parseInt(e.target.value, 10) || 0 }, false)}
                    onBlur={() => onFieldChange({}, true)}
                  />
                </div>
              </>
            ) : null}
          </AccordionSection>
        </div>
      ) : null}

      {sidebarOpen ? (
        <div className="sidebar-footer">
          <input
            type="text"
            className="form-control form-control-sm mb-2"
            placeholder="Nome do cenário (opcional)"
            value={scenarioLabel}
            onChange={(e) => onScenarioLabelChange(e.target.value)}
          />
          <button className={running ? 'btn btn-run w-100 loading' : 'btn btn-run w-100'} disabled={running} onClick={onRun}>
            {running ? 'Calculando...' : 'Executar'}
          </button>
          <div className="run-status mt-2" style={{ color: runStatusColor }}>
            {runStatusText}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
