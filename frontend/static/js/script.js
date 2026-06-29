/**
 * Riberball — Planejamento de Produção
 * Controla a sidebar paramétrica, execução do solver, gráficos,
 * tabelas, histórico de execuções e comparação de cenários.
 */

// ── Alpine.js: estado global da shell ────────────────────────────
function appShell() {
    return {
        sidebarOpen: true,
        sec: { horizon: true, capacity: true, machines: true, solver: false },

        init() {
            fetchInitData();
            initCapacityWatch();
            initActionButtons();
        }
    };
}

// ── Estado da aplicação ──────────────────────────────────────────
const AppState = {
    charts: { inventory: null, production: null, demand: null },
    data:   { summary: [], production: [], setups: [], machine_stops: [] }
};

// Intervalos de parada: {machine: [{start, end}, ...]}
const _machineStopRanges = {};

// ── Inicialização ────────────────────────────────────────────────

function initCapacityWatch() {
    ['shifts-per-day', 'hours-per-shift', 'days-per-week'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateCapacityDisplay);
    });

    const settingIds = [
        'start-period', 'end-period', 'coverage-months',
        'shifts-per-day', 'hours-per-shift', 'days-per-week',
        'solver-select', 'time-limit',
        'setup-time-high', 'setup-time-low'
    ];
    settingIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveSettingsState);
    });
}

function initActionButtons() {
    document.getElementById('btn-run').addEventListener('click', handleRunOptimization);

    document.getElementById('btn-download-summary')?.addEventListener('click', downloadSummaryCSV);
    document.getElementById('btn-download-detailed')?.addEventListener('click', downloadDetailedCSV);
    document.getElementById('btn-download-setups')?.addEventListener('click', downloadSetupsCSV);
    document.getElementById('btn-refresh-history')?.addEventListener('click', loadHistory);

    // Ao entrar na aba Comparação, atualiza o histórico
    document.getElementById('tab-comparison-btn')?.addEventListener('click', loadHistory);
}

// ── Carga de dados iniciais ──────────────────────────────────────

async function fetchInitData() {
    try {
        const resp = await fetch('/api/init-data');
        const data = await resp.json();
        setupDateInputs(data.periods);
        setupMachineGrid(data.machines);
        loadSettingsState();
    } catch (e) {
        setRunStatus('Erro ao carregar dados iniciais.', 'danger');
    }
}

function setupDateInputs(periods) {
    const dates = periods.map(p => p.split(' ')[0]).sort();
    const startEl = document.getElementById('start-period');
    const endEl   = document.getElementById('end-period');
    if (!dates.length) return;
    startEl.min = dates[0];
    startEl.max = dates[dates.length - 1];
    endEl.min   = dates[0];
    if (!startEl.value) startEl.value = dates[0];
    if (!endEl.value)   endEl.value   = dates[dates.length - 1];
}

// ── Grade de máquinas ────────────────────────────────────────────

const CALENDAR_SVG = `<svg class="machine-calendar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`;

function setupMachineGrid(machines) {
    const grid = document.getElementById('machine-list');
    grid.innerHTML = '';

    machines.forEach(m => {
        const box = _createMachineBox(m);
        box.classList.add('active');
        const cal = box.querySelector('.machine-calendar-icon');

        box.addEventListener('click', e => {
            if (e.target.closest('.machine-calendar-icon') || e.target.closest('.machine-stops-popover')) return;
            box.classList.toggle('active');
            closeAllPopovers();
            saveSettingsState();
        });

        cal.addEventListener('click', e => {
            e.stopPropagation();
            toggleStopsPopover(box, m);
        });

        grid.appendChild(box);
    });

    // Grade de setup alto (mesmas máquinas, toggle independente)
    const highGrid = document.getElementById('high-setup-list');
    highGrid.innerHTML = '';
    highGrid.className = 'machine-grid high-setup-grid';
    machines.forEach(m => {
        const box = _createMachineBox(m, false);
        box.addEventListener('click', e => {
            if (e.target.closest('.machine-stops-popover')) return;
            box.classList.toggle('selected');
            saveSettingsState();
        });
        highGrid.appendChild(box);
    });
}

function _createMachineBox(m, withCalendar = true) {
    const box = document.createElement('div');
    box.className = 'machine-box';
    box.dataset.machine = m;
    box.innerHTML = `<span>M${m}</span>${withCalendar ? CALENDAR_SVG : ''}`;
    return box;
}

// ── Popover de paradas ───────────────────────────────────────────

