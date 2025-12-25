/**
 * Riberball Production Planning - Main Frontend Script
 * Modularized for better maintainability.
 */

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initInputs();
    initDataLoading();
    initActionButtons();
    initResizer();
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
        vacations: []
    }
};

// --- Initialization Functions ---

function initTabs() {
    const tabLinks = document.querySelectorAll('.tab-link');
    const subTabLinks = document.querySelectorAll('.sub-tab-link');

    tabLinks.forEach(link => {
        link.addEventListener('click', () => switchTab(link, '.tab-link', '.tab-content', 'data-tab'));
    });

    subTabLinks.forEach(link => {
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
        'operators-per-machine', 'solver-select', 'time-limit'
    ];
    
    inputsToWatch.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveSettingsState);
    });

    ['shifts-per-day', 'hours-per-shift', 'days-per-week'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.addEventListener('input', updateCapacityDisplay);
    });

    const decisionTypeEl = document.getElementById('decision-type');
    if (decisionTypeEl) {
        decisionTypeEl.addEventListener('change', (e) => {
            const type = e.target.value;
            const bucketGroup = document.getElementById('bucket-hours-group');
            if (bucketGroup) bucketGroup.style.display = (type === 'hours') ? 'block' : 'none';
            saveSettingsState();
        });
    }
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

