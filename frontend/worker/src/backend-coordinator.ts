interface Lease {
  instanceId: string;
  machineLabel: string;
  publicUrl: string | null;
  registeredAt: number;
  lastHeartbeatAt: number;
}

const LEASE_TTL_MS = 45000;

export class BackendCoordinator implements DurableObject {
  state: DurableObjectState;

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const lease = await this.state.storage.get<Lease>('lease');
    const now = Date.now();
    const leaseActive = lease !== undefined && now - lease.lastHeartbeatAt < LEASE_TTL_MS;

    let response: Response;

    if (url.pathname === '/register' && request.method === 'POST') {
      const body = await request.json<{ instance_id: string; machine_label: string }>();
      if (leaseActive && lease!.instanceId !== body.instance_id) {
        response = Response.json(
          { error: 'already_connected', machine_label: lease!.machineLabel, registered_at: lease!.registeredAt },
          { status: 409 },
        );
      } else {
        const newLease: Lease = {
          instanceId: body.instance_id,
          machineLabel: body.machine_label,
          publicUrl: null,
          registeredAt: now,
          lastHeartbeatAt: now,
        };
        await this.state.storage.put('lease', newLease);
        response = Response.json({ status: 'registered' });
      }
    } else if (url.pathname === '/heartbeat' && request.method === 'POST') {
      const body = await request.json<{ instance_id: string; public_url?: string }>();
      if (!leaseActive || lease!.instanceId !== body.instance_id) {
        response = Response.json({ error: 'lease_lost' }, { status: 409 });
      } else {
        lease!.lastHeartbeatAt = now;
        if (body.public_url) {
          lease!.publicUrl = body.public_url;
        }
        await this.state.storage.put('lease', lease);
        response = Response.json({ status: 'ok' });
      }
    } else if (url.pathname === '/unregister' && request.method === 'POST') {
      const body = await request.json<{ instance_id: string }>();
      if (lease && lease.instanceId === body.instance_id) {
        await this.state.storage.delete('lease');
      }
      response = Response.json({ status: 'ok' });
    } else if (url.pathname === '/status' && request.method === 'GET') {
      if (leaseActive) {
        response = Response.json({
          connected: true,
          machine_label: lease!.machineLabel,
          public_url: lease!.publicUrl,
          since: lease!.registeredAt,
          last_heartbeat_at: lease!.lastHeartbeatAt,
        });
      } else {
        response = Response.json({ connected: false });
      }
    } else {
      response = new Response('not found', { status: 404 });
    }

    return response;
  }
}
