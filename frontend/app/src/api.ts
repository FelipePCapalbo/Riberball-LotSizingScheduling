import type { BackendStatus, ColorRunResult, DataFiles, HistoryRecord, HistoryRun, InitData, RunResult, Settings } from './types';

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body?.message || body?.error || `HTTP ${response.status}`);
  }
  return body as T;
}

export function getBackendStatus(): Promise<BackendStatus> {
  return requestJson('/api/backend-status');
}

export function getDataFiles(): Promise<DataFiles> {
  return requestJson('/api/data-files');
}

export function setDataFile(file: string): Promise<{ status: string; file: string }> {
  return requestJson('/api/set-data-file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file }),
  });
}

export function getInitData(): Promise<InitData> {
  return requestJson('/api/init-data');
}

export function getSettings(): Promise<Settings> {
  return requestJson('/api/settings');
}

export function saveSettings(settings: Settings): Promise<{ status: string }> {
  return requestJson('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
}

export function runOptimization(settings: Settings, label: string): Promise<RunResult> {
  return requestJson(`/api/run?t=${Date.now()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings, label }),
    signal: AbortSignal.timeout(3_600_000),
  });
}

export function runColor(colorMethod: string): Promise<ColorRunResult> {
  return requestJson(`/api/run-color?t=${Date.now()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ color_method: colorMethod }),
    signal: AbortSignal.timeout(3_600_000),
  });
}

export function getHistory(): Promise<HistoryRun[]> {
  return requestJson('/api/history');
}

export function getHistoryRun(runId: string): Promise<HistoryRecord> {
  return requestJson(`/api/history/${runId}`);
}
