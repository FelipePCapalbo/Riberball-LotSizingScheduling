import asyncio
import os
import signal
import uuid
from contextlib import asynccontextmanager

import httpx

from backend import registration_client, tunnel
from backend.config import HEARTBEAT_INTERVAL_SECONDS, MACHINE_LABEL, PORT, TUNNEL_ENABLED, WORKER_BASE_URL

REGISTER_ATTEMPTS = 4
REGISTER_RETRY_SECONDS = 5

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
        response = None
        int_attempt = 0
        while response is None:
            int_attempt = int_attempt + 1
            try:
                response = await registration_client.register(instance_id, MACHINE_LABEL)
            except httpx.HTTPError:
                if int_attempt < REGISTER_ATTEMPTS:
                    print(f'[backend] Frontend não respondeu (tentativa {int_attempt} de '
                          f'{REGISTER_ATTEMPTS}). Nova tentativa em {REGISTER_RETRY_SECONDS}s...',
                          flush=True)
                    await asyncio.sleep(REGISTER_RETRY_SECONDS)
                else:
                    raise RuntimeError(
                        f'Não foi possível falar com o frontend em {WORKER_BASE_URL} após '
                        f'{REGISTER_ATTEMPTS} tentativas. Confira a conexão com a internet '
                        'e se a saída HTTPS não está bloqueada nesta rede.'
                    ) from None

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

        response = None
        int_attempt = 0
        while response is None:
            int_attempt = int_attempt + 1
            try:
                response = await registration_client.heartbeat(instance_id, public_url=public_url)
            except httpx.HTTPError:
                if int_attempt < REGISTER_ATTEMPTS:
                    print(f'[backend] Frontend não respondeu ao publicar a URL do túnel '
                          f'(tentativa {int_attempt} de {REGISTER_ATTEMPTS}). '
                          f'Nova tentativa em {REGISTER_RETRY_SECONDS}s...', flush=True)
                    await asyncio.sleep(REGISTER_RETRY_SECONDS)
                else:
                    raise RuntimeError(
                        f'O túnel subiu, mas não foi possível publicar a URL no frontend em '
                        f'{WORKER_BASE_URL} após {REGISTER_ATTEMPTS} tentativas.'
                    ) from None

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
