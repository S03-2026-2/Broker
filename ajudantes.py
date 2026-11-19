"""Ferramentas dos testes de sistema: subir processos reais do Broker e do receptor."""
import contextlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def subir(modulo: str, porta: int, **ambiente) -> subprocess.Popen:
    env = {**os.environ, **{k: str(v) for k, v in ambiente.items()}}
    processo = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", modulo, "--host", "127.0.0.1",
         "--port", str(porta), "--log-level", "warning"],
        cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    fim = time.time() + 15
    while time.time() < fim:
        try:
            if httpx.get(f"http://127.0.0.1:{porta}/saude", timeout=0.5).status_code == 200:
                return processo
        except httpx.HTTPError:
            time.sleep(0.1)
    processo.kill()
    raise RuntimeError(f"{modulo} não subiu: {processo.stderr.read().decode()}")


@contextlib.contextmanager
def ambiente(env_broker=None, env_receptor=None):
    """Sobe o Broker e o receptor de exemplo; devolve as duas URLs base."""
    p_broker, p_receptor = porta_livre(), porta_livre()
    processos = []
    try:
        processos.append(subir("app.api.principal:app", p_broker,
                               **{"BROKER_INTERVALO_REENTREGA": 3600, **(env_broker or {})}))
        processos.append(subir("demo_http.receptor:app", p_receptor, **(env_receptor or {})))
        yield f"http://127.0.0.1:{p_broker}", f"http://127.0.0.1:{p_receptor}"
    finally:
        for p in processos:
            p.terminate()
            p.wait(timeout=10)


def esperar(condicao, limite=10.0):
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(0.05)
    return False
