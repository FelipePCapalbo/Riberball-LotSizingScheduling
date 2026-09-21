import type { BackendState } from '../types';

interface Props {
  state: BackendState;
  machineLabel?: string;
}

export default function BackendStatusBadge({ state, machineLabel }: Props) {
  let text: string;
  if (state === 'connected') {
    text = `backend conectado (${machineLabel})`;
  } else if (state === 'starting') {
    text = `backend iniciando o túnel (${machineLabel})`;
  } else if (state === 'disconnected') {
    text = 'nenhum backend conectado';
  } else {
    text = 'verificando backend...';
  }

  return <div className={`status status--${state}`}>{text}</div>;
}
