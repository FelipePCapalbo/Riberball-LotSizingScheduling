export default function ComparisonTab({ runs, onRefresh, onSelectRun }) {
    return (
        <div>
            <div className="table-toolbar">
                <span className="text-muted small">Clique em uma linha para carregar o cenário na aba Planejamento Tático.</span>
                <button className="btn btn-sm btn-outline-secondary" onClick={onRefresh}>Atualizar</button>
            </div>
            <div className="table-responsive">
                <table className="table table-sm table-hover data-table table-fit-content">
                    <thead>
                        <tr>
                            <th rowSpan="2">Cenário</th>
                            <th rowSpan="2">Data/Hora</th>
                            <th rowSpan="2">Horizonte</th>
                            <th className="text-center" rowSpan="2">Máquinas</th>
                            <th colSpan="6" className="text-center">Etapa 1 — Tático</th>
                            <th colSpan="4" className="text-center">Etapa 2 — Operacional (Cores)</th>
                        </tr>
                        <tr>
                            <th>Solver</th>
                            <th className="text-end">Tempo (s)</th>
                            <th className="text-end">Custo (R$)</th>
                            <th className="text-end">Serviço (%)</th>
                            <th className="text-end">Estoque Médio (Kg)</th>
                            <th className="text-end">Giro de Estoque</th>
                            <th>Método</th>
                            <th className="text-end">Tempo (s)</th>
                            <th className="text-end">Custo (R$)</th>
                            <th className="text-end">Serviço (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {runs.length === 0 && (
                            <tr className="table-empty"><td colSpan="14">Nenhuma execução registrada.</td></tr>
                        )}
                        {runs.map(run => {
                            const kpis = run.kpis || {}
                            const colorKpis = run.color_kpis || {}
                            const start = run.start_period ? run.start_period.split(' ')[0] : '—'
                            const end = run.end_period ? run.end_period.split(' ')[0] : '—'
                            const dt = run.timestamp ? run.timestamp.replace('T', ' ') : '—'

                            const cost = kpis.total_cost != null ? 'R$ ' + kpis.total_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '—'
                            const svc = kpis.service_level != null ? kpis.service_level.toFixed(1) + '%' : '—'
                            const inv = kpis.avg_inventory != null ? kpis.avg_inventory.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : '—'
                            const giro = kpis.inventory_turnover != null ? kpis.inventory_turnover.toFixed(2) + 'x' : '—'
                            const dur = run.duration_seconds != null ? run.duration_seconds.toFixed(1) + ' s' : '—'

                            const colorMethodLabel = run.color_method === 'milp' ? 'Modelo matemático'
                                : run.color_method === 'heuristic' ? 'Heurística'
                                : '—'
                            const colorCost = colorKpis.total_cost != null ? 'R$ ' + colorKpis.total_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '—'
                            const colorSvc = colorKpis.service_level != null ? colorKpis.service_level.toFixed(1) + '%' : '—'
                            const colorDur = run.color_duration_seconds != null ? run.color_duration_seconds.toFixed(1) + ' s' : '—'

                            return (
                                <tr key={run.id} className="comparison-row" onClick={() => onSelectRun(run.id)}>
                                    <td>{run.label || run.id}</td>
                                    <td>{dt}</td>
                                    <td>{start} → {end}</td>
                                    <td className="text-center">{run.active_machines_count ?? '—'}</td>
                                    <td>{run.solver_name || '—'}</td>
                                    <td className="text-end">{dur}</td>
                                    <td className="text-end">{cost}</td>
                                    <td className="text-end">{svc}</td>
                                    <td className="text-end">{inv}</td>
                                    <td className="text-end">{giro}</td>
                                    <td>{colorMethodLabel}</td>
                                    <td className="text-end">{colorDur}</td>
                                    <td className="text-end">{colorCost}</td>
                                    <td className="text-end">{colorSvc}</td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
