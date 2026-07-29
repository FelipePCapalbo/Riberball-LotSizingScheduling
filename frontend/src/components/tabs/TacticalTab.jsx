import { useState } from 'react'
import ChartCanvas from '../charts/ChartCanvas.jsx'
import { buildInventoryChartConfig, buildDemandChartConfig, buildProductionChartConfig, getProductionMachines } from '../charts/chartConfigs.js'
import DataTable from '../DataTable.jsx'
import { formatDate, fmtN, fmtCSV, downloadCSV } from '../../lib/format.js'

export default function TacticalTab({ result }) {
    const [subTab, setSubTab] = useState('summary')
    const [selectedMachines, setSelectedMachines] = useState([])

    const summary = result?.summary || []
    const production = result?.production || []
    const setups = result?.setups || []
    const inventory = result?.inventory || []
    const demand = result?.demand || []
    const allMachines = getProductionMachines(production)

    function toggleMachine(machine) {
        setSelectedMachines(prev => prev.includes(machine) ? prev.filter(m => m !== machine) : [...prev, machine])
    }

    const summarySorted = [...summary].sort((a, b) => a.Period.localeCompare(b.Period))
    const productionSorted = [...production].sort((a, b) => {
        if (a.Period !== b.Period) {
            return a.Period.localeCompare(b.Period)
        } else {
            const machineA = parseInt(a.Machine) || 0
            const machineB = parseInt(b.Machine) || 0
            return machineA !== machineB ? machineA - machineB : a.Product.localeCompare(b.Product)
        }
    })
    const setupsSorted = [...setups].sort((a, b) => {
        if (a.Period !== b.Period) {
            return a.Period.localeCompare(b.Period)
        } else {
            return (parseInt(a.Machine) || 0) - (parseInt(b.Machine) || 0)
        }
    })

    return (
        <div>
            <div className="charts-grid">
                <div className="chart-card">
                    <div className="chart-title">Perfil de Estoque (Kg)</div>
                    <ChartCanvas config={buildInventoryChartConfig(inventory)} />
                </div>
                <div className="chart-card">
                    <div className="chart-title">Atendimento da Demanda (Kg)</div>
                    <ChartCanvas config={buildDemandChartConfig(demand)} />
                </div>
            </div>

            <div className="chart-card mt-2">
                <div className="chart-card-header">
                    <span className="chart-title">Produção Agregada (Kg)</span>
                    <div className="prod-filter">
                        <button
                            className={selectedMachines.length === 0 ? 'filter-chip active' : 'filter-chip'}
                            onClick={() => setSelectedMachines([])}
                        >Todas</button>
                        <div className="d-flex flex-wrap gap-1">
                            {allMachines.map(machine => (
                                <button
                                    key={machine}
                                    className={selectedMachines.includes(machine) ? 'filter-chip selected' : 'filter-chip'}
                                    onClick={() => toggleMachine(machine)}
                                >M{machine}</button>
                            ))}
                        </div>
                    </div>
                </div>
                <ChartCanvas config={buildProductionChartConfig(production, selectedMachines)} />
            </div>

            <ul className="nav nav-tabs sub-tabs mt-3" role="tablist">
                <li className="nav-item">
                    <button className={subTab === 'summary' ? 'nav-link active' : 'nav-link'} onClick={() => setSubTab('summary')}>Resumo Mensal</button>
                </li>
                <li className="nav-item">
                    <button className={subTab === 'detailed' ? 'nav-link active' : 'nav-link'} onClick={() => setSubTab('detailed')}>Produção Detalhada</button>
                </li>
                <li className="nav-item">
                    <button className={subTab === 'setups' ? 'nav-link active' : 'nav-link'} onClick={() => setSubTab('setups')}>Setups</button>
                </li>
            </ul>

            <div className="tab-content">
                {subTab === 'summary' && (
                    <div className="tab-pane fade show active">
                        <div className="table-toolbar">
                            <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => downloadCSV(
                                    summary,
                                    ['Mês', 'Estoque', 'Utilização', 'Demanda', 'Perda', 'Produzido'],
                                    r => [formatDate(r.Period), fmtCSV(r.Inventory), fmtCSV(r.Utilization * 100), fmtCSV(r.Demand), fmtCSV(r.Lost), fmtCSV(r.Production)],
                                    'resumo_mensal.csv'
                                )}
                            >Exportar CSV</button>
                        </div>
                        <div className="table-responsive table-scroll">
                            <DataTable
                                columns={[
                                    { header: 'Mês', render: r => formatDate(r.Period) },
                                    { header: 'Estoque (Kg)', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.Inventory, 0) },
                                    { header: 'Utilização', headerClassName: 'text-end', className: 'text-end', render: r => (r.Utilization * 100).toFixed(1) + '%' },
                                    { header: 'Demanda (Kg)', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.Demand, 0) },
                                    { header: 'Perda (Kg)', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.Lost, 0) },
                                    { header: 'Produzido (Kg)', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.Production, 0) }
                                ]}
                                rows={summarySorted}
                                emptyMessage="Nenhum dado."
                            />
                        </div>
                    </div>
                )}

                {subTab === 'detailed' && (
                    <div className="tab-pane fade show active">
                        <div className="table-toolbar">
                            <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => downloadCSV(
                                    production,
                                    ['Período', 'Máquina', 'Produto', 'Horas', 'Dias', 'kg'],
                                    r => [formatDate(r.Period), `M${r.Machine}`, r.Product, fmtCSV(r.Hours), fmtCSV(r.Hours / 24), fmtCSV(r.Kg)],
                                    'producao_detalhada.csv'
                                )}
                            >Exportar CSV</button>
                        </div>
                        <div className="table-responsive table-scroll">
                            <DataTable
                                columns={[
                                    { header: 'Período', render: r => formatDate(r.Period) },
                                    { header: 'Máquina', render: r => `M${r.Machine}` },
                                    { header: 'Produto', render: r => r.Product },
                                    { header: 'Horas', headerClassName: 'text-end', className: 'text-end', render: r => r.Hours.toFixed(1) + ' h' },
                                    { header: 'Dias', headerClassName: 'text-end', className: 'text-end', render: r => (r.Hours / 24).toFixed(1) + ' d' },
                                    { header: 'kg', headerClassName: 'text-end', className: 'text-end', render: r => fmtN(r.Kg, 2) + ' kg' }
                                ]}
                                rows={productionSorted}
                                emptyMessage="Nenhum dado."
                            />
                        </div>
                    </div>
                )}

                {subTab === 'setups' && (
                    <div className="tab-pane fade show active">
                        <div className="table-toolbar">
                            <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => downloadCSV(
                                    setups,
                                    ['Período', 'Máquina', 'De', 'Para', 'Custo (R$)'],
                                    r => [formatDate(r.Period), `M${r.Machine}`, r.From, r.To, fmtCSV(r.Cost || 0)],
                                    'setups_detalhado.csv'
                                )}
                            >Exportar CSV</button>
                        </div>
                        <div className="table-responsive table-scroll">
                            <DataTable
                                columns={[
                                    { header: 'Período', render: r => formatDate(r.Period) },
                                    { header: 'Máquina', render: r => `M${r.Machine}` },
                                    { header: 'De', render: r => r.From },
                                    { header: 'Para', render: r => r.To },
                                    { header: 'Custo (R$)', headerClassName: 'text-end', className: 'text-end', render: r => 'R$ ' + fmtN(r.Cost || 0, 2) }
                                ]}
                                rows={setupsSorted}
                                emptyMessage="Nenhum dado."
                            />
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
