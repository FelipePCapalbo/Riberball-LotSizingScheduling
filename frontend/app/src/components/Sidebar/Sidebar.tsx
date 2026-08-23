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
  weeks: string[];
  settings: Settings;
  onFieldChange: (patch: Partial<Settings>, save: boolean) => void;
  scenarioLabel: string;
  onScenarioLabelChange: (label: string) => void;
  onRun: () => void;
  running: boolean;
  runStatusText: string;
  runStatusTone: string;
}

export default function Sidebar({
  sidebarOpen,
  onToggleSidebar,
  dataFiles,
  activeDataFile,
  onDataFileChange,
  machines,
  weeks,
  settings,
  onFieldChange,
  scenarioLabel,
  onScenarioLabelChange,
  onRun,
  running,
  runStatusText,
  runStatusTone,
}: SidebarProps) {
  const [openSections, setOpenSections] = useState({
    data: true,
    horizon: true,
    capacity: true,
    machines: true,
    costs: false,
    solver: false,
  });

  const toggleSection = (key: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const activeMachines = new Set(settings.active_machines);
  const shiftsPerWeek = settings.shifts_per_day * settings.working_days_per_week;
  const hoursPerWeek = (shiftsPerWeek * settings.hours_per_shift).toFixed(1);

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
              <label>Semana inicial</label>
              <select
                className="form-select form-select-sm"
                value={settings.start_week ?? ''}
                onChange={(e) => onFieldChange({ start_week: e.target.value }, true)}
              >
                {weeks.map((week) => (
                  <option key={week} value={week}>
                    {week}
                  </option>
                ))}
              </select>
            </div>
            <div className="sb-field">
              <label>Semanas no plano</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={1}
                max={52}
                value={settings.weeks_in_plan}
                onChange={(e) => onFieldChange({ weeks_in_plan: parseInt(e.target.value, 10) || 1 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-field">
              <label>
                Semanas congeladas <span className="text-muted fw-normal">(programação por turno)</span>
              </label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={1}
                max={4}
                value={settings.frozen_weeks}
                onChange={(e) => onFieldChange({ frozen_weeks: parseInt(e.target.value, 10) || 1 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-field">
              <label>
                Cobertura <span className="text-muted fw-normal">(semanas à frente, α)</span>
              </label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={0}
                max={12}
                value={settings.coverage_weeks}
                onChange={(e) => onFieldChange({ coverage_weeks: parseInt(e.target.value, 10) || 0 }, false)}
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
                  min={1}
                  max={3}
                  value={settings.shifts_per_day}
                  onChange={(e) => onFieldChange({ shifts_per_day: parseInt(e.target.value, 10) || 1 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
              <div className="sb-field">
                <label>Horas/turno</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  min={1}
                  max={12}
                  step={0.5}
                  value={settings.hours_per_shift}
                  onChange={(e) => onFieldChange({ hours_per_shift: parseFloat(e.target.value) || 1 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
              <div className="sb-field">
                <label>Dias úteis</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  min={1}
                  max={7}
                  value={settings.working_days_per_week}
                  onChange={(e) => onFieldChange({ working_days_per_week: parseInt(e.target.value, 10) || 1 }, false)}
                  onBlur={() => onFieldChange({}, true)}
                />
              </div>
            </div>
            <div className="sb-hint">
              {shiftsPerWeek} turnos/semana · {hoursPerWeek} h/semana por máquina
            </div>
          </AccordionSection>

          <AccordionSection title="Máquinas" open={openSections.machines} onToggle={() => toggleSection('machines')}>
            <MachineGrid
              machines={machines}
              selected={activeMachines}
              onToggle={(machine) => {
                const next = new Set(activeMachines);
                if (next.has(machine)) {
                  next.delete(machine);
                } else {
                  next.add(machine);
                }
                onFieldChange({ active_machines: Array.from(next) }, true);
              }}
              toggledClassName="active"
            />
            <div className="sb-field mt-3">
              <label>Custo horário de setup (R$/h)</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={0}
                step={10}
                value={settings.setup_hourly_cost_default}
                onChange={(e) => onFieldChange({ setup_hourly_cost_default: parseFloat(e.target.value) || 0 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-hint">Mão de obra, energia e composto descartado na limpeza.</div>
          </AccordionSection>

          <AccordionSection title="Custos e prioridades" open={openSections.costs} onToggle={() => toggleSection('costs')}>
            <div className="sb-field">
              <label>Taxa anual de carregamento (θ)</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={0}
                max={1}
                step={0.01}
                value={settings.annual_holding_rate}
                onChange={(e) => onFieldChange({ annual_holding_rate: parseFloat(e.target.value) || 0 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-hint">
              Capital (WACC) + armazenagem + seguro/impostos + obsolescência. Faixa usual: 0,20 a 0,30 ao ano.
            </div>
            <div className="sb-field mt-3">
              <label>Multiplicador de atraso da carteira</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={1}
                step={0.5}
                value={settings.order_backlog_multiplier}
                onChange={(e) => onFieldChange({ order_backlog_multiplier: parseFloat(e.target.value) || 1 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-hint">Quanto o atraso de pedido firme custa frente à venda perdida de previsão.</div>
            <div className="sb-field mt-3">
              <label>Peso da meta de cobertura (ρ)</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={0}
                max={1}
                step={0.05}
                value={settings.coverage_weight}
                onChange={(e) => onFieldChange({ coverage_weight: parseFloat(e.target.value) || 0 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
          </AccordionSection>

          <AccordionSection title="Solver" open={openSections.solver} onToggle={() => toggleSection('solver')}>
            <p className="sb-label">Plano semanal</p>
            <div className="sb-field">
              <label>Motor</label>
              <select
                className="form-select form-select-sm"
                value={settings.weekly_solver_name}
                onChange={(e) => onFieldChange({ weekly_solver_name: e.target.value }, true)}
              >
                <option value="CBC">CBC</option>
                <option value="GUROBI">Gurobi</option>
              </select>
            </div>
            <div className="sb-field">
              <label>Tempo limite (s)</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={10}
                step={30}
                value={settings.weekly_time_limit}
                onChange={(e) => onFieldChange({ weekly_time_limit: parseInt(e.target.value, 10) || 10 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>

            <div className="sb-divider" />
            <p className="sb-label">Programação por turno</p>
            <div className="sb-field">
              <label>Motor</label>
              <select
                className="form-select form-select-sm"
                value={settings.daily_solver_name}
                onChange={(e) => onFieldChange({ daily_solver_name: e.target.value }, true)}
              >
                <option value="CBC">CBC</option>
                <option value="GUROBI">Gurobi</option>
              </select>
            </div>
            <div className="sb-field">
              <label>Tempo limite (s)</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={10}
                step={30}
                value={settings.daily_time_limit}
                onChange={(e) => onFieldChange({ daily_time_limit: parseInt(e.target.value, 10) || 10 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
            <div className="sb-field">
              <label>Posições por turno</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={1}
                max={6}
                value={settings.positions_per_shift}
                onChange={(e) => onFieldChange({ positions_per_shift: parseInt(e.target.value, 10) || 1 }, false)}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
          </AccordionSection>

          <div className="sidebar-footer">
            <div className="sb-field">
              <label>Nome do cenário (opcional)</label>
              <input
                className="form-control form-control-sm"
                value={scenarioLabel}
                onChange={(e) => onScenarioLabelChange(e.target.value)}
              />
            </div>
            <button className={running ? 'btn-run w-100 loading' : 'btn-run w-100'} onClick={onRun} disabled={running}>
              {running ? 'Calculando...' : 'Executar'}
            </button>
            {runStatusText ? (
              <div className={`run-status run-status--${runStatusTone} mt-2`}>{runStatusText}</div>
            ) : null}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
