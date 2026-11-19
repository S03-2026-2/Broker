"""Painel, estado, histórico e reprocessamento pela API (com envio HTTP simulado)."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.aplicacao import criar_aplicacao
from app.api.assinante_webhook import AssinanteWebhook
from app.servidor.broker import Broker

URL = "http://distribuicao/eventos"


class Destino:
    def __init__(self):
        self.status = 200
        self.recebidos = []

    def handler(self, request):
        self.recebidos.append(json.loads(request.content))
        return httpx.Response(self.status)


@pytest.fixture
def destino():
    return Destino()


@pytest.fixture
def cliente(destino):
    http = httpx.Client(transport=httpx.MockTransport(destino.handler))
    app = criar_aplicacao(Broker(max_tentativas=3), lambda url: AssinanteWebhook(url, http))
    return TestClient(app)


def assinar(cliente, topico="jogador.criado", url=URL):
    cliente.post("/assinar", json={"topico": topico, "url": url})


def publicar(cliente, topico="jogador.criado", dados=None):
    return cliente.post("/publicar", json={"topico": topico, "dados": dados or {}}).json()["id"]


def test_topico_publicado_sem_assinantes_aparece_em_topicos(cliente):
    publicar(cliente, "novo.topico")
    assert cliente.get("/topicos").json() == {"topicos": ["novo.topico"]}


def test_estado_mostra_assinantes_contadores_e_filas(cliente, destino):
    assinar(cliente)
    publicar(cliente)
    estado = cliente.get("/estado").json()
    topico = estado["topicos"][0]
    assert topico["nome"] == "jogador.criado" and topico["publicadas"] == 1
    assert topico["assinantes"][0]["destino"] == URL
    assert topico["assinantes"][0]["entregues"] == 1
    assert estado["totais"]["publicadas"] == 1 and estado["totais"]["entregues"] == 1
    assert any(f["nome"] == "fila_de_erros" for f in estado["filas"])


def test_estado_acompanha_falhas_e_pendentes(cliente, destino):
    assinar(cliente)
    destino.status = 503
    publicar(cliente)
    estado = cliente.get("/estado").json()
    assinante = estado["topicos"][0]["assinantes"][0]
    assert assinante["falhas"] == 1 and assinante["pendentes"] == 1
    assert estado["totais"]["falhas"] == 1


def test_historico_conta_a_historia_da_mensagem(cliente, destino):
    assinar(cliente)
    destino.status = 503
    id_msg = publicar(cliente)
    cliente.post("/reentregas")
    cliente.post("/reentregas")                    # esgota
    destino.status = 200
    cliente.post(f"/erros/{id_msg}/reprocessar")

    eventos = cliente.get("/historico").json()["eventos"]
    sequencia = [e["tipo"] for e in eventos if e["mensagem"] == id_msg]
    assert sequencia == ["publicada", "falhou", "falhou", "esgotada", "reprocessada", "entregue"]


def test_historico_desde_devolve_so_o_que_e_novo(cliente):
    assinar(cliente)
    publicar(cliente)
    ultimo = cliente.get("/historico").json()["eventos"][-1]["id"]
    publicar(cliente)
    novos = cliente.get("/historico", params={"desde": ultimo}).json()["eventos"]
    assert [e["tipo"] for e in novos] == ["publicada", "entregue"]


def test_historico_respeita_o_limite(cliente):
    for _ in range(5):
        publicar(cliente)
    assert len(cliente.get("/historico", params={"limite": 2}).json()["eventos"]) == 2


def test_erros_informam_o_destino_da_falha(cliente, destino):
    assinar(cliente)
    destino.status = 503
    publicar(cliente)
    cliente.post("/reentregas")
    cliente.post("/reentregas")
    erro = cliente.get("/erros").json()["erros"][0]
    assert erro["destinos"][0].startswith("jogador.criado.AssinanteWebhook")


def test_reprocessar_pela_api_entrega_so_ao_que_falhou(destino):
    def handler(request):
        destino.recebidos.append(str(request.url))
        return httpx.Response(503 if "quebrado" in str(request.url) and destino.status == 503 else 200)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    app = criar_aplicacao(Broker(max_tentativas=1), lambda url: AssinanteWebhook(url, http))
    c = TestClient(app)
    c.post("/assinar", json={"topico": "t", "url": "http://saudavel/e"})
    c.post("/assinar", json={"topico": "t", "url": "http://quebrado/e"})
    destino.status = 503
    id_msg = c.post("/publicar", json={"topico": "t", "dados": {}}).json()["id"]
    destino.status = 200
    destino.recebidos.clear()

    r = c.post(f"/erros/{id_msg}/reprocessar")

    assert r.status_code == 200 and r.json() == {"reprocessadas": 1}
    assert destino.recebidos == ["http://quebrado/e"]   # o saudável não recebeu de novo
    assert c.get("/erros").json() == {"erros": []}


def test_reprocessar_id_inexistente_devolve_404(cliente):
    assert cliente.post("/erros/nao-existe/reprocessar").status_code == 404


def test_painel_e_uma_pagina_html(cliente):
    r = cliente.get("/painel")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "painel em tempo real" in r.text and "/estado" in r.text


def test_com_chave_os_dados_sao_protegidos_mas_o_painel_abre():
    app = criar_aplicacao(Broker(), lambda url: AssinanteWebhook(url), chave_api="k")
    c = TestClient(app)
    assert c.get("/painel").status_code == 200           # só código, sem dados
    assert c.get("/estado").status_code == 401
    assert c.get("/historico").status_code == 401
    assert c.post("/erros/x/reprocessar").status_code == 401
    assert c.get("/estado", headers={"X-API-Key": "k"}).status_code == 200
