import type { BackendStatus, DataFiles, HistoryRecord, HistoryRun, InitData, RunResult, Settings } from './types';

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  return response.json() as Promise<T>;
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

export function runOptimization(label: string): Promise<RunResult> {
  return requestJson(`/api/run?t=${Date.now()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label }),
    signal: AbortSignal.timeout(3_600_000),
  });
}

export function getHistory(): Promise<HistoryRun[]> {
  return requestJson('/api/history');
}

export function getHistoryRun(runId: string): Promise<HistoryRecord> {
  return requestJson(`/api/history/${runId}`);
}
