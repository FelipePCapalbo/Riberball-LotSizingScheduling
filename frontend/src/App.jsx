import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import KpiBar from './components/KpiBar.jsx'
import TacticalTab from './components/tabs/TacticalTab.jsx'
import ColorTab from './components/tabs/ColorTab.jsx'
import ComparisonTab from './components/tabs/ComparisonTab.jsx'
import {
    getDataFiles, setDataFile, getInitData, getSettings, postSettings,
    runTactical, runColor, getHistory, getHistoryRun
} from './api/client.js'

const DEFAULT_SETTINGS = {
    start_period: null,
    end_period: null,
    coverage_months: 0,
    shifts_per_day: 3,
    hours_per_shift: 8,
    days_per_week: 7,
    active_machines: [],
    high_setup_machines: [],
    setup_time_high: 7,
    setup_time_low: 3,
    solver_name: 'CBC',
    time_limit: 600,
    color_method: 'heuristic',
    color_solver_name: 'CBC',
    color_time_limit: 600
}

export default function App() {
    const [settings, setSettings] = useState(DEFAULT_SETTINGS)
    const [dataFiles, setDataFiles] = useState({ files: [], active: null })
    const [machines, setMachines] = useState([])
    const [periods, setPeriods] = useState([])
    const [scenarioLabel, setScenarioLabel] = useState('')
    const [activeTab, setActiveTab] = useState('results')
    const [isRunning, setIsRunning] = useState(false)
    const [runStatus, setRunStatus] = useState({ message: '', type: '' })
    const [colorRunStatus, setColorRunStatus] = useState({ message: '', type: '' })
    const [tacticalResult, setTacticalResult] = useState(null)
    const [colorResult, setColorResult] = useState(null)
    const [historyRuns, setHistoryRuns] = useState([])

    useEffect(() => {
        init()
    }, [])

    async function init() {
        try {
            const files = await getDataFiles()
            setDataFiles(files)
            await loadInitData()
        } catch (err) {
            setRunStatus({ message: 'Erro ao carregar dados iniciais.', type: 'danger' })
        }
    }

    async function loadInitData() {
        const initData = await getInitData()
        setPeriods(initData.periods)
        setMachines(initData.machines)

        const loaded = await getSettings()
        const dates = initData.periods.map(p => p.split(' ')[0]).sort()

        setSettings(prev => {
            const merged = { ...prev, ...loaded }
            if (!merged.active_machines || merged.active_machines.length === 0) {
                merged.active_machines = initData.machines.slice()
            }
            if (!merged.start_period && dates.length) {
                merged.start_period = dates[0] + ' 00:00:00'
            }
            if (!merged.end_period && dates.length) {
                merged.end_period = dates[dates.length - 1] + ' 00:00:00'
            }
            return merged
        })
    }

    async function handleSelectFile(file) {
        setRunStatus({ message: 'Carregando arquivo...', type: '' })
        await setDataFile(file)
        setDataFiles(prev => ({ ...prev, active: file }))
        await loadInitData()
        setRunStatus({ message: '', type: '' })
    }

    function updateField(key, value, save) {
        setSettings(prev => {
            const next = { ...prev, [key]: value }
            if (save) {
                postSettings(next).catch(() => {})
            }
            return next
        })
    }

    async function handleRunColor() {
        setColorRunStatus({ message: 'Sequenciando cores...', type: '' })
        try {
            const result = await runColor(settings.color_method)
            setColorResult(result)
            setColorRunStatus({
                message: `${result.status} — ${result.method === 'milp' ? 'Modelo matemático' : 'Heurística'}`,
                type: 'success'
            })
        } catch (err) {
            setColorRunStatus({ message: `Erro: ${err.message}`, type: 'danger' })
        }
    }

    async function handleRun() {
        if (settings.end_period && settings.end_period < settings.start_period) {
            setRunStatus({ message: 'Data de fim deve ser posterior ao início.', type: 'danger' })
        } else if (!settings.active_machines.length) {
            setRunStatus({ message: 'Selecione ao menos uma máquina.', type: 'danger' })
        } else {
            setIsRunning(true)
            setRunStatus({ message: 'Processando...', type: '' })
            try {
                const result = await runTactical(settings, scenarioLabel.trim())
                const statusLabel = result.status === 'Optimal' ? 'Ótimo' : 'Viável'
                setRunStatus({
                    message: `${statusLabel} — ${settings.solver_name || 'CBC'}`,
                    type: result.status === 'Optimal' ? 'success' : 'warning'
                })
                setTacticalResult(result)
                setActiveTab('results')
                handleRunColor()
            } catch (err) {
                setRunStatus({ message: `Erro: ${err.message}`, type: 'danger' })
            } finally {
                setIsRunning(false)
            }
        }
    }

    async function loadHistory() {
        try {
            const runs = await getHistory()
            setHistoryRuns(runs)
        } catch (err) {
            setHistoryRuns([])
        }
    }

    async function loadRunIntoResults(runId) {
        try {
            const record = await getHistoryRun(runId)
            if (record?.result) {
                setTacticalResult({
                    ...record.result,
                    kpis: record.kpis,
                    duration_seconds: record.duration_seconds,
                    data_file: record.data_file,
                    run_id: record.id
                })
                if (record.color_result) {
                    setColorResult({
                        ...record.color_result,
                        kpis: record.color_kpis,
                        duration_seconds: record.color_duration_seconds
                    })
                    setColorRunStatus({
                        message: `${record.color_result.status} — ${record.color_result.method === 'milp' ? 'Modelo matemático' : 'Heurística'}`,
                        type: 'success'
                    })
                } else {
                    setColorResult(null)
                    setColorRunStatus({ message: '', type: '' })
                }
                setActiveTab('results')
            }
        } catch (err) {
            console.error('Erro ao carregar cenário:', err)
        }
    }

    const kpiItems = [
        { label: 'Custo Total', value: tacticalResult?.kpis?.total_cost != null ? 'R$ ' + tacticalResult.kpis.total_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : null },
        { label: 'Nível de Serviço', value: tacticalResult?.kpis?.service_level != null ? tacticalResult.kpis.service_level.toFixed(1) + '%' : null },
        { label: 'Estoque Médio', value: tacticalResult?.kpis?.avg_inventory != null ? tacticalResult.kpis.avg_inventory.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' Kg' : null },
        { label: 'Tempo de Execução', value: tacticalResult?.duration_seconds != null ? tacticalResult.duration_seconds.toFixed(1) + ' s' : null },
        { label: 'Input', value: tacticalResult?.data_file, small: true }
    ]

    return (
        <div className="app-shell">
            <Sidebar
                settings={settings}
                updateField={updateField}
                machines={machines}
                periods={periods}
                dataFiles={dataFiles}
                onSelectFile={handleSelectFile}
                scenarioLabel={scenarioLabel}
                setScenarioLabel={setScenarioLabel}
                onRun={handleRun}
                isRunning={isRunning}
                runStatus={runStatus}
            />

            <main className="main-content">
                <div className="main-header">
                    <h1>Dimensionamento de Lotes</h1>
                </div>

                {tacticalResult && <KpiBar items={kpiItems} />}

                <ul className="nav nav-tabs main-tabs" role="tablist">
                    <li className="nav-item">
                        <button className={activeTab === 'results' ? 'nav-link active' : 'nav-link'} onClick={() => setActiveTab('results')}>Planejamento Tático</button>
                    </li>
                    <li className="nav-item">
                        <button className={activeTab === 'colors' ? 'nav-link active' : 'nav-link'} onClick={() => setActiveTab('colors')}>Sequenciamento de Cores</button>
                    </li>
                    <li className="nav-item">
                        <button
                            className={activeTab === 'comparison' ? 'nav-link active' : 'nav-link'}
                            onClick={() => { setActiveTab('comparison'); loadHistory() }}
                        >Comparação de Cenários</button>
                    </li>
                </ul>

                <div className="tab-content main-tab-content">
                    {activeTab === 'results' && <TacticalTab result={tacticalResult} />}
                    {activeTab === 'colors' && <ColorTab result={colorResult} statusMessage={colorRunStatus.message} statusType={colorRunStatus.type} />}
                    {activeTab === 'comparison' && <ComparisonTab runs={historyRuns} onRefresh={loadHistory} onSelectRun={loadRunIntoResults} />}
                </div>
            </main>
        </div>
    )
}
