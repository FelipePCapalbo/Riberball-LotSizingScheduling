import { useEffect, useState } from 'react';
import { getBackendStatus } from '../api';

const POLL_INTERVAL_MS = 5000;

export default function BackendStatusBadge() {
  const [status, setStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');
  const [machineLabel, setMachineLabel] = useState<string | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;

    const refresh = () => {
      getBackendStatus()
        .then((data) => {
          if (!cancelled) {
            setStatus(data.connected ? 'connected' : 'disconnected');
            setMachineLabel(data.machine_label);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setStatus('disconnected');
          }
        });
    };

    refresh();
    const intervalId = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  let text: string;
  if (status === 'connected') {
    text = `backend conectado (${machineLabel})`;
  } else if (status === 'disconnected') {
    text = 'nenhum backend conectado';
  } else {
    text = 'verificando backend...';
  }

  return <div className={`status status--${status}`}>{text}</div>;
}
