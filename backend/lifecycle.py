import asyncio
import os
import signal
import uuid
from contextlib import asynccontextmanager

import httpx

from backend import registration_client, tunnel
from backend.config import HEARTBEAT_INTERVAL_SECONDS, MACHINE_LABEL, PORT, SHARED_SECRET, TUNNEL_ENABLED

PROBE_INTERVAL_SECONDS = 1.0
PROBE_TIMEOUT_SECONDS = 90

instance_id = str(uuid.uuid4())
published_url = None
tunnel_process = None


async def publish_tunnel():
    global published_url, tunnel_process

    tunnel_process, public_url = await tunnel.start_tunnel(PORT)
    print(f'[backend] Túnel público em {public_url}', flush=True)

    loop = asyncio.get_event_loop()
    deadline = loop.time() + PROBE_TIMEOUT_SECONDS
    tunnel_is_serving = False
    while not tunnel_is_serving and loop.time() < deadline:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                probe = await client.get(
                    f'{public_url}/api/health',
                    headers={'Authorization': f'Bearer {SHARED_SECRET}'},
                )
                tunnel_is_serving = probe.status_code == 200
            except httpx.HTTPError:
                tunnel_is_serving = False
        if not tunnel_is_serving:
            await asyncio.sleep(PROBE_INTERVAL_SECONDS)

    if tunnel_is_serving:
        published_url = public_url
        await registration_client.heartbeat(instance_id, public_url=public_url)
        print('[backend] Túnel respondendo; frontend liberado para usar a API.', flush=True)
    else:
        print(f'[backend] Túnel não respondeu em {PROBE_TIMEOUT_SECONDS} s. Encerrando.', flush=True)
        os.kill(os.getpid(), signal.SIGTERM)


async def heartbeat_loop():
    lease_lost = False
    while not lease_lost:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        response = await registration_client.heartbeat(instance_id, public_url=published_url)
        if response.status_code == 409:
            print('[backend] Lease perdido para outra instância conectada. Encerrando.', flush=True)
            os.kill(os.getpid(), signal.SIGTERM)
            lease_lost = True


def report_publish_failure(task):
    if not task.cancelled() and task.exception():
        print(f'[backend] Falha ao publicar o túnel: {task.exception()}', flush=True)
        os.kill(os.getpid(), signal.SIGTERM)


@asynccontextmanager
async def lifespan(app):
    publish_task = None
    heartbeat_task = None

    if TUNNEL_ENABLED:
        response = await registration_client.register(instance_id, MACHINE_LABEL)
        if response.status_code == 409:
            existing = response.json()
            raise RuntimeError(
                f'Já existe um backend conectado (máquina "{existing.get("machine_label")}", '
                f'registrado às {existing.get("registered_at")}). Encerrando esta instância.'
            )
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        publish_task = asyncio.create_task(publish_tunnel())
        publish_task.add_done_callback(report_publish_failure)

    try:
        yield
    finally:
        if TUNNEL_ENABLED:
            publish_task.cancel()
            heartbeat_task.cancel()
            await registration_client.unregister(instance_id)
            await tunnel.stop_tunnel(tunnel_process)