function toggleStopsPopover(machineDiv, machine) {
    const existing = machineDiv.querySelector('.machine-stops-popover');
    if (existing) { existing.remove(); return; }
    closeAllPopovers();

    const popover = document.createElement('div');
    popover.className = 'machine-stops-popover';
    popover.addEventListener('click', e => e.stopPropagation());

    const { min: hMin, max: hMax } = getHorizonDates();
    popover.innerHTML = `
        <div class="popover-title">Paradas — M${machine}</div>
        <div class="popover-form">
            <div class="popover-row">
                <label>Início</label>
                <input type="date" class="stop-start" ${hMin ? `min="${hMin}"` : ''} ${hMax ? `max="${hMax}"` : ''}>
            </div>
            <div class="popover-row">
                <label>Fim</label>
                <input type="date" class="stop-end" ${hMin ? `min="${hMin}"` : ''} ${hMax ? `max="${hMax}"` : ''}>
            </div>
            <button class="btn-add-range" type="button">+ Adicionar</button>
        </div>
        <div class="popover-ranges-list"></div>
        <div class="popover-hint"></div>
    `;

    const startInput = popover.querySelector('.stop-start');
    const endInput   = popover.querySelector('.stop-end');
    const listDiv    = popover.querySelector('.popover-ranges-list');
    const hint       = popover.querySelector('.popover-hint');

    function renderList() {
        const ranges = _machineStopRanges[machine] || [];
        listDiv.innerHTML = '';
        ranges.forEach((r, idx) => {
            const days = countRangeDays(r.start, r.end);
            const item = document.createElement('div');
            item.className = 'popover-range-item';
            item.innerHTML = `<span>${fmt2(r.start)} — ${fmt2(r.end)} <em>(${days}d)</em></span><button class="btn-remove-range" data-idx="${idx}">&times;</button>`;
            item.querySelector('.btn-remove-range').addEventListener('click', e => {
                e.stopPropagation();
                ranges.splice(idx, 1);
                if (!ranges.length) delete _machineStopRanges[machine];
                refresh();
            });
            listDiv.appendChild(item);
        });
        const total = totalStopDays(machine);
        hint.textContent = `${total} dias parados no horizonte`;
        updateMachineBoxColor(machineDiv, total);
    }

    function refresh() { renderList(); saveSettingsState(); }

    popover.querySelector('.btn-add-range').addEventListener('click', () => {
        const s = startInput.value, e = endInput.value;
        if (!s || !e) return;
        if (!_machineStopRanges[machine]) _machineStopRanges[machine] = [];
        const start = s <= e ? s : e;
        const end   = s <= e ? e : s;
        _machineStopRanges[machine].push({ start, end });
        startInput.value = '';
        endInput.value   = '';
        refresh();
    });

    renderList();
    machineDiv.appendChild(popover);
    startInput.focus();
}

function closeAllPopovers() {
    document.querySelectorAll('.machine-stops-popover').forEach(p => p.remove());
}

document.addEventListener('click', e => {
    if (!e.target.closest('.machine-box')) closeAllPopovers();
});

function getHorizonDates() {
    return {
        min: document.getElementById('start-period')?.value || '',
        max: document.getElementById('end-period')?.value   || ''
    };
}

function countRangeDays(start, end) {
    const s = new Date(start + 'T00:00:00');
    const e = new Date(end   + 'T00:00:00');
    if (isNaN(s) || isNaN(e) || e < s) return 0;
    return Math.round((e - s) / 86400000) + 1;
}

function totalStopDays(machine) {
    return (_machineStopRanges[machine] || []).reduce((sum, r) => sum + countRangeDays(r.start, r.end), 0);
}

function updateMachineBoxColor(div, stopDays) {
    if (!div.classList.contains('active')) return;
    div.classList.toggle('has-stops', stopDays > 0);
}

// ── Execução ─────────────────────────────────────────────────────

