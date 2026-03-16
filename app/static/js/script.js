/**
 * Riberball Production Planning - Main Frontend Script
 * Subperíodos diários, operadores indexados, férias sequenciais.
 */

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initInputs();
    initDataLoading();
    initActionButtons();
});

// --- State Management ---
const AppState = {
    charts: {
        inventory: null,
        production: null,
        demand: null,
        vacations: null
    },
    data: {
        summary: [],
        production: [],
        setups: [],
        vacations: [],
        machine_stops: []
    }
};

// Intervalos de parada por máquina: {machine: [{start: "YYYY-MM-DD", end: "YYYY-MM-DD"}, ...]}
const _machineStopRanges = {};

// --- Initialization Functions ---

function initTabs() {
    document.querySelectorAll('.tab-link').forEach(link => {
        link.addEventListener('click', () => switchTab(link, '.tab-link', '.tab-content', 'data-tab'));
    });
    document.querySelectorAll('.sub-tab-link').forEach(link => {
        link.addEventListener('click', () => switchTab(link, '.sub-tab-link', '.sub-tab-content', 'data-sub'));
    });
}

function switchTab(clickedLink, linkClass, contentClass, dataAttr) {
    const targetId = clickedLink.getAttribute(dataAttr);
    document.querySelectorAll(linkClass).forEach(el => el.classList.remove('active'));
    document.querySelectorAll(contentClass).forEach(el => el.classList.remove('active'));
    clickedLink.classList.add('active');
    const targetContent = document.getElementById(targetId);
    if (targetContent) targetContent.classList.add('active');
}

function initInputs() {
    const inputsToWatch = [
        'start-period', 'end-period',
        'shifts-per-day', 'hours-per-shift', 'days-per-week',
        'decision-type', 'bucket-hours', 'coverage-months',
        'solver-select', 'time-limit',
        'operators-per-machine', 'total-operators', 'operators-on-vacation', 'vacation-days'
    ];

    inputsToWatch.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveSettingsState);
    });

    ['shifts-per-day', 'hours-per-shift', 'days-per-week'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateCapacityDisplay);
    });

    const decisionTypeEl = document.getElementById('decision-type');
    if (decisionTypeEl) {
        decisionTypeEl.addEventListener('change', (e) => {
            const bucketGroup = document.getElementById('bucket-hours-group');
            if (bucketGroup) bucketGroup.style.display = (e.target.value === 'hours') ? 'block' : 'none';
            saveSettingsState();
        });
    }

    const opPerMachine = document.getElementById('operators-per-machine');
    if (opPerMachine) {
        opPerMachine.addEventListener('input', recalcTotalOperators);
    }
}

function recalcTotalOperators() {
    const opPerMachine = parseInt(document.getElementById('operators-per-machine')?.value) || 1;
    const activeMachines = document.querySelectorAll('.machine-box.active').length;
    const totalEl = document.getElementById('total-operators');
    if (totalEl) totalEl.value = activeMachines * opPerMachine;
    saveSettingsState();
}

function initDataLoading() {
    fetchInitData();
}

function initActionButtons() {
    document.getElementById('btn-run').addEventListener('click', handleRunOptimization);

    const btnSummary = document.getElementById('btn-download-summary');
    if (btnSummary) btnSummary.addEventListener('click', downloadSummaryCSV);

    const btnDetailed = document.getElementById('btn-download-detailed');
    if (btnDetailed) btnDetailed.addEventListener('click', downloadDetailedCSV);

    const btnSetups = document.getElementById('btn-download-setups');
    if (btnSetups) btnSetups.addEventListener('click', downloadSetupsCSV);

    const btnVacations = document.getElementById('btn-download-vacations');
    if (btnVacations) btnVacations.addEventListener('click', downloadVacationsCSV);
}

// --- Logic & API Calls ---

async function fetchInitData() {
    try {
        const response = await fetch('/api/init-data');
        const data = await response.json();

        setupDateInputs(data.periods);
        setupMachineGrid(data.machines);
        loadSettingsState();

    } catch (error) {
        console.error('Error loading init data:', error);
        updateStatus('Erro ao carregar dados iniciais.', 'red');
    }
}

