import { formatDate } from '../../lib/format.js'

const PRODUCTION_PALETTE = [
    '#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed',
    '#0891b2', '#be185d', '#65a30d', '#ea580c', '#6366f1',
    '#0f766e', '#b45309', '#9333ea', '#0284c7', '#15803d'
]

export function buildInventoryChartConfig(inventoryData) {
    const periods = [...new Set(inventoryData.map(d => d.Period))].sort()
    const totals = {}
    periods.forEach(p => { totals[p] = 0 })
    inventoryData.forEach(r => { totals[r.Period] += r.Inventory })

    return {
        type: 'line',
        data: {
            labels: periods.map(formatDate),
            datasets: [{ label: 'Estoque (Kg)', data: periods.map(p => totals[p]), borderColor: '#00215D', fill: false, tension: 0.2 }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0 } }, plugins: { legend: { display: false } } }
    }
}

export function buildDemandChartConfig(demandData) {
    const periods = [...new Set(demandData.map(d => d.Period))].sort()
    const met = {}, lost = {}, total = {}
    periods.forEach(p => { met[p] = 0; lost[p] = 0; total[p] = 0 })
    demandData.forEach(r => { met[r.Period] += r.Met; lost[r.Period] += r.Lost; total[r.Period] += r.Demand })

    return {
        type: 'bar',
        data: {
            labels: periods.map(formatDate),
            datasets: [
                { label: 'Atendida', data: periods.map(p => met[p]), backgroundColor: '#198754' },
                { label: 'Perdida', data: periods.map(p => lost[p]), backgroundColor: '#dc3545' },
                { type: 'line', label: 'Total', data: periods.map(p => total[p]), borderColor: '#000', borderWidth: 2, pointRadius: 0 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } } }
    }
}

export function getProductionMachines(prodData) {
    return [...new Set(prodData.map(d => d.Machine))].sort((a, b) => (parseInt(a) || 0) - (parseInt(b) || 0))
}

export function buildProductionChartConfig(prodData, selectedMachines) {
    const periods = [...new Set(prodData.map(d => d.Period))].sort()
    const allMachines = getProductionMachines(prodData)
    const colorOf = machine => PRODUCTION_PALETTE[allMachines.indexOf(machine) % PRODUCTION_PALETTE.length]

    let datasets
    let stacked
    if (selectedMachines.length === 0) {
        datasets = [{
            label: 'Total',
            data: periods.map(p => prodData.filter(x => x.Period === p).reduce((s, x) => s + x.Kg, 0)),
            backgroundColor: '#2563eb'
        }]
        stacked = false
    } else {
        datasets = selectedMachines.map(machine => ({
            label: `M${machine}`,
            data: periods.map(p => prodData.filter(x => x.Period === p && x.Machine === machine).reduce((s, x) => s + x.Kg, 0)),
            backgroundColor: colorOf(machine)
        }))
        stacked = true
    }

    return {
        type: 'bar',
        data: { labels: periods.map(formatDate), datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: stacked, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
            scales: { x: { stacked }, y: { stacked, title: { display: true, text: 'Kg' } } }
        }
    }
}
