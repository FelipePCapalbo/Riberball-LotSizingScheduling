import { useState } from 'react';
import { ENVIRONMENT } from '../../environment';
import type { Settings, SnapshotRow } from '../../types';
import AccordionSection from './AccordionSection';
import MachineGrid from './MachineGrid';

interface SidebarProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  snapshots: SnapshotRow[];
  activeSnapshotId: number | null;
  onSnapshotChange: (snapshotId: number) => void;
  onUploadFile: (file: File) => void;
  uploading: boolean;
  machines: string[];
  activeMachines: string[];
  onMachineToggle: (machine: string) => void;
  twoColorMachines: string[];
  onTwoColorToggle: (machine: string) => void;
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
  snapshots,
  activeSnapshotId,
  onSnapshotChange,
  onUploadFile,
  uploading,
  machines,
  activeMachines,
  onMachineToggle,
  twoColorMachines,
  onTwoColorToggle,
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

  const activeMachineSet = new Set(activeMachines);
  const twoColorMachineSet = new Set(twoColorMachines);
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
            <div className="sb-field sb-upload">
              <label className="btn btn-sm btn-outline-secondary w-100 mb-0">
                {uploading && 'Lendo o Excel...'}
                {!uploading && 'Subir Excel'}
                <input
                  type="file"
                  accept=".xlsx"
                  disabled={uploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      onUploadFile(file);
                    }
                    e.target.value = '';
                  }}
                />
              </label>
            </div>
            <div className="sb-field">
              <label>Fotografia de planejamento</label>
              <select
                className="form-select form-select-sm"
                value={activeSnapshotId ?? ''}
                onChange={(e) => onSnapshotChange(parseInt(e.target.value, 10))}
              >
                {activeSnapshotId === null && <option value="">Nenhuma — suba um Excel</option>}
                {snapshots.map((snapshot) => (
                  <option key={snapshot.snapshot_id} value={snapshot.snapshot_id}>
                    #{snapshot.snapshot_id} {snapshot.source_file} ({snapshot.created_at.replace('T', ' ').slice(0, 16)})
                  </option>
                ))}
              </select>
            </div>
            <div className="sb-hint">
              Cadastro (máquinas, produtividade, setups, custos, MTS/MTO) e fotografia (demanda, carteira, estoque) vêm do
              Excel; mudanças no cadastro passam por aprovação.
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
                Semanas detalhadas em turnos <span className="text-muted fw-normal">(operacional)</span>
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
            <div className="sb-field">
              <label>
                Capacidade do armazém (kg) <span className="text-muted fw-normal">(vazio = sem limite)</span>
              </label>
              <input
                type="number"
                className="form-control form-control-sm"
                min={0}
                value={settings.warehouse_capacity_kg ?? ''}
                onChange={(e) => {
                  let warehouseCapacity: number | null = null;
                  if (e.target.value !== '') {
                    warehouseCapacity = parseFloat(e.target.value);
                  }
                  onFieldChange({ warehouse_capacity_kg: warehouseCapacity }, false);
                }}
                onBlur={() => onFieldChange({}, true)}
              />
            </div>
          </AccordionSection>

          <AccordionSection title="Máquinas" open={openSections.machines} onToggle={() => toggleSection('machines')}>
            <MachineGrid
              machines={machines}
              selected={activeMachineSet}
              onToggle={onMachineToggle}
              toggledClassName="active"
            />
            <div className="sb-hint">
              Ativar ou desativar uma máquina grava no cadastro. O custo horário de setup de cada máquina vem da aba
              Maquinas do Excel.
            </div>
            <div className="sb-field">
              <label>Máquinas de duas cores</label>
            </div>
            <MachineGrid
              machines={machines}
              selected={twoColorMachineSet}
              onToggle={onTwoColorToggle}
              toggledClassName="selected"
              containerClassName="two-color-grid"
            />
            <div className="sb-hint">
              Na máquina de duas cores cada lado tem o seu tanque e roda com a taxa cadastrada. A forma é a mesma nos
              dois lados, e a troca de cor de um lado não para o outro.
            </div>
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
          </AccordionSection>

          <AccordionSection title="Solver" open={openSections.solver} onToggle={() => toggleSection('solver')}>
            <p className="sb-label">Plano semanal</p>
            {ENVIRONMENT.solverOptions.length > 1 && (
              <div className="sb-field">
                <label>Motor</label>
                <select
                  className="form-select form-select-sm"
                  value={settings.weekly_solver_name}
                  onChange={(e) => onFieldChange({ weekly_solver_name: e.target.value }, true)}
                >
                  {ENVIRONMENT.solverOptions.map((solverOption) => (
                    <option key={solverOption.value} value={solverOption.value}>
                      {solverOption.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
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
            {ENVIRONMENT.solverOptions.length > 1 && (
              <div className="sb-field">
                <label>Motor</label>
                <select
                  className="form-select form-select-sm"
                  value={settings.daily_solver_name}
                  onChange={(e) => onFieldChange({ daily_solver_name: e.target.value }, true)}
                >
                  {ENVIRONMENT.solverOptions.map((solverOption) => (
                    <option key={solverOption.value} value={solverOption.value}>
                      {solverOption.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
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
