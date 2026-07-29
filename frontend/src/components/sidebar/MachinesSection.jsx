import MachineGrid from './MachineGrid.jsx'

export default function MachinesSection({ open, onToggleOpen, machines, settings, updateField }) {
    function toggleActiveMachine(machine) {
        const current = settings.active_machines
        const next = current.includes(machine)
            ? current.filter(m => m !== machine)
            : [...current, machine]
        updateField('active_machines', next, true)
    }

    function toggleHighSetupMachine(machine) {
        const current = settings.high_setup_machines
        const next = current.includes(machine)
            ? current.filter(m => m !== machine)
            : [...current, machine]
        updateField('high_setup_machines', next, true)
    }

    return (
        <div className="sb-section">
            <button className="sb-section-toggle" onClick={onToggleOpen}>
                Máquinas
                <svg className={open ? 'chevron' : 'chevron rotated'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            </button>
            {open && (
                <div>
                    <p className="sb-label">Ativas / Inativas</p>
                    <MachineGrid machines={machines} selected={settings.active_machines} onToggle={toggleActiveMachine} variant="active" />
                    <div className="machine-legend">
                        <span><span className="ldot ldot-active"></span>Ativa</span>
                        <span><span className="ldot ldot-off"></span>Inativa</span>
                    </div>

                    <hr className="sb-divider" />
                    <p className="sb-label">Setup alto (máquinas)</p>
                    <MachineGrid machines={machines} selected={settings.high_setup_machines} onToggle={toggleHighSetupMachine} variant="high-setup" />
                    <div className="sb-field-row mt-2">
                        <div className="sb-field">
                            <label>Tempo setup alto (h)</label>
                            <input
                                type="number" className="form-control form-control-sm" step="0.5" min="0"
                                value={settings.setup_time_high}
                                onChange={e => updateField('setup_time_high', parseFloat(e.target.value) || 0, false)}
                                onBlur={() => updateField('setup_time_high', settings.setup_time_high, true)}
                            />
                        </div>
                        <div className="sb-field">
                            <label>Tempo setup baixo (h)</label>
                            <input
                                type="number" className="form-control form-control-sm" step="0.5" min="0"
                                value={settings.setup_time_low}
                                onChange={e => updateField('setup_time_low', parseFloat(e.target.value) || 0, false)}
                                onBlur={() => updateField('setup_time_low', settings.setup_time_low, true)}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
