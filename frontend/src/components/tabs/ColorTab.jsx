import { useState } from 'react'
import DataTable from '../DataTable.jsx'
import KpiBar from '../KpiBar.jsx'
import { fmtN } from '../../lib/format.js'

export default function ColorTab({ result, statusMessage, statusType }) {
    const [subTab, setSubTab] = useState('schedule')

    const statusColor = statusType === 'danger' ? '#dc3545'
        : statusType === 'success' ? '#198754'
        : '#495057'

    const colorSchedule = result?.color_schedule || []
    const colorOrders = result?.orders || []
    const colorSetups = result?.color_setups || []

    const kpiItems = [
        { label: 'Nível de Serviço (Cor)', value: result?.kpis?.service_level != null ? result.kpis.service_level.toFixed(1) + '%' : null },
        { label: 'Custo de Atraso', value: result?.kpis?.delay_cost != null ? 'R$ ' + result.kpis.delay_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : null },
        { label: 'Custo de Troca', value: result?.kpis?.setup_cost != null ? 'R$ ' + result.kpis.setup_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : null },
        { label: 'Trocas de Cor', value: result?.kpis?.total_setups ?? null },
        { label: 'Tempo de Execução', value: result?.duration_seconds != null ? result.duration_seconds.toFixed(1) + ' s' : null },
        { label: 'Método', value: result ? (result.method === 'milp' ? 'Modelo matemático' : 'Heurística') : null, small: true }
    ]

    const scheduleSorted = [...colorSchedule].sort((a, b) => {
        if (a.day !== b.day) {
            return a.day - b.day
        } else {
            return (parseInt(a.machine) || 0) - (parseInt(b.machine) || 0)
        }
    })
    const ordersSorted = [...colorOrders].sort((a, b) => a.due_day - b.due_day)
    const setupsSorted = [...colorSetups].sort((a, b) => {
        if (a.day !== b.day) {
            return a.day - b.day
        } else {
            return (parseInt(a.machine) || 0) - (parseInt(b.machine) || 0)
        }
    })

    return (
        <div>
            <div className="table-toolbar">
                <div className="run-status" style={{ color: statusColor }}>{statusMessage}</div>
            </div>

            {result && <KpiBar items={kpiItems} />}

            <ul className="nav nav-tabs sub-tabs mt-3" role="tablist">
                <li className="nav-item">
                    <button className={subTab === 'schedule' ? 'nav-link active' : 'nav-link'} onClick={() => setSubTab('schedule')}>Sequência</button>
                </li>
                <li className="nav-item">
                    <button className={subTab === 'orders' ? 'nav-link active' : 'nav-link'} onClick={() => setSubTab('orders')}>Pedidos</button>
                </li>
                <li className="nav-item">
                    <button className={subTab === 'setups' ? 'nav-link active' : 'nav-link'} onClick={() => setSubTab('setups')}>Trocas de Cor</button>
                </li>
            </ul>

            <div className="tab-content">
                {subTab === 'schedule' && (
                    <div className="tab-pane fade show active">
                        <div className="table-responsive table-scroll">
                            <DataTable
                                columns={[
                                    { header: 'Dia', render: r => r.day },
                                    { header: 'Máquina', render: r => `M${r.machine}` },
                                    { header: 'Produto', render: r => r.product },
                                    { header: 'Cor', render: r => r.color },
                                    { header: 'Horas', headerClassName: 'text-end', className: 'text-end', render: r => r.hours.toFixed(1) + ' h' },
                                    { header: 'Kg', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.kg, 2) + ' kg' }
                                ]}
                                rows={scheduleSorted}
                                emptyMessage="Nenhum dado."
                            />
                        </div>
                    </div>
                )}

                {subTab === 'orders' && (
                    <div className="tab-pane fade show active">
                        <div className="table-responsive table-scroll">
                            <DataTable
                                columns={[
                                    { header: 'SKU', render: r => r.sku },
                                    { header: 'Prazo (dia)', headerClassName: 'text-end', className: 'text-end', render: r => r.due_day },
                                    { header: 'Quantidade', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.quantity, 0) },
                                    { header: 'Atraso', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.delayed_qty, 0) },
                                    {
                                        header: 'Status', render: r => (
                                            r.delayed_qty <= 0.001
                                                ? <span className="badge text-bg-success">No prazo</span>
                                                : <span className="badge text-bg-danger">Atrasado</span>
                                        )
                                    }
                                ]}
                                rows={ordersSorted}
                                emptyMessage="Nenhum dado."
                            />
                        </div>
                    </div>
                )}

                {subTab === 'setups' && (
                    <div className="tab-pane fade show active">
                        <div className="table-responsive table-scroll">
                            <DataTable
                                columns={[
                                    { header: 'Dia', render: r => r.day },
                                    { header: 'Máquina', render: r => `M${r.machine}` },
                                    { header: 'Produto', render: r => r.product },
                                    { header: 'De', render: r => r.from_color },
                                    { header: 'Para', render: r => r.to_color },
                                    { header: 'Setup (h)', headerClassName: 'text-end', className: 'text-end', render: r => r.setup_time.toFixed(2) },
                                    { header: 'Custo (R$)', headerClassName: 'text-end', className: 'text-end', render: r => 'R$ ' + fmtN(r.cost || 0, 2) }
                                ]}
                                rows={setupsSorted}
                                emptyMessage="Nenhuma troca."
                            />
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
