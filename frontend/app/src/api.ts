import type {
  BackendStatus,
  ChangeDecision,
  DailyResult,
  HistoryRecord,
  HistoryRun,
  InitData,
  Settings,
  Snapshots,
  UploadOutcome,
  UploadReview,
  WeeklyResult,
} from './types';

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const raw = await response.text();

  let body: any = null;
  let parsed = false;
  if (raw.length > 0) {
    try {
      body = JSON.parse(raw);
      parsed = true;
    } catch {
      parsed = false;
    }
  }

  if (!parsed) {
    throw new Error(`HTTP ${response.status} - o servidor respondeu algo que nao e JSON`);
  }
  if (!response.ok) {
    throw new Error(body?.message || body?.error || `HTTP ${response.status}`);
  }
  return body as T;
}

export function getBackendStatus(): Promise<BackendStatus> {
  return requestJson('/api/backend-status');
}

export function getSnapshots(): Promise<Snapshots> {
  return requestJson('/api/snapshots');
}

export function setActiveSnapshot(snapshotId: number): Promise<{ status: string; active: number }> {
  return requestJson('/api/snapshots/active', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ snapshot_id: snapshotId }),
  });
}

export function uploadWorkbook(file: File): Promise<UploadReview> {
  return requestJson(`/api/uploads?filename=${encodeURIComponent(file.name)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/octet-stream' },
    body: file,
  });
}

export function applyUpload(uploadId: number, decisions: Record<string, ChangeDecision>): Promise<UploadOutcome> {
  return requestJson(`/api/uploads/${uploadId}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decisions }),
  });
}

export function discardUpload(uploadId: number): Promise<{ status: string }> {
  return requestJson(`/api/uploads/${uploadId}/discard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
}

export function setMachineActive(machine: string, isActive: boolean): Promise<{ status: string }> {
  return requestJson('/api/machines/active', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ machine, is_active: isActive }),
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

export function runWeekly(settings: Settings, label: string): Promise<WeeklyResult> {
  return requestJson(`/api/run?t=${Date.now()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings, label }),
    signal: AbortSignal.timeout(3_600_000),
  });
}

export function runDaily(runId: string | undefined): Promise<DailyResult> {
  return requestJson(`/api/run-daily?t=${Date.now()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId }),
    signal: AbortSignal.timeout(3_600_000),
  });
}

export function getHistory(): Promise<HistoryRun[]> {
  return requestJson('/api/history');
}

export function getHistoryRun(runId: string): Promise<HistoryRecord> {
  return requestJson(`/api/history/${runId}`);
}