function setupDateInputs(periods) {
    const validDates = periods.map(p => p.split(' ')[0]).sort();
    const startInput = document.getElementById('start-period');
    const endInput = document.getElementById('end-period');

    if (validDates.length > 0) {
        startInput.min = validDates[0];
        startInput.max = validDates[validDates.length - 1];
        endInput.min = validDates[0];

        if (!startInput.value) startInput.value = validDates[0];
        if (!endInput.value) endInput.value = validDates[validDates.length - 1];
    }
}

const CALENDAR_SVG = `<svg class="machine-calendar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`;

function setupMachineGrid(machines) {
    const machineGrid = document.getElementById('machine-list');
    machineGrid.innerHTML = '';

    machines.forEach(m => {
        const div = document.createElement('div');
        div.className = 'machine-box active';
        div.dataset.machine = m;
        div.innerHTML = `<span>M${m}</span>${CALENDAR_SVG}`;

        const textSpan = div.querySelector('span');
        const calIcon = div.querySelector('.machine-calendar-icon');

        div.addEventListener('click', (e) => {
            if (e.target.closest('.machine-calendar-icon') || e.target.closest('.machine-stops-popover')) return;
            div.classList.toggle('active');
            closeAllPopovers();
            recalcTotalOperators();
            saveSettingsState();
        });

        calIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleStopsPopover(div, m);
        });

        machineGrid.appendChild(div);
    });

    recalcTotalOperators();
}

function countRangeDays(start, end) {
    const s = new Date(start + 'T00:00:00');
    const e = new Date(end + 'T00:00:00');
    if (isNaN(s) || isNaN(e) || e < s) return 0;
    return Math.round((e - s) / 86400000) + 1;
}

function totalStopDays(machine) {
    const ranges = _machineStopRanges[machine] || [];
    return ranges.reduce((sum, r) => sum + countRangeDays(r.start, r.end), 0);
}

function getHorizonDates() {
    const s = document.getElementById('start-period')?.value || '';
    const e = document.getElementById('end-period')?.value || '';
    return { min: s, max: e };
}

function toggleStopsPopover(machineDiv, machine) {
    let popover = machineDiv.querySelector('.machine-stops-popover');
    if (popover) {
        popover.remove();
        return;
    }

    closeAllPopovers();

    popover = document.createElement('div');
    popover.className = 'machine-stops-popover';
    popover.addEventListener('click', (e) => e.stopPropagation());

    const horizon = getHorizonDates();
    const ranges = _machineStopRanges[machine] || [];
    const total = totalStopDays(machine);

    popover.innerHTML = `
        <div class="popover-title">Paradas — M${machine}</div>
        <div class="popover-form">
            <div class="popover-row">
                <label>Início</label>
                <input type="date" class="stop-start" ${horizon.min ? `min="${horizon.min}"` : ''} ${horizon.max ? `max="${horizon.max}"` : ''}>
            </div>
            <div class="popover-row">
                <label>Fim</label>
                <input type="date" class="stop-end" ${horizon.min ? `min="${horizon.min}"` : ''} ${horizon.max ? `max="${horizon.max}"` : ''}>
            </div>
            <button class="btn-add-range" type="button">+ Adicionar</button>
        </div>
        <div class="popover-ranges-list"></div>
        <div class="popover-hint">${total} dias parados no horizonte</div>
    `;

    const startInput = popover.querySelector('.stop-start');
    const endInput = popover.querySelector('.stop-end');
    const btnAdd = popover.querySelector('.btn-add-range');
    const listDiv = popover.querySelector('.popover-ranges-list');
    const hint = popover.querySelector('.popover-hint');

    function renderRangeList() {
        const currentRanges = _machineStopRanges[machine] || [];
        listDiv.innerHTML = '';
        currentRanges.forEach((r, idx) => {
            const days = countRangeDays(r.start, r.end);
            const item = document.createElement('div');
            item.className = 'popover-range-item';
            item.innerHTML = `
                <span>${formatDateShort(r.start)} — ${formatDateShort(r.end)} <em>(${days}d)</em></span>
                <button class="btn-remove-range" data-idx="${idx}" title="Remover">&times;</button>
            `;
            item.querySelector('.btn-remove-range').addEventListener('click', (e) => {
                e.stopPropagation();
                currentRanges.splice(idx, 1);
                if (currentRanges.length === 0) delete _machineStopRanges[machine];
                refreshAfterChange();
            });
            listDiv.appendChild(item);
        });
    }

    function refreshAfterChange() {
        const t = totalStopDays(machine);
        hint.textContent = `${t} dias parados no horizonte`;
        updateMachineBoxColor(machineDiv, t);
        renderRangeList();
        saveSettingsState();
    }

    btnAdd.addEventListener('click', () => {
        const s = startInput.value;
        const e = endInput.value;
        if (!s || !e) return;
        if (e < s) { startInput.value = e; endInput.value = s; return; }
        if (!_machineStopRanges[machine]) _machineStopRanges[machine] = [];
        _machineStopRanges[machine].push({ start: s, end: e });
        startInput.value = '';
        endInput.value = '';
        refreshAfterChange();
    });

    renderRangeList();
    machineDiv.appendChild(popover);
    startInput.focus();
}

