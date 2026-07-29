export default function CapacitySection({ open, onToggleOpen, settings, updateField }) {
    const totalHours = (settings.shifts_per_day * settings.hours_per_shift * settings.days_per_week * 4.33).toFixed(2)

    return (
        <div className="sb-section">
            <button className="sb-section-toggle" onClick={onToggleOpen}>
                Capacidade
                <svg className={open ? 'chevron' : 'chevron rotated'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            </button>
            {open && (
                <div>
                    <div className="sb-field-row">
                        <div className="sb-field">
                            <label>Turnos/dia</label>
                            <input
                                type="number" className="form-control form-control-sm" step="1" min="1" max="3"
                                value={settings.shifts_per_day}
                                onChange={e => updateField('shifts_per_day', parseFloat(e.target.value) || 0, false)}
                                onBlur={() => updateField('shifts_per_day', settings.shifts_per_day, true)}
                            />
                        </div>
                        <div className="sb-field">
                            <label>Hrs./turno</label>
                            <input
                                type="number" className="form-control form-control-sm" step="0.5" min="1" max="24"
                                value={settings.hours_per_shift}
                                onChange={e => updateField('hours_per_shift', parseFloat(e.target.value) || 0, false)}
                                onBlur={() => updateField('hours_per_shift', settings.hours_per_shift, true)}
                            />
                        </div>
                        <div className="sb-field">
                            <label>Dias/sem.</label>
                            <input
                                type="number" className="form-control form-control-sm" step="1" min="1" max="7"
                                value={settings.days_per_week}
                                onChange={e => updateField('days_per_week', parseFloat(e.target.value) || 0, false)}
                                onBlur={() => updateField('days_per_week', settings.days_per_week, true)}
                            />
                        </div>
                    </div>
                    <div className="sb-field">
                        <label>Horas disponíveis/mês</label>
                        <input type="text" className="form-control form-control-sm" readOnly value={totalHours} />
                    </div>
                </div>
            )}
        </div>
    )
}
