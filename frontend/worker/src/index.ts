import { BackendCoordinator } from './backend-coordinator';

export { BackendCoordinator };

export interface Env {
  ASSETS: Fetcher;
  BACKEND_COORDINATOR: DurableObjectNamespace;
  SHARED_SECRET: string;
}

function getCoordinatorStub(env: Env): DurableObjectStub {
  const id = env.BACKEND_COORDINATOR.idFromName('singleton');
  return env.BACKEND_COORDINATOR.get(id);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    let response: Response;

    if (url.pathname === '/api/backend-status') {
      const coordinator = getCoordinatorStub(env);
      response = await coordinator.fetch('https://coordinator/status');
    } else if (url.pathname.startsWith('/internal/backend/')) {
      if (request.headers.get('Authorization') !== `Bearer ${env.SHARED_SECRET}`) {
        response = new Response('unauthorized', { status: 401 });
      } else {
        const coordinator = getCoordinatorStub(env);
        const action = url.pathname.replace('/internal/backend/', '');
        response = await coordinator.fetch(`https://coordinator/${action}`, {
          method: request.method,
          headers: request.headers,
          body: request.body,
        });
      }
    } else if (url.pathname.startsWith('/api/')) {
      const coordinator = getCoordinatorStub(env);
      const statusResponse = await coordinator.fetch('https://coordinator/status');
      const status = await statusResponse.json<{ connected: boolean; public_url: string | null }>();
      if (!status.connected || !status.public_url) {
        response = Response.json({ error: 'no backend connected' }, { status: 503 });
      } else {
        const proxyUrl = status.public_url + url.pathname + url.search;
        const proxyHeaders = new Headers(request.headers);
        proxyHeaders.set('Authorization', `Bearer ${env.SHARED_SECRET}`);
        try {
          response = await fetch(proxyUrl, {
            method: request.method,
            headers: proxyHeaders,
            body: request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body,
          });
        } catch {
          response = Response.json(
            {
              error: 'backend unreachable',
              message: 'O tunel do backend nao respondeu. Verifique se ele continua rodando na maquina.',
            },
            { status: 502 },
          );
        }
      }
    } else {
      response = await env.ASSETS.fetch(request);
    }

    return response;
  },
};