function formatDateShort(isoDate) {
    const parts = isoDate.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
    return isoDate;
}

function closeAllPopovers() {
    document.querySelectorAll('.machine-stops-popover').forEach(p => p.remove());
}

function updateMachineBoxColor(div, stopDays) {
    if (!div.classList.contains('active')) return;
    if (stopDays > 0) {
        div.classList.add('has-stops');
    } else {
        div.classList.remove('has-stops');
    }
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.machine-box')) {
        closeAllPopovers();
    }
});

async function handleRunOptimization() {
    const btn = document.getElementById('btn-run');
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = 'Calculando...';
    updateStatus('Processando otimização...', '#333');
    updateCostDisplay('');

    const payload = buildRunPayload();
    if (!validatePayload(payload)) {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = 'Executar Planejamento';
        return;
    }

    saveSettingsState();

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3600000);

        const response = await fetch('/api/run?t=' + Date.now(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }

        const result = await response.json();

        const validStatuses = ['Optimal', 'Feasible'];
        if (validStatuses.includes(result.status)) {
            const solverUsed = payload.solver_name || 'CBC';
            const statusLabel = result.status === 'Feasible'
                ? 'Solução viável (limite de tempo atingido)'
                : 'Otimização concluída';
            updateStatus(`${statusLabel} — Solver: ${solverUsed}`, result.status === 'Optimal' ? 'green' : 'darkorange');
            if (result.kpis && result.kpis.total_cost !== undefined) {
                updateCostDisplay(result.kpis.total_cost);
            }
            renderResults(result);

            const summaryTabLink = document.querySelector('.tab-link[data-tab="tab-summary"]');
            if (summaryTabLink) summaryTabLink.click();
        } else {
            updateStatus(`Erro/Status: ${result.status || result.message}`, 'red');
        }

    } catch (error) {
        console.error(error);
        if (error.name === 'AbortError') {
            updateStatus('Tempo limite excedido. O cálculo está demorando muito.', 'red');
        } else {
            updateStatus(`Erro de comunicação: ${error.message}`, 'red');
        }
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = 'Executar Planejamento';
    }
}

function buildRunPayload() {
    const getVal = (id) => document.getElementById(id)?.value || '';

    return {
        start_period: getVal('start-period') + " 00:00:00",
        end_period: getVal('end-period') ? getVal('end-period') + " 00:00:00" : null,
        active_machines: Array.from(document.querySelectorAll('.machine-box.active')).map(el => el.dataset.machine),
        coverage_months: getVal('coverage-months'),
        decision_type: getVal('decision-type'),
        bucket_hours: getVal('bucket-hours'),
        solver_name: getVal('solver-select'),
        time_limit: parseInt(getVal('time-limit')) || 600,
        capacity_params: {
            shifts_per_day: getVal('shifts-per-day'),
            hours_per_shift: getVal('hours-per-shift'),
            days_per_week: getVal('days-per-week')
        },
        manual_stops_ranges: JSON.parse(JSON.stringify(_machineStopRanges)),
        num_operators: parseInt(getVal('total-operators')) || 0,
        operators_per_machine: parseInt(getVal('operators-per-machine')) || 1,
        num_operators_on_vacation: parseInt(getVal('operators-on-vacation')) || 0,
        vacation_days: parseInt(getVal('vacation-days')) || 0
    };
}