async function handleRunOptimization() {
    const btn = document.getElementById('btn-run');
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = 'Calculando...';
    setRunStatus('Processando...', '');

    const settings = collectSettings();
    if (!validateSettings(settings)) {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = 'Executar';
        return;
    }

    await saveSettingsState();

    try {
        const label = document.getElementById('scenario-label')?.value?.trim() || '';
        const resp = await fetch('/api/run?t=' + Date.now(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label }),
            signal: AbortSignal.timeout(3_600_000)
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const result = await resp.json();

        if (['Optimal', 'Feasible'].includes(result.status)) {
            const solver = settings.solver_name || 'CBC';
            const label  = result.status === 'Optimal' ? 'Ótimo' : 'Viável';
            setRunStatus(`${label} — ${solver}`, result.status === 'Optimal' ? 'success' : 'warning');
            renderKpis(result.kpis, result.duration_seconds);
            renderResults(result);
            // Redireciona para aba Resultados
            document.querySelector('[data-bs-target="#tab-results"]')?.click();
        } else {
            setRunStatus(`Status: ${result.status || result.message}`, 'danger');
        }
    } catch (err) {
        setRunStatus(`Erro: ${err.message}`, 'danger');
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = 'Executar';
    }
}

// ── Coleta e persistência de configurações ───────────────────────

function collectSettings() {
    const v = id => document.getElementById(id)?.value || '';

    const highSetupMachines = Array.from(
        document.querySelectorAll('#high-setup-list .machine-box.selected')
    ).map(el => el.dataset.machine);

    return {
        start_period:        v('start-period')  ? v('start-period')  + ' 00:00:00' : null,
        end_period:          v('end-period')     ? v('end-period')    + ' 00:00:00' : null,
        coverage_months:     parseInt(v('coverage-months'))  || 0,
        shifts_per_day:      parseFloat(v('shifts-per-day')) || 0,
        hours_per_shift:     parseFloat(v('hours-per-shift'))|| 0,
        days_per_week:       parseFloat(v('days-per-week'))  || 0,
        active_machines:     Array.from(document.querySelectorAll('#machine-list .machine-box.active')).map(el => el.dataset.machine),
        manual_stops_ranges: JSON.parse(JSON.stringify(_machineStopRanges)),
        high_setup_machines: highSetupMachines,
        setup_time_high:     parseFloat(v('setup-time-high')) || 7.0,
        setup_time_low:      parseFloat(v('setup-time-low'))  || 3.0,
        solver_name:         v('solver-select'),
        time_limit:          parseInt(v('time-limit')) || 600
    };
}

function validateSettings(s) {
    if (s.end_period && s.end_period < s.start_period) {
        setRunStatus('Data de fim deve ser posterior ao início.', 'danger');
        return false;
    }
    if (!s.active_machines.length) {
        setRunStatus('Selecione ao menos uma máquina.', 'danger');
        return false;
    }
    return true;
}

async function saveSettingsState() {
    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectSettings())
    });
}

async function loadSettingsState() {
    const resp  = await fetch('/api/settings');
    const state = await resp.json();

    const set = (id, val) => {
        if (val == null) return;
        const el = document.getElementById(id);
        if (el) el.value = val;
    };

    set('start-period',   state.start_period ? state.start_period.split(' ')[0] : null);
    set('end-period',     state.end_period   ? state.end_period.split(' ')[0]   : null);
    set('coverage-months', state.coverage_months);
    set('shifts-per-day',  state.shifts_per_day);
    set('hours-per-shift', state.hours_per_shift);
    set('days-per-week',   state.days_per_week);
    set('solver-select',   state.solver_name);
    set('time-limit',      state.time_limit);
    set('setup-time-high', state.setup_time_high);
    set('setup-time-low',  state.setup_time_low);

    updateCapacityDisplay();

    // Máquinas ativas
    if (state.active_machines?.length) {
        document.querySelectorAll('#machine-list .machine-box').forEach(el => {
            el.classList.toggle('active', state.active_machines.includes(el.dataset.machine));
        });
    }

    // Máquinas de setup alto
    if (state.high_setup_machines?.length) {
        document.querySelectorAll('#high-setup-list .machine-box').forEach(el => {
            el.classList.toggle('selected', state.high_setup_machines.includes(el.dataset.machine));
        });
    }

    // Paradas manuais
    if (state.manual_stops_ranges) {
        Object.keys(_machineStopRanges).forEach(k => delete _machineStopRanges[k]);
        Object.entries(state.manual_stops_ranges).forEach(([m, ranges]) => {
            _machineStopRanges[m] = ranges;
            const box = document.querySelector(`#machine-list .machine-box[data-machine="${m}"]`);
            if (box) updateMachineBoxColor(box, totalStopDays(m));
        });
    }
}

// ── KPIs ─────────────────────────────────────────────────────────

