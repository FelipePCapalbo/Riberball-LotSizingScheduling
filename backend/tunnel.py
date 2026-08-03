import asyncio
import atexit
import re
import shutil

TRYCLOUDFLARE_URL_PATTERN = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
STARTUP_TIMEOUT_SECONDS = 30

_tunnel_process = None


def _terminate_on_exit():
    if _tunnel_process and _tunnel_process.returncode is None:
        _tunnel_process.terminate()


atexit.register(_terminate_on_exit)


async def _drain_stdout(process):
    async for _line in process.stdout:
        pass


async def start_tunnel(port):
    global _tunnel_process
    cloudflared_path = shutil.which('cloudflared')
    if not cloudflared_path:
        raise RuntimeError(
            'cloudflared não encontrado no PATH. Instale com "brew install cloudflared" (macOS) '
            'ou "choco install cloudflared" (Windows) antes de iniciar o backend.'
        )

    _tunnel_process = await asyncio.create_subprocess_exec(
        cloudflared_path, 'tunnel', '--url', f'http://localhost:{port}',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    loop = asyncio.get_event_loop()
    deadline = loop.time() + STARTUP_TIMEOUT_SECONDS
    public_url = None
    while public_url is None:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise RuntimeError('Timeout esperando o cloudflared publicar a URL do túnel.')
        line = await asyncio.wait_for(_tunnel_process.stdout.readline(), timeout=remaining)
        match = TRYCLOUDFLARE_URL_PATTERN.search(line.decode(errors='ignore'))
        if match:
            public_url = match.group(0)

    asyncio.create_task(_drain_stdout(_tunnel_process))
    return _tunnel_process, public_url


async def stop_tunnel(process):
    if process and process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=10)
        except asyncio.TimeoutError:
            process.kill()
