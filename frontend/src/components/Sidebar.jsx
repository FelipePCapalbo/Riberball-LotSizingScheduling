import { useState } from 'react'
import DataSection from './sidebar/DataSection.jsx'
import HorizonSection from './sidebar/HorizonSection.jsx'
import CapacitySection from './sidebar/CapacitySection.jsx'
import MachinesSection from './sidebar/MachinesSection.jsx'
import SolverSection from './sidebar/SolverSection.jsx'

export default function Sidebar({
    settings, updateField, machines, periods, dataFiles, onSelectFile,
    scenarioLabel, setScenarioLabel, onRun, isRunning, runStatus
}) {
    const [sidebarOpen, setSidebarOpen] = useState(true)
    const [sec, setSec] = useState({ data: true, horizon: true, capacity: true, machines: true, solver: false })

    function toggleSection(name) {
        setSec(prev => ({ ...prev, [name]: !prev[name] }))
    }

    const statusColor = runStatus.type === 'danger' ? '#dc3545'
        : runStatus.type === 'success' ? '#198754'
        : runStatus.type === 'warning' ? '#856404'
        : '#495057'

    return (
        <aside className={sidebarOpen ? 'sidebar' : 'sidebar sidebar-collapsed'}>
            <div className="sidebar-header">
                {sidebarOpen && <span className="sidebar-brand">RIBERBALL</span>}
                <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} title="Recolher painel">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="3" y1="6" x2="21" y2="6" />
                        <line x1="3" y1="12" x2="21" y2="12" />
                        <line x1="3" y1="18" x2="21" y2="18" />
                    </svg>
                </button>
            </div>

            {sidebarOpen && (
                <div className="sidebar-body">
                    <DataSection
                        open={sec.data} onToggleOpen={() => toggleSection('data')}
                        files={dataFiles.files} activeFile={dataFiles.active} onSelectFile={onSelectFile}
                    />
                    <HorizonSection
                        open={sec.horizon} onToggleOpen={() => toggleSection('horizon')}
                        settings={settings} periods={periods} updateField={updateField}
                    />
                    <CapacitySection
                        open={sec.capacity} onToggleOpen={() => toggleSection('capacity')}
                        settings={settings} updateField={updateField}
                    />
                    <MachinesSection
                        open={sec.machines} onToggleOpen={() => toggleSection('machines')}
                        machines={machines} settings={settings} updateField={updateField}
                    />
                    <SolverSection
                        open={sec.solver} onToggleOpen={() => toggleSection('solver')}
                        settings={settings} updateField={updateField}
                    />
                </div>
            )}

            {sidebarOpen && (
                <div className="sidebar-footer">
                    <input
                        type="text" className="form-control form-control-sm mb-2"
                        placeholder="Nome do cenário (opcional)"
                        value={scenarioLabel}
                        onChange={e => setScenarioLabel(e.target.value)}
                    />
                    <button className={isRunning ? 'btn btn-run w-100 loading' : 'btn btn-run w-100'} disabled={isRunning} onClick={onRun}>
                        {isRunning ? 'Calculando...' : 'Executar'}
                    </button>
                    <div className="run-status mt-2" style={{ color: statusColor }}>{runStatus.message}</div>
                </div>
            )}
        </aside>
    )
}