function renderKpis(kpis, durationSeconds) {
    const bar = document.getElementById('kpi-bar');
    bar.classList.remove('d-none');

    const cost = kpis?.total_cost;
    document.getElementById('kpi-cost').textContent =
        cost != null ? 'R$ ' + cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '—';

    const svc = kpis?.service_level;
    document.getElementById('kpi-service').textContent =
        svc != null ? svc.toFixed(1) + '%' : '—';

    const inv = kpis?.avg_inventory;
    document.getElementById('kpi-inventory').textContent =
        inv != null ? inv.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' Kg' : '—';

    document.getElementById('kpi-duration').textContent =
        durationSeconds != null ? durationSeconds.toFixed(1) + ' s' : '—';
}

function updateCapacityDisplay() {
    const shifts = parseFloat(document.getElementById('shifts-per-day').value) || 0;
    const hours  = parseFloat(document.getElementById('hours-per-shift').value) || 0;
    const days   = parseFloat(document.getElementById('days-per-week').value)   || 0;
    document.getElementById('total-hours-display').value = (shifts * hours * days * 4.33).toFixed(2);
}

function setRunStatus(msg, type) {
    const el = document.getElementById('run-status');
    if (!el) return;
    el.textContent  = msg;
    el.style.color  = type === 'danger'  ? '#dc3545'
                    : type === 'success' ? '#198754'
                    : type === 'warning' ? '#856404'
                    : '#495057';
}

// ── Renderização de resultados ────────────────────────────────────

function renderResults(data) {
    AppState.data.summary    = data.summary    || [];
    AppState.data.production = data.production || [];
    AppState.data.setups     = data.setups     || [];
    AppState.data.machine_stops = data.machine_stops || [];

    renderCharts(data);
    renderSummaryTable(AppState.data.summary);
    renderDetailedTable(AppState.data.production);
    renderSetupsTable(AppState.data.setups);
}

function renderCharts(data) {
    renderInventoryChart(data.inventory);
    renderProductionChart(data.production);
    renderDemandChart(data.demand);
}

function renderInventoryChart(inventoryData) {
    const periods = [...new Set(inventoryData.map(d => d.Period))].sort();
    const totals  = {};
    periods.forEach(p => { totals[p] = 0; });
    inventoryData.forEach(r => { totals[r.Period] += r.Inventory; });

    const ctx = document.getElementById('inventoryChart');
    AppState.charts.inventory?.destroy();
    AppState.charts.inventory = new Chart(ctx, {
        type: 'line',
        data: {
            labels: periods.map(formatDate),
            datasets: [{ label: 'Estoque (Kg)', data: periods.map(p => totals[p]), borderColor: '#00215D', fill: false, tension: 0.2 }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0 } }, plugins: { legend: { display: false } } }
    });
}

function renderDemandChart(demandData) {
    const periods = [...new Set(demandData.map(d => d.Period))].sort();
    const met = {}, lost = {}, total = {};
    periods.forEach(p => { met[p] = 0; lost[p] = 0; total[p] = 0; });
    demandData.forEach(r => { met[r.Period] += r.Met; lost[r.Period] += r.Lost; total[r.Period] += r.Demand; });

    const ctx = document.getElementById('demandChart');
    AppState.charts.demand?.destroy();
    AppState.charts.demand = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: periods.map(formatDate),
            datasets: [
                { label: 'Atendida', data: periods.map(p => met[p]),   backgroundColor: '#198754' },
                { label: 'Perdida',  data: periods.map(p => lost[p]),  backgroundColor: '#dc3545' },
                { type: 'line', label: 'Total', data: periods.map(p => total[p]), borderColor: '#000', borderWidth: 2, pointRadius: 0 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } } }
    });
}

