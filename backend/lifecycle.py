import asyncio
import os
import signal
import uuid
from contextlib import asynccontextmanager

from backend import registration_client, tunnel
from backend.config import HEARTBEAT_INTERVAL_SECONDS, MACHINE_LABEL, PORT, TUNNEL_ENABLED, WORKER_BASE_URL

instance_id = str(uuid.uuid4())


async def heartbeat_loop():
    lease_lost = False
    while not lease_lost:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        response = await registration_client.heartbeat(instance_id)
        if response.status_code == 409:
            print('[backend] Lease perdido para outra instância conectada. Encerrando.', flush=True)
            os.kill(os.getpid(), signal.SIGTERM)
            lease_lost = True


@asynccontextmanager
async def lifespan(app):
    tunnel_process = None
    heartbeat_task = None

    if TUNNEL_ENABLED:
        response = await registration_client.register(instance_id, MACHINE_LABEL)
        if response.status_code == 409:
            existing = response.json()
            raise RuntimeError(
                f'Já existe um backend conectado (máquina "{existing.get("machine_label")}", '
                f'registrado às {existing.get("registered_at")}). Encerrando esta instância.'
            )
        elif response.status_code == 401:
            raise RuntimeError(
                f'O frontend em {WORKER_BASE_URL} recusou a autenticação (401). '
                'O SHARED_SECRET de backend/.env não confere com o configurado no Worker.'
            )
        elif response.status_code != 200:
            raise RuntimeError(
                f'O frontend em {WORKER_BASE_URL} respondeu {response.status_code} ao registrar. '
                'Confira se o endereço está correto e se o Worker está publicado.'
            )

        tunnel_process, public_url = await tunnel.start_tunnel(PORT)
        print(f'[backend] Túnel público em {public_url}', flush=True)

        response = await registration_client.heartbeat(instance_id, public_url=public_url)
        if response.status_code != 200:
            raise RuntimeError(
                f'O frontend em {WORKER_BASE_URL} respondeu {response.status_code} ao publicar '
                'a URL do túnel. A interface não conseguiria alcançar este backend.'
            )

        print('[backend] Conectado à interface. Pode fechar esta janela para encerrar.', flush=True)
        heartbeat_task = asyncio.create_task(heartbeat_loop())

    try:
        yield
    finally:
        if TUNNEL_ENABLED:
            if heartbeat_task:
                heartbeat_task.cancel()
            await registration_client.unregister(instance_id)
            await tunnel.stop_tunnel(tunnel_process)