function initResizer() {
    const resizer = document.getElementById('dragMe');
    const leftSide = document.getElementById('left-panel');
    const rightSide = document.getElementById('right-panel');
    const parent = resizer ? resizer.parentElement : null;

    if (!resizer || !leftSide || !rightSide || !parent) return;

    let x = 0;
    let leftWidth = 0;

    const mouseDownHandler = function(e) {
        // Obter posição inicial do mouse
        x = e.clientX;
        leftWidth = leftSide.getBoundingClientRect().width;

        // Adicionar listeners ao documento para permitir arrastar fora do elemento
        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
        
        resizer.classList.add('resizing');
        document.body.style.cursor = 'col-resize'; // Força cursor no body durante drag
        
        // Evita seleção de texto durante o resize
        leftSide.style.userSelect = 'none';
        rightSide.style.userSelect = 'none';
    };

    const mouseMoveHandler = function(e) {
        const dx = e.clientX - x;
        const newLeftWidth = leftWidth + dx;
        const containerWidth = parent.getBoundingClientRect().width;
        
        // Constraints (min widths)
        const minLeft = 300;
        const minRight = 200;

        if (newLeftWidth >= minLeft && newLeftWidth <= (containerWidth - minRight)) {
            leftSide.style.width = `${newLeftWidth}px`;
            leftSide.style.flex = `0 0 auto`; // Fixa a largura, remove comportamento flex responsivo imediato
        }
    };

    const mouseUpHandler = function() {
        document.removeEventListener('mousemove', mouseMoveHandler);
        document.removeEventListener('mouseup', mouseUpHandler);
        
        resizer.classList.remove('resizing');
        document.body.style.removeProperty('cursor');
        
        leftSide.style.removeProperty('user-select');
        rightSide.style.removeProperty('user-select');
    };

    resizer.addEventListener('mousedown', mouseDownHandler);
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

function setupMachineGrid(machines) {
    const machineGrid = document.getElementById('machine-list');
    machineGrid.innerHTML = '';

    machines.forEach(m => {
        const div = document.createElement('div');
        div.className = 'machine-box active'; // Default active
        div.textContent = `M${m}`;
        div.dataset.machine = m;
        
        div.addEventListener('click', () => {
            div.classList.toggle('active');
            saveSettingsState();
        });

        machineGrid.appendChild(div);
    });
}

async function handleRunOptimization() {
    const btn = document.getElementById('btn-run');
    btn.disabled = true;
    updateStatus('Processando otimização...', '#333');
    updateCostDisplay('');

    const payload = buildRunPayload();
    if (!validatePayload(payload)) {
        btn.disabled = false;
        return;
    }
    
    saveSettingsState();

    try {
        // Configura um timeout customizado longo (30 min) para evitar queda do navegador
        const controller = new AbortController();
        // Aumentando para 60 minutos para lidar com instâncias muito complexas
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
        
        if (result.status === 'Optimal') {
            updateStatus('Otimização concluída com sucesso!', 'green');
            if (result.kpis.total_cost !== undefined) {
                updateCostDisplay(result.kpis.total_cost);
            }
            renderResults(result);
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
    }
}

function buildRunPayload() {
    const getVal = (id) => document.getElementById(id).value;
    const ops = parseFloat(getVal('operators-per-machine')) || 0;
    
    return {
        start_period: getVal('start-period') + " 00:00:00",
        end_period: getVal('end-period') ? getVal('end-period') + " 00:00:00" : null,
        active_machines: Array.from(document.querySelectorAll('.machine-box.active')).map(el => el.dataset.machine),
        coverage_months: getVal('coverage-months'),
        decision_type: getVal('decision-type'),
        bucket_hours: getVal('bucket-hours'),
        vacation_planning: ops > 0,
        operators_per_machine: ops,
        solver_name: getVal('solver-select'),
        time_limit: parseInt(getVal('time-limit')) || 600,
        capacity_params: {
            shifts_per_day: getVal('shifts-per-day'),
            hours_per_shift: getVal('hours-per-shift'),
            days_per_week: getVal('days-per-week')
        }
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
        el.textContent = 'Custo Total da Solução: R$ ' + cost.toLocaleString('pt-BR', {minimumFractionDigits: 2});
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
        operatorsPerMachine: document.getElementById('operators-per-machine').value,
        timeLimit: document.getElementById('time-limit').value,
        activeMachines: Array.from(document.querySelectorAll('.machine-box.active')).map(el => el.dataset.machine)
    };
    localStorage.setItem('riberball_settings', JSON.stringify(state));
}

function loadSettingsState() {
    const saved = localStorage.getItem('riberball_settings');
    if (!saved) return;

    try {
        const state = JSON.parse(saved);
        const setVal = (id, val) => { if(val) document.getElementById(id).value = val; };
        
        setVal('start-period', state.startPeriod);
        setVal('end-period', state.endPeriod);
        setVal('coverage-months', state.coverageMonths);
        setVal('shifts-per-day', state.shiftsPerDay);
        setVal('hours-per-shift', state.hoursPerShift);
        setVal('days-per-week', state.daysPerWeek);
        setVal('bucket-hours', state.bucketHours);
        setVal('operators-per-machine', state.operatorsPerMachine);
        setVal('time-limit', state.timeLimit);
        
        if (state.decisionType) {
            const el = document.getElementById('decision-type');
            el.value = state.decisionType;
            el.dispatchEvent(new Event('change')); // Trigger visibility logic
        }

        updateCapacityDisplay();

        if (state.activeMachines) {
            document.querySelectorAll('.machine-box').forEach(el => {
                el.classList.remove('active');
                if (state.activeMachines.includes(el.dataset.machine)) {
                    el.classList.add('active');
                }
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
    renderVacationsChart(data.vacations);
}

function renderVacationsChart(vacationsData) {
    // Get all periods from summary to ensure we show months with 0 vacations
    let periods = [];
    if (AppState.data.summary && AppState.data.summary.length > 0) {
        periods = AppState.data.summary.map(s => s.Period).sort();
    } else if (vacationsData && vacationsData.length > 0) {
        periods = [...new Set(vacationsData.map(d => d.Period))].sort();
    }

    if (periods.length === 0) return;

    const displayPeriods = periods.map(p => formatDate(p));
    
    // Count stopped machines per period
    const countByPeriod = {};
    periods.forEach(p => countByPeriod[p] = 0);
    
    if (vacationsData) {
        vacationsData.forEach(r => {
            if (countByPeriod.hasOwnProperty(r.Period)) {
                countByPeriod[r.Period]++; 
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
                label: 'Máquinas Paradas (Férias)',
                data: periods.map(p => countByPeriod[p]),
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
                    ticks: { stepSize: 1 },
                    title: { display: true, text: 'Qtd. Máquinas' }
                } 
            }
        }
    });
}

function renderInventoryChart(inventoryData) {
    const periods = [...new Set(inventoryData.map(d => d.Period))].sort();
    const displayPeriods = periods.map(p => formatDate(p));
    
    const invByPeriod = {};
    const targetByPeriod = {}; // Keep logic if we re-add target later
    
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
    const machines = [...new Set(prodData.map(d => d.Machine))].sort();
    
    const datasets = machines.map(m => {
        const color = '#' + Math.floor(Math.random()*16777215).toString(16);
        return {
            label: `M${m}`,
            data: periods.map(p => {
                return prodData
                    .filter(x => x.Period === p && x.Machine === m)
                    .reduce((sum, item) => sum + item.Quantity, 0);
            }),
            backgroundColor: color
        };
    });

    const ctx = document.getElementById('productionChart');
    if (AppState.charts.production) AppState.charts.production.destroy();

    AppState.charts.production = new Chart(ctx, {
        type: 'bar',
        data: { labels: displayPeriods, datasets: datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { stacked: true }, y: { stacked: true, title: { display: true, text: 'Kg' } } }
        }
    });
}

function renderDemandChart(demandData) {
    const periods = [...new Set(demandData.map(d => d.Period))].sort();
    const displayPeriods = periods.map(p => formatDate(p));
    
    const metrics = { demand: {}, met: {}, lost: {}, backlog: {} };
    periods.forEach(p => { for(let k in metrics) metrics[k][p] = 0; });
    
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
        tr.style.borderBottom = '1px solid #eee';
        
        // Resumo Mensal geralmente usa formato Mês/Ano. 
        // Mas se quisermos forçar consistência, podemos usar a mesma lógica ou ajustar.
        // Dado que é "Resumo Mensal", manter MM/AAAA talvez seja melhor, 
        // mas o usuário pediu "Force DD/MM/AAAA".
        // Vamos aplicar DD/MM/AAAA se a data tiver dia. Se for só mês, mantém.
        const fmtDate = formatDate(row.Period);
        
        tr.innerHTML = `
            <td style="padding: 10px; text-align: left;">${fmtDate}</td>
            <td style="padding: 10px;">${fmtNumber(row.Inventory, 0)}</td>
            <td style="padding: 10px;">${(row.Utilization * 100).toFixed(1)}%</td>
            <td style="padding: 10px;">${fmtNumber(row.Demand, 0)}</td>
            <td style="padding: 10px;">${fmtNumber(row.Lost, 0)}</td>
            <td style="padding: 10px;">${fmtNumber(row.Production, 0)}</td>
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
        tr.style.borderBottom = '1px solid #eee';
        
        const daysProd = row.Hours / 24.0;
        
        tr.innerHTML = `
            <td style="padding: 10px;">${formatDate(row.Period)}</td>
            <td style="padding: 10px;">M${row.Machine}</td>
            <td style="padding: 10px;">${row.Product}</td>
            <td style="padding: 10px; text-align: right;">${row.Hours.toFixed(1)}h</td>
            <td style="padding: 10px; text-align: right;">${daysProd.toFixed(1)}d</td>
            <td style="padding: 10px; text-align: right;">${fmtNumber(row.Quantity, 2)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderSetupsTable(data) {
    const tbody = document.getElementById('setups-table-body');
    if (!tbody) return;
    
    // Add header for Cost if not exists
    const thead = tbody.previousElementSibling;
    if (thead) {
        const headerRow = thead.querySelector('tr');
        if (headerRow && headerRow.children.length === 4) {
            const th = document.createElement('th');
            th.textContent = "Custo Estimado (R$)";
            th.style.padding = "12px";
            th.style.textAlign = "right";
            headerRow.appendChild(th);
        }
    }

    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center;">Nenhum setup registrado.</td></tr>';
        return;
    }

    // Sort: Period, Machine
    data.sort((a, b) => {
        if (a.Period !== b.Period) return a.Period.localeCompare(b.Period);
        const mA = parseInt(a.Machine) || 0;
        const mB = parseInt(b.Machine) || 0;
        return mA - mB;
    });

    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #eee';
        
        const cost = row.Cost !== undefined ? fmtNumber(row.Cost, 2) : '-';

        tr.innerHTML = `
            <td style="padding: 10px;">${formatDate(row.Period)}</td>
            <td style="padding: 10px;">M${row.Machine}</td>
            <td style="padding: 10px;">${row.From}</td>
            <td style="padding: 10px;">${row.To}</td>
            <td style="padding: 10px; text-align: right;">R$ ${cost}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderVacationsTable(data) {
    const tbody = document.getElementById('vacations-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="padding: 20px; text-align: center;">Nenhuma férias programada ou módulo desativado.</td></tr>';
        return;
    }

    // Sort: Period, Machine
    data.sort((a, b) => {
        if (a.Period !== b.Period) return a.Period.localeCompare(b.Period);
        const mA = parseInt(a.Machine) || 0;
        const mB = parseInt(b.Machine) || 0;
        return mA - mB;
    });

    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #eee';
        
        tr.innerHTML = `
            <td style="padding: 10px;">${formatDate(row.Period)}</td>
            <td style="padding: 10px;">M${row.Machine}</td>
            <td style="padding: 10px;">${row.Operators} Operadores</td>
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
    downloadCSV(AppState.data.vacations, ["Período", "Máquina", "Operadores"], row => [
        formatDate(row.Period),
        `M${row.Machine}`,
        row.Operators
    ], "ferias_programadas.csv");
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
    // Tenta limpar timestamp se vier (ex: "2024-01-01 00:00:00")
    const cleanDate = isoDate.split(' ')[0]; 
    const parts = cleanDate.split('-');
    
    // YYYY-MM-DD -> DD/MM/YYYY
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    // YYYY-MM -> MM/YYYY (Fallback se vier incompleto)
    if (parts.length === 2) {
        return `${parts[1]}/${parts[0]}`;
    }
    return isoDate;
}

function fmtNumber(val, digits) {
    return val.toLocaleString('pt-BR', {minimumFractionDigits: digits, maximumFractionDigits: digits});
}

function fmtNumberCSV(val) {
    return val.toFixed(2).replace('.', ',');
}