function renderProductionChart(prodData) {
    const periods    = [...new Set(prodData.map(d => d.Period))].sort();
    const allMachines = [...new Set(prodData.map(d => d.Machine))].sort((a, b) => (parseInt(a)||0) - (parseInt(b)||0));

    const palette = [
        '#2563eb','#16a34a','#dc2626','#d97706','#7c3aed',
        '#0891b2','#be185d','#65a30d','#ea580c','#6366f1',
        '#0f766e','#b45309','#9333ea','#0284c7','#15803d',
    ];
    const colorOf = m => palette[allMachines.indexOf(m) % palette.length];

    const cbContainer = document.getElementById('production-machine-checkboxes');
    const btnAll      = document.getElementById('btn-filter-all');

    cbContainer.innerHTML = '';
    allMachines.forEach(m => {
        const chip = document.createElement('button');
        chip.className = 'filter-chip';
        chip.textContent = `M${m}`;
        chip.dataset.machine = m;
        chip.addEventListener('click', () => {
            chip.classList.toggle('selected');
            btnAll.classList.remove('active');
            _updateFilter();
        });
        cbContainer.appendChild(chip);
    });

    btnAll.onclick = () => {
        cbContainer.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('selected'));
        btnAll.classList.add('active');
        _drawAggregated();
    };

    _drawAggregated();

    function _updateFilter() {
        const selected = [...cbContainer.querySelectorAll('.filter-chip.selected')].map(c => c.dataset.machine);
        if (!selected.length) { btnAll.classList.add('active'); _drawAggregated(); }
        else _drawByMachine(selected);
    }

    function _drawAggregated() {
        _render([{ label: 'Total', data: periods.map(p => prodData.filter(x => x.Period === p).reduce((s, x) => s + x.Kg, 0)), backgroundColor: '#2563eb' }], false);
    }

    function _drawByMachine(machines) {
        _render(machines.map(m => ({
            label: `M${m}`,
            data: periods.map(p => prodData.filter(x => x.Period === p && x.Machine === m).reduce((s, x) => s + x.Kg, 0)),
            backgroundColor: colorOf(m)
        })), true);
    }

    function _render(datasets, stacked) {
        const ctx = document.getElementById('productionChart');
        AppState.charts.production?.destroy();
        AppState.charts.production = new Chart(ctx, {
            type: 'bar',
            data: { labels: periods.map(formatDate), datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: stacked, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
                scales: { x: { stacked }, y: { stacked, title: { display: true, text: 'Kg' } } }
            }
        });
    }
}

// ── Tabelas ───────────────────────────────────────────────────────

function renderSummaryTable(data) {
    const tbody = document.getElementById('summary-table-body');
    tbody.innerHTML = '';
    if (!data?.length) { tbody.innerHTML = '<tr class="table-empty"><td colspan="6">Nenhum dado.</td></tr>'; return; }
    data.sort((a, b) => a.Period.localeCompare(b.Period)).forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(row.Period)}</td>
            <td class="text-end">${fmtN(row.Inventory, 0)}</td>
            <td class="text-end">${(row.Utilization * 100).toFixed(1)}%</td>
            <td class="text-end">${fmtN(row.Demand, 0)}</td>
            <td class="text-end">${fmtN(row.Lost, 0)}</td>
            <td class="text-end">${fmtN(row.Production, 0)}</td>`;
        tbody.appendChild(tr);
    });
}

function renderDetailedTable(data) {
    const tbody = document.getElementById('detailed-table-body');
    tbody.innerHTML = '';
    if (!data?.length) { tbody.innerHTML = '<tr class="table-empty"><td colspan="6">Nenhum dado.</td></tr>'; return; }
    data.sort((a, b) => {
        if (a.Period !== b.Period) return a.Period.localeCompare(b.Period);
        const ma = parseInt(a.Machine)||0, mb = parseInt(b.Machine)||0;
        return ma !== mb ? ma - mb : a.Product.localeCompare(b.Product);
    }).forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(row.Period)}</td>
            <td>M${row.Machine}</td>
            <td>${row.Product}</td>
            <td class="text-end">${row.Hours.toFixed(1)} h</td>
            <td class="text-end">${(row.Hours / 24).toFixed(1)} d</td>
            <td class="text-end">${fmtN(row.Kg, 2)} kg</td>`;
        tbody.appendChild(tr);
    });
}