function validatePayload(payload) {
    if (payload.end_period && payload.end_period < payload.start_period) {
        updateStatus('A data de fim deve ser posterior à data de início.', 'red');
        return false;
    }
    if (payload.active_machines.length === 0) {
        updateStatus('Selecione ao menos uma máquina.', 'red');
        return false;
    }
    return true;
}

// --- UI Helpers ---

function updateStatus(msg, color) {
    const el = document.getElementById('status-msg');
    if (el) {
        el.textContent = msg;
        el.style.color = color;
    }
}

function updateCostDisplay(cost) {
    const el = document.getElementById('cost-msg');
    if (!el) return;

    if (cost === '') {
        el.textContent = '';
    } else {
        el.textContent = 'Custo Total da Solução: R$ ' + cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 });
    }
}

function updateCapacityDisplay() {
    const shifts = parseFloat(document.getElementById('shifts-per-day').value) || 0;
    const hours = parseFloat(document.getElementById('hours-per-shift').value) || 0;
    const days = parseFloat(document.getElementById('days-per-week').value) || 0;
    const total = shifts * hours * days * 4.33;
    document.getElementById('total-hours-display').value = total.toFixed(2);
}

// --- Persistence ---

function saveSettingsState() {
    const state = {
        startPeriod: document.getElementById('start-period').value,
        endPeriod: document.getElementById('end-period').value,
        coverageMonths: document.getElementById('coverage-months').value,
        shiftsPerDay: document.getElementById('shifts-per-day').value,
        hoursPerShift: document.getElementById('hours-per-shift').value,
        daysPerWeek: document.getElementById('days-per-week').value,
        decisionType: document.getElementById('decision-type').value,
        bucketHours: document.getElementById('bucket-hours').value,
        solverName: document.getElementById('solver-select').value,
        timeLimit: document.getElementById('time-limit').value,
        activeMachines: Array.from(document.querySelectorAll('.machine-box.active')).map(el => el.dataset.machine),
        machineStopRanges: JSON.parse(JSON.stringify(_machineStopRanges)),
        operatorsPerMachine: document.getElementById('operators-per-machine')?.value,
        totalOperators: document.getElementById('total-operators')?.value,
        operatorsOnVacation: document.getElementById('operators-on-vacation')?.value,
        vacationDays: document.getElementById('vacation-days')?.value
    };
    localStorage.setItem('riberball_settings', JSON.stringify(state));
}

function loadSettingsState() {
    const saved = localStorage.getItem('riberball_settings');
    if (!saved) return;

    try {
        const state = JSON.parse(saved);
        const setVal = (id, val) => {
            if (val !== undefined && val !== null) {
                const el = document.getElementById(id);
                if (el) el.value = val;
            }
        };

        setVal('start-period', state.startPeriod);
        setVal('end-period', state.endPeriod);
        setVal('coverage-months', state.coverageMonths);
        setVal('shifts-per-day', state.shiftsPerDay);
        setVal('hours-per-shift', state.hoursPerShift);
        setVal('days-per-week', state.daysPerWeek);
        setVal('bucket-hours', state.bucketHours);
        setVal('time-limit', state.timeLimit);
        setVal('operators-per-machine', state.operatorsPerMachine);
        setVal('total-operators', state.totalOperators);
        setVal('operators-on-vacation', state.operatorsOnVacation);
        setVal('vacation-days', state.vacationDays);

        if (state.solverName) document.getElementById('solver-select').value = state.solverName;

        if (state.decisionType) {
            const el = document.getElementById('decision-type');
            el.value = state.decisionType;
            el.dispatchEvent(new Event('change'));
        }

        updateCapacityDisplay();

        if (state.activeMachines) {
            document.querySelectorAll('.machine-box').forEach(el => {
                el.classList.toggle('active', state.activeMachines.includes(el.dataset.machine));
            });
        }

        if (state.machineStopRanges) {
            Object.keys(_machineStopRanges).forEach(k => delete _machineStopRanges[k]);
            Object.entries(state.machineStopRanges).forEach(([machine, ranges]) => {
                _machineStopRanges[machine] = ranges;
                const box = document.querySelector(`.machine-box[data-machine="${machine}"]`);
                if (box) updateMachineBoxColor(box, totalStopDays(machine));
            });
        }
    } catch (e) {
        console.error("Error parsing saved state", e);
    }
}

