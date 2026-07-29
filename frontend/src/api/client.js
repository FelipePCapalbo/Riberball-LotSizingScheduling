async function request(path, options = {}) {
    const response = await fetch(path, options)
    if (!response.ok) {
        const body = await response.json().catch(() => null)
        const detail = body?.detail
        const message = typeof detail === 'string' ? detail : detail?.message || `HTTP ${response.status}`
        throw new Error(message)
    }
    return response.json()
}

export function getDataFiles() {
    return request('/api/data-files')
}

export function setDataFile(file) {
    return request('/api/set-data-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file })
    })
}

export function getInitData() {
    return request('/api/init-data')
}

export function getSettings() {
    return request('/api/settings')
}

export function postSettings(settings) {
    return request('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
}

export function runTactical(settings, label) {
    return request('/api/run?t=' + Date.now(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings, label }),
        signal: AbortSignal.timeout(3_600_000)
    })
}

export function runColor(colorMethod) {
    return request('/api/run-color?t=' + Date.now(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color_method: colorMethod }),
        signal: AbortSignal.timeout(3_600_000)
    })
}

export function getHistory() {
    return request('/api/history')
}

export function getHistoryRun(runId) {
    return request(`/api/history/${runId}`)
}