function renderSetupsTable(data) {
    const tbody = document.getElementById('setups-table-body');
    tbody.innerHTML = '';
    if (!data?.length) { tbody.innerHTML = '<tr class="table-empty"><td colspan="5">Nenhum setup.</td></tr>'; return; }
    data.sort((a, b) => {
        if (a.Period !== b.Period) return a.Period.localeCompare(b.Period);
        return (parseInt(a.Machine)||0) - (parseInt(b.Machine)||0);
    }).forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(row.Period)}</td>
            <td>M${row.Machine}</td>
            <td>${row.From}</td>
            <td>${row.To}</td>
            <td class="text-end">R$ ${fmtN(row.Cost || 0, 2)}</td>`;
        tbody.appendChild(tr);
    });
}

// ── Histórico e Comparação ────────────────────────────────────────

async function loadHistory() {
    try {
        const resp = await fetch('/api/history');
        const runs = await resp.json();
        renderComparisonTable(runs);
    } catch (e) {
        document.getElementById('comparison-table-body').innerHTML =
            '<tr class="table-empty"><td colspan="9">Erro ao carregar histórico.</td></tr>';
    }
}

function renderComparisonTable(runs) {
    const tbody = document.getElementById('comparison-table-body');
    tbody.innerHTML = '';

    if (!runs?.length) {
        tbody.innerHTML = '<tr class="table-empty"><td colspan="10">Nenhuma execução registrada.</td></tr>';
        return;
    }

    runs.forEach(run => {
        const kpis  = run.kpis || {};
        const start = run.start_period ? run.start_period.split(' ')[0] : '—';
        const end   = run.end_period   ? run.end_period.split(' ')[0]   : '—';
        const dt    = run.timestamp    ? run.timestamp.replace('T', ' ') : '—';

        const cost  = kpis.total_cost        != null ? 'R$ ' + kpis.total_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '—';
        const svc   = kpis.service_level     != null ? kpis.service_level.toFixed(1) + '%' : '—';
        const inv   = kpis.avg_inventory     != null ? kpis.avg_inventory.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : '—';
        const giro  = kpis.inventory_turnover != null ? kpis.inventory_turnover.toFixed(2) + 'x' : '—';
        const dur   = run.duration_seconds   != null ? run.duration_seconds.toFixed(1) + ' s' : '—';

        const tr = document.createElement('tr');
        tr.className = 'comparison-row';
        tr.innerHTML = `
            <td>${escHtml(run.label || run.id)}</td>
            <td>${dt}</td>
            <td>${start} → ${end}</td>
            <td class="text-center">${run.active_machines_count ?? '—'}</td>
            <td>${run.solver_name || '—'}</td>
            <td class="text-end">${dur}</td>
            <td class="text-end">${cost}</td>
            <td class="text-end">${svc}</td>
            <td class="text-end">${inv}</td>
            <td class="text-end">${giro}</td>`;

        tr.addEventListener('click', () => loadRunIntoResults(run.id));
        tbody.appendChild(tr);
    });
}

async function loadRunIntoResults(runId) {
    try {
        const resp   = await fetch(`/api/history/${runId}`);
        const record = await resp.json();
        if (!record?.result) return;

        renderKpis(record.kpis, record.duration_seconds);
        renderResults(record.result);
        document.querySelector('[data-bs-target="#tab-results"]')?.click();
    } catch (e) {
        console.error('Erro ao carregar cenário:', e);
    }
}

// ── Export CSV ────────────────────────────────────────────────────

function downloadSummaryCSV() {
    downloadCSV(AppState.data.summary,
        ['Mês','Estoque','Utilização','Demanda','Perda','Produzido'],
        r => [formatDate(r.Period), fmtCSV(r.Inventory), fmtCSV(r.Utilization*100), fmtCSV(r.Demand), fmtCSV(r.Lost), fmtCSV(r.Production)],
        'resumo_mensal.csv');
}

function downloadDetailedCSV() {
    downloadCSV(AppState.data.production,
        ['Período','Máquina','Produto','Horas','Dias','kg'],
        r => [formatDate(r.Period), `M${r.Machine}`, r.Product, fmtCSV(r.Hours), fmtCSV(r.Hours/24), fmtCSV(r.Kg)],
        'producao_detalhada.csv');
}

function downloadSetupsCSV() {
    downloadCSV(AppState.data.setups,
        ['Período','Máquina','De','Para','Custo (R$)'],
        r => [formatDate(r.Period), `M${r.Machine}`, r.From, r.To, fmtCSV(r.Cost||0)],
        'setups_detalhado.csv');
}

function downloadCSV(data, headers, mapper, filename) {
    if (!data?.length) { alert('Não há dados para exportar.'); return; }
    let csv = '\uFEFF' + headers.join(';') + '\n';
    data.forEach(row => { csv += mapper(row).join(';') + '\n'; });
    const a   = document.createElement('a');
    a.href    = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    a.download = filename;
    a.click();
}

// ── Formatadores ──────────────────────────────────────────────────

function formatDate(iso) {
    const p = iso.split(' ')[0].split('-');
    if (p.length === 3) return `${p[2]}/${p[1]}/${p[0]}`;
    if (p.length === 2) return `${p[1]}/${p[0]}`;
    return iso;
}

function fmt2(iso) {
    const p = iso.split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}` : iso;
}

function fmtN(val, digits) {
    return (val ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtCSV(val) {
    return (val ?? 0).toFixed(2).replace('.', ',');
}

function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
