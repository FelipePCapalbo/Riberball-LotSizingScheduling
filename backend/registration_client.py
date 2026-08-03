import httpx

from backend.config import SHARED_SECRET, WORKER_BASE_URL


async def register(instance_id, machine_label):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f'{WORKER_BASE_URL}/internal/backend/register',
            headers={'Authorization': f'Bearer {SHARED_SECRET}'},
            json={'instance_id': instance_id, 'machine_label': machine_label},
        )
    return response


async def heartbeat(instance_id, public_url=None):
    payload = {'instance_id': instance_id}
    if public_url:
        payload['public_url'] = public_url
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f'{WORKER_BASE_URL}/internal/backend/heartbeat',
            headers={'Authorization': f'Bearer {SHARED_SECRET}'},
            json=payload,
        )
    return response


async def unregister(instance_id):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f'{WORKER_BASE_URL}/internal/backend/unregister',
            headers={'Authorization': f'Bearer {SHARED_SECRET}'},
            json={'instance_id': instance_id},
        )
    return response