// --- Rendering & Charts ---

function renderResults(data) {
    AppState.data.summary = data.summary || [];
    AppState.data.production = data.production || [];
    AppState.data.setups = data.setups || [];
    AppState.data.vacations = data.vacations || [];
    AppState.data.machine_stops = data.machine_stops || [];

    renderCharts(data);
    renderSummaryTable(AppState.data.summary);
    renderDetailedTable(AppState.data.production);
    renderSetupsTable(AppState.data.setups);
    renderVacationsTable(AppState.data.vacations);
}

function renderCharts(data) {
    renderInventoryChart(data.inventory);
    renderProductionChart(data.production);
    renderDemandChart(data.demand);
    renderVacationsChart(data.machine_stops);
}

function renderVacationsChart(machineStops) {
    let periods = [];
    if (AppState.data.summary && AppState.data.summary.length > 0) {
        periods = AppState.data.summary.map(s => s.Period).sort();
    }

    if (periods.length === 0) return;

    const displayPeriods = periods.map(p => formatDate(p));

    const daysByPeriod = {};
    periods.forEach(p => daysByPeriod[p] = 0);

    if (machineStops) {
        machineStops.forEach(r => {
            if (daysByPeriod.hasOwnProperty(r.Period)) {
                daysByPeriod[r.Period] += r.DaysStopped;
            }
        });
    }

    const ctx = document.getElementById('vacationsChart');
    if (!ctx) return;

    if (AppState.charts.vacations) AppState.charts.vacations.destroy();

    AppState.charts.vacations = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: displayPeriods,
            datasets: [{
                label: 'Dias de Parada (todas as máquinas)',
                data: periods.map(p => daysByPeriod[p]),
                backgroundColor: 'orange',
                borderColor: 'darkorange',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Dias de Parada' }
                }
            }
        }
    });
}

function renderInventoryChart(inventoryData) {
    const periods = [...new Set(inventoryData.map(d => d.Period))].sort();
    const displayPeriods = periods.map(p => formatDate(p));

    const invByPeriod = {};
    periods.forEach(p => { invByPeriod[p] = 0; });
    inventoryData.forEach(r => { invByPeriod[r.Period] += r.Inventory; });

    const ctx = document.getElementById('inventoryChart');
    if (AppState.charts.inventory) AppState.charts.inventory.destroy();

    AppState.charts.inventory = new Chart(ctx, {
        type: 'line',
        data: {
            labels: displayPeriods,
            datasets: [{
                label: 'Estoque Total (Kg)',
                data: periods.map(p => invByPeriod[p]),
                borderColor: 'blue',
                fill: false
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0 } } }
    });
}

