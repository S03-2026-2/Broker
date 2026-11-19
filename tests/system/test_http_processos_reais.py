"""Três processos de verdade (Broker, receptor e este teste) conversando por HTTP."""
import time

import httpx
import pytest

from app.cliente.cliente_http import ClienteHttpBroker
from app.cliente.publicador import Publicador
from tests.system.ajudantes import esperar, porta_livre, subir  # noqa: F401

@pytest.fixture
def ambiente_http():
    p_broker, p_receptor = porta_livre(), porta_livre()
    processos = []
    try:
        # reentrega automática desligada na prática (3600 s): o teste a aciona à mão
        broker = subir("app.api.principal:app", p_broker,
                       BROKER_INTERVALO_REENTREGA=3600, BROKER_CHAVE_API="segredo")
        processos.append(broker)
        receptor = subir("demo_http.receptor:app", p_receptor, RECEPTOR_FALHAS_INICIAIS=2)
        processos.append(receptor)
        yield {
            "broker": f"http://127.0.0.1:{p_broker}",
            "receptor": f"http://127.0.0.1:{p_receptor}",
        }
    finally:
        for p in processos:
            p.terminate()
            p.wait(timeout=10)


def test_publicar_assinar_falhar_e_reentregar_entre_processos(ambiente_http):
    url_broker, url_receptor = ambiente_http["broker"], ambiente_http["receptor"]
    cabecalho = {"X-API-Key": "segredo"}
    cliente = ClienteHttpBroker(url_broker, chave_api="segredo")

    cliente.assinar_por_url("jogador.criado", f"{url_receptor}/eventos")
    ack = Publicador("jogadores", cliente).publicar("jogador.criado", {"jogador_id": 42})

    # O receptor falha nas 2 primeiras chamadas: nada chegou ainda.
    assert ack
    time.sleep(0.5)
    assert httpx.get(f"{url_receptor}/eventos").json() == []

    # Reentregas: a 2ª tentativa também falha, a 3ª funciona.
    httpx.post(f"{url_broker}/reentregas", headers=cabecalho)
    r = httpx.post(f"{url_broker}/reentregas", headers=cabecalho)
    assert r.json() == {"entregues": 1}

    eventos = httpx.get(f"{url_receptor}/eventos").json()
    assert len(eventos) == 1
    assert eventos[0]["id"] == ack and eventos[0]["dados"] == {"jogador_id": 42}
    assert httpx.get(f"{url_broker}/erros", headers=cabecalho).json() == {"erros": []}


def test_sem_chave_a_api_recusa(ambiente_http):
    r = httpx.get(f"{ambiente_http['broker']}/topicos")
    assert r.status_code == 401


def test_listagem_de_topicos_e_filas_pela_rede(ambiente_http):
    cliente = ClienteHttpBroker(ambiente_http["broker"], chave_api="segredo")
    cliente.assinar_por_url("troca.criada", f"{ambiente_http['receptor']}/eventos")
    assert cliente.listar_topicos() == ["troca.criada"]
    assert "fila_de_erros" in cliente.listar_filas()
