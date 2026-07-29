export default function HorizonSection({ open, onToggleOpen, settings, periods, updateField }) {
    const dates = periods.map(p => p.split(' ')[0]).sort()
    const minDate = dates.length ? dates[0] : undefined
    const maxDate = dates.length ? dates[dates.length - 1] : undefined
    const startValue = settings.start_period ? settings.start_period.split(' ')[0] : ''
    const endValue = settings.end_period ? settings.end_period.split(' ')[0] : ''

    return (
        <div className="sb-section">
            <button className="sb-section-toggle" onClick={onToggleOpen}>
                Horizonte
                <svg className={open ? 'chevron' : 'chevron rotated'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            </button>
            {open && (
                <div>
                    <div className="sb-field">
                        <label>Início</label>
                        <input
                            type="date"
                            className="form-control form-control-sm"
                            min={minDate}
                            max={maxDate}
                            value={startValue}
                            onChange={e => updateField('start_period', e.target.value + ' 00:00:00', true)}
                        />
                    </div>
                    <div className="sb-field">
                        <label>Fim</label>
                        <input
                            type="date"
                            className="form-control form-control-sm"
                            min={minDate}
                            value={endValue}
                            onChange={e => updateField('end_period', e.target.value + ' 00:00:00', true)}
                        />
                    </div>
                    <div className="sb-field">
                        <label>Estoque de Segurança <span className="text-muted fw-normal">(períodos α)</span></label>
                        <input
                            type="number"
                            className="form-control form-control-sm"
                            step="1"
                            min="0"
                            value={settings.coverage_months}
                            onChange={e => updateField('coverage_months', parseInt(e.target.value) || 0, false)}
                            onBlur={() => updateField('coverage_months', settings.coverage_months, true)}
                        />
                    </div>
                </div>
            )}
        </div>
    )
}