function renderProductionChart(prodData) {
    const periods = [...new Set(prodData.map(d => d.Period))].sort();
    const displayPeriods = periods.map(p => formatDate(p));
    const allMachines = [...new Set(prodData.map(d => d.Machine))].sort((a, b) => (parseInt(a) || 0) - (parseInt(b) || 0));

    const palette = [
        '#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed',
        '#0891b2', '#be185d', '#65a30d', '#ea580c', '#6366f1',
        '#0f766e', '#b45309', '#9333ea', '#0284c7', '#15803d',
        '#c2410c', '#4338ca', '#0e7490', '#a21caf', '#854d0e',
        '#1d4ed8', '#166534', '#991b1b', '#92400e', '#5b21b6'
    ];
    const colorOf = (m) => palette[allMachines.indexOf(m) % palette.length];

    const checkboxContainer = document.getElementById('production-machine-checkboxes');
    const btnAll = document.getElementById('btn-filter-all');

    if (checkboxContainer) {
        checkboxContainer.innerHTML = '';
        allMachines.forEach(m => {
            const chip = document.createElement('label');
            chip.className = 'machine-filter-chip';
            chip.title = `Máquina ${m}`;

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = m;

            chip.appendChild(cb);
            chip.appendChild(document.createTextNode(`M${m}`));

            chip.addEventListener('click', () => {
                cb.checked = !cb.checked;
                chip.classList.toggle('selected', cb.checked);
                _updateProductionFilter();
            });

            checkboxContainer.appendChild(chip);
        });
    }

    if (btnAll) {
        btnAll.onclick = () => {
            checkboxContainer.querySelectorAll('.machine-filter-chip').forEach(c => {
                c.classList.remove('selected');
                c.querySelector('input').checked = false;
            });
            btnAll.classList.add('active');
            _drawAggregated();
        };
    }

    _drawAggregated();

    function _updateProductionFilter() {
        const checked = [...checkboxContainer.querySelectorAll('input:checked')].map(c => c.value);
        btnAll.classList.toggle('active', checked.length === 0);
        if (checked.length === 0) {
            _drawAggregated();
        } else {
            _drawByMachine(checked);
        }
    }

    function _drawAggregated() {
        const totals = periods.map(p =>
            prodData.filter(x => x.Period === p).reduce((s, x) => s + x.Quantity, 0)
        );
        _renderChart(
            [{ label: 'Produção Total', data: totals, backgroundColor: '#2563eb' }],
            false
        );
    }

    function _drawByMachine(machines) {
        const datasets = machines.map(m => ({
            label: `M${m}`,
            data: periods.map(p =>
                prodData.filter(x => x.Period === p && x.Machine === m)
                    .reduce((s, x) => s + x.Quantity, 0)
            ),
            backgroundColor: colorOf(m)
        }));
        _renderChart(datasets, true);
    }

    function _renderChart(datasets, stacked) {
        const ctx = document.getElementById('productionChart');
        if (AppState.charts.production) AppState.charts.production.destroy();

        AppState.charts.production = new Chart(ctx, {
            type: 'bar',
            data: { labels: displayPeriods, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: stacked,
                        position: 'bottom',
                        labels: { boxWidth: 12, font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            footer: stacked
                                ? (items) => `Total: ${items.reduce((s, i) => s + i.parsed.y, 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} Kg`
                                : undefined
                        }
                    }
                },
                scales: {
                    x: { stacked },
                    y: { stacked, title: { display: true, text: 'Kg' } }
                }
            }
        });
    }
}

function renderDemandChart(demandData) {
    const periods = [...new Set(demandData.map(d => d.Period))].sort();
    const displayPeriods = periods.map(p => formatDate(p));

    const metrics = { demand: {}, met: {}, lost: {} };
    periods.forEach(p => { for (let k in metrics) metrics[k][p] = 0; });

    demandData.forEach(r => {
        metrics.demand[r.Period] += r.Demand;
        metrics.met[r.Period] += r.Met;
        metrics.lost[r.Period] += r.Lost;
    });

    const ctx = document.getElementById('demandChart');
    if (AppState.charts.demand) AppState.charts.demand.destroy();

    AppState.charts.demand = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: displayPeriods,
            datasets: [
                { label: 'Atendida', data: periods.map(p => metrics.met[p]), backgroundColor: 'green' },
                { label: 'Perdida', data: periods.map(p => metrics.lost[p]), backgroundColor: 'red' },
                { type: 'line', label: 'Demanda Total', data: periods.map(p => metrics.demand[p]), borderColor: 'black', borderWidth: 2 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { stacked: true }, y: { stacked: true } }
        }
    });
}

