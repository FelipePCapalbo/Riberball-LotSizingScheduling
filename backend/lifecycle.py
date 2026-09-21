import asyncio
import os
import signal
import uuid
from contextlib import asynccontextmanager

import httpx

from backend import registration_client, tunnel
from backend.config import (
    HEARTBEAT_INTERVAL_SECONDS,
    MACHINE_LABEL,
    PORT,
    SHARED_SECRET,
    TUNNEL_ENABLED,
    WORKER_BASE_URL,
)

REGISTER_ATTEMPTS = 4
REGISTER_RETRY_SECONDS = 5
PROBE_INTERVAL_SECONDS = 1
PROBE_TIMEOUT_SECONDS = 90
DNS_INTERVAL_SECONDS = 3
DNS_TIMEOUT_SECONDS = 120
DOH_RESOLVER_URL = 'https://cloudflare-dns.com/dns-query'

instance_id = str(uuid.uuid4())
published_url = None
tunnel_process = None


async def release_lease():
    try:
        await registration_client.unregister(instance_id)
    except httpx.HTTPError:
        print('[backend] Não foi possível avisar o frontend da desconexão. '
              'O registro expira sozinho em 45s.', flush=True)


async def publish_tunnel():
    global published_url, tunnel_process

    tunnel_process, public_url = await tunnel.start_tunnel(PORT)
    print(f'[backend] Túnel público em {public_url}', flush=True)

    str_tunnel_host = public_url.split('://')[1]
    loop = asyncio.get_event_loop()
    dns_deadline = loop.time() + DNS_TIMEOUT_SECONDS
    dns_is_published = False
    while not dns_is_published and loop.time() < dns_deadline:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                lookup = await client.get(
                    DOH_RESOLVER_URL,
                    params={'name': str_tunnel_host, 'type': 'A'},
                    headers={'Accept': 'application/dns-json'},
                )
                dict_lookup = lookup.json()
                if dict_lookup.get('Status') == 0 and dict_lookup.get('Answer'):
                    dns_is_published = True
                else:
                    dns_is_published = False
            except httpx.HTTPError:
                dns_is_published = False
        if not dns_is_published:
            await asyncio.sleep(DNS_INTERVAL_SECONDS)

    if not dns_is_published:
        raise RuntimeError(
            f'O nome {str_tunnel_host} não entrou no DNS em {DNS_TIMEOUT_SECONDS}s. '
            'O túnel subiu, mas ninguém conseguiria alcançá-lo.'
        )

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

    if not tunnel_is_serving:
        raise RuntimeError(
            f'O túnel {public_url} não respondeu em {PROBE_TIMEOUT_SECONDS}s. '
            'A interface não conseguiria alcançar este backend.'
        )

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

    published_url = public_url
    print('[backend] Conectado à interface. Pode fechar esta janela para encerrar.', flush=True)


def report_publish_failure(task):
    if not task.cancelled() and task.exception():
        print(f'[backend] {task.exception()}', flush=True)
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


@asynccontextmanager
async def lifespan(app):
    publish_task = None
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

        heartbeat_task = asyncio.create_task(heartbeat_loop())
        publish_task = asyncio.create_task(publish_tunnel())
        publish_task.add_done_callback(report_publish_failure)

    try:
        yield
    finally:
        if TUNNEL_ENABLED:
            publish_task.cancel()
            heartbeat_task.cancel()
            await release_lease()
            await tunnel.stop_tunnel(tunnel_process)
