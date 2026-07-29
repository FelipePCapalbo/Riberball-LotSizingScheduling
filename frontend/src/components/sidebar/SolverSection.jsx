export default function SolverSection({ open, onToggleOpen, settings, updateField }) {
    return (
        <div className="sb-section">
            <button className="sb-section-toggle" onClick={onToggleOpen}>
                Solver
                <svg className={open ? 'chevron' : 'chevron rotated'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            </button>
            {open && (
                <div>
                    <p className="sb-label">Modelo Tático</p>
                    <div className="sb-field">
                        <label>Motor</label>
                        <select
                            className="form-select form-select-sm"
                            value={settings.solver_name}
                            onChange={e => updateField('solver_name', e.target.value, true)}
                        >
                            <option value="CBC">CBC (Open-source)</option>
                            <option value="GUROBI">Gurobi (Licença)</option>
                        </select>
                    </div>
                    <div className="sb-field">
                        <label>Tempo limite (s)</label>
                        <input
                            type="number" className="form-control form-control-sm" step="60" min="10"
                            value={settings.time_limit}
                            onChange={e => updateField('time_limit', parseInt(e.target.value) || 0, false)}
                            onBlur={() => updateField('time_limit', settings.time_limit, true)}
                        />
                    </div>

                    <hr className="sb-divider" />
                    <p className="sb-label">Modelo Operacional</p>
                    <div className="sb-field">
                        <label>Método de sequenciamento</label>
                        <select
                            className="form-select form-select-sm"
                            value={settings.color_method}
                            onChange={e => updateField('color_method', e.target.value, true)}
                        >
                            <option value="heuristic">Heurística</option>
                            <option value="milp">Modelo matemático</option>
                        </select>
                    </div>
                    {settings.color_method === 'milp' && (
                        <div>
                            <div className="sb-field">
                                <label>Motor</label>
                                <select
                                    className="form-select form-select-sm"
                                    value={settings.color_solver_name}
                                    onChange={e => updateField('color_solver_name', e.target.value, true)}
                                >
                                    <option value="CBC">CBC (Open-source)</option>
                                    <option value="GUROBI">Gurobi (Licença)</option>
                                </select>
                            </div>
                            <div className="sb-field">
                                <label>Tempo limite (s)</label>
                                <input
                                    type="number" className="form-control form-control-sm" step="60" min="10"
                                    value={settings.color_time_limit}
                                    onChange={e => updateField('color_time_limit', parseInt(e.target.value) || 0, false)}
                                    onBlur={() => updateField('color_time_limit', settings.color_time_limit, true)}
                                />
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