function renderSummaryTable(data) {
    const tbody = document.getElementById('summary-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding: 20px; text-align: center;">Nenhum dado disponível.</td></tr>';
        return;
    }

    data.sort((a, b) => a.Period.localeCompare(b.Period));

    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(row.Period)}</td>
            <td class="text-right">${fmtNumber(row.Inventory, 0)}</td>
            <td class="text-right">${(row.Utilization * 100).toFixed(1)}%</td>
            <td class="text-right">${fmtNumber(row.Demand, 0)}</td>
            <td class="text-right">${fmtNumber(row.Lost, 0)}</td>
            <td class="text-right">${fmtNumber(row.Production, 0)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderDetailedTable(data) {
    const tbody = document.getElementById('detailed-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding: 20px; text-align: center;">Nenhum dado disponível.</td></tr>';
        return;
    }

    data.sort((a, b) => {
        if (a.Period !== b.Period) return a.Period.localeCompare(b.Period);
        const mA = parseInt(a.Machine) || 0;
        const mB = parseInt(b.Machine) || 0;
        if (mA !== mB) return mA - mB;
        return a.Product.localeCompare(b.Product);
    });

    data.forEach(row => {
        const tr = document.createElement('tr');
        const daysProd = row.Hours / 24.0;
        tr.innerHTML = `
            <td>${formatDate(row.Period)}</td>
            <td>M${row.Machine}</td>
            <td>${row.Product}</td>
            <td class="text-right">${row.Hours.toFixed(1)}h</td>
            <td class="text-right">${daysProd.toFixed(1)}d</td>
            <td class="text-right">${fmtNumber(row.Quantity, 2)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderSetupsTable(data) {
    const tbody = document.getElementById('setups-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center;">Nenhum setup registrado.</td></tr>';
        return;
    }

    data.sort((a, b) => {
        if (a.Period !== b.Period) return a.Period.localeCompare(b.Period);
        return (parseInt(a.Machine) || 0) - (parseInt(b.Machine) || 0);
    });

    data.forEach(row => {
        const tr = document.createElement('tr');
        const cost = row.Cost !== undefined ? fmtNumber(row.Cost, 2) : '-';
        tr.innerHTML = `
            <td>${formatDate(row.Period)}</td>
            <td>M${row.Machine}</td>
            <td>${row.From}</td>
            <td>${row.To}</td>
            <td class="text-right">R$ ${cost}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderVacationsTable(data) {
    const tbody = document.getElementById('vacations-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center;">Nenhuma férias programada.</td></tr>';
        return;
    }

    data.sort((a, b) => a.Operator - b.Operator);

    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>Operador ${row.Operator}</td>
            <td>Dia ${row.StartDay}</td>
            <td>Dia ${row.EndDay}</td>
            <td class="text-right">${row.Days}</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- CSV Export ---

function downloadSummaryCSV() {
    downloadCSV(AppState.data.summary, ["Mês", "Estoque", "Utilização", "Demanda", "Perda", "Produzido"], row => [
        formatDate(row.Period),
        fmtNumberCSV(row.Inventory),
        fmtNumberCSV(row.Utilization * 100),
        fmtNumberCSV(row.Demand),
        fmtNumberCSV(row.Lost),
        fmtNumberCSV(row.Production)
    ], "resumo_mensal.csv");
}

function downloadDetailedCSV() {
    downloadCSV(AppState.data.production, ["Período", "Máquina", "Produto", "Horas", "Dias", "Quantidade"], row => [
        formatDate(row.Period),
        `M${row.Machine}`,
        row.Product,
        fmtNumberCSV(row.Hours),
        fmtNumberCSV(row.Hours / 24.0),
        fmtNumberCSV(row.Quantity)
    ], "producao_detalhada.csv");
}

function downloadSetupsCSV() {
    downloadCSV(AppState.data.setups, ["Período", "Máquina", "De", "Para", "Custo (R$)"], row => [
        formatDate(row.Period),
        `M${row.Machine}`,
        row.From,
        row.To,
        fmtNumberCSV(row.Cost || 0)
    ], "setups_detalhado.csv");
}

function downloadVacationsCSV() {
    downloadCSV(AppState.data.vacations, ["Operador", "Início", "Fim", "Dias"], row => [
        `Operador ${row.Operator}`,
        `Dia ${row.StartDay}`,
        `Dia ${row.EndDay}`,
        row.Days
    ], "ferias_operadores.csv");
}

function downloadCSV(data, headers, rowMapper, filename) {
    if (!data || data.length === 0) {
        alert("Não há dados para exportar.");
        return;
    }

    let csv = "\uFEFF" + headers.join(";") + "\n";
    data.forEach(row => {
        csv += rowMapper(row).join(";") + "\n";
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = filename;
    link.click();
}

// --- Formatters ---

function formatDate(isoDate) {
    const cleanDate = isoDate.split(' ')[0];
    const parts = cleanDate.split('-');

    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    if (parts.length === 2) {
        return `${parts[1]}/${parts[0]}`;
    }
    return isoDate;
}

function fmtNumber(val, digits) {
    return val.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtNumberCSV(val) {
    return val.toFixed(2).replace('.', ',');
}
