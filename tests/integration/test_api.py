"""API real + Broker real; só o envio HTTP ao assinante é simulado."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.aplicacao import criar_aplicacao
from app.api.assinante_webhook import AssinanteWebhook
from app.servidor.broker import Broker


class Destinos:
    """Controla como cada URL de assinante responde."""

    def __init__(self):
        self.recebidos = []          # (url, corpo)
        self.status = {}             # url -> código de resposta (padrão 200)

    def handler(self, request):
        import json
        url = str(request.url)
        self.recebidos.append((url, json.loads(request.content)))
        return httpx.Response(self.status.get(url, 200))


@pytest.fixture
def destinos():
    return Destinos()


@pytest.fixture
def broker():
    return Broker(max_tentativas=3)


@pytest.fixture
def cliente(broker, destinos):
    http = httpx.Client(transport=httpx.MockTransport(destinos.handler))
    app = criar_aplicacao(broker, lambda url: AssinanteWebhook(url, http))
    return TestClient(app)


URL = "http://distribuicao/eventos"


def assinar(cliente, topico="jogador.criado", url=URL):
    return cliente.post("/assinar", json={"topico": topico, "url": url})


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_assinar_devolve_201(cliente):
    r = assinar(cliente)
    assert r.status_code == 201
    assert r.json()["topico"] == "jogador.criado"


def test_publicar_devolve_202_com_id_e_entrega_ao_assinante(cliente, destinos):
    assinar(cliente)
    r = cliente.post("/publicar", json={"topico": "jogador.criado", "dados": {"jogador_id": 42}})
    assert r.status_code == 202
    corpo = r.json()
    assert corpo["status"] == "aceito" and corpo["id"]
    (url, recebido), = destinos.recebidos
    assert url == URL
    assert recebido["id"] == corpo["id"]
    assert recebido["dados"] == {"jogador_id": 42}


def test_publicar_respeita_o_id_informado(cliente):
    r = cliente.post("/publicar", json={"topico": "t", "dados": {}, "id": "abc123"})
    assert r.json()["id"] == "abc123"


def test_publicar_sem_assinantes_e_aceito(cliente, destinos):
    r = cliente.post("/publicar", json={"topico": "ninguem.ouve", "dados": {}})
    assert r.status_code == 202 and destinos.recebidos == []


@pytest.mark.parametrize("corpo", [
    {"dados": {}},                       # sem tópico
    {"topico": "", "dados": {}},         # tópico vazio
    {"topico": "   ", "dados": {}},      # tópico só com espaços
    {"topico": "t"},                     # sem dados
    {"topico": "t", "dados": [1, 2]},    # dados não é objeto
])
def test_publicar_invalido_devolve_422(cliente, corpo):
    assert cliente.post("/publicar", json=corpo).status_code == 422


def test_assinar_mesma_url_duas_vezes_devolve_409(cliente):
    assinar(cliente)
    assert assinar(cliente).status_code == 409


@pytest.mark.parametrize("corpo", [
    {"topico": "t", "url": "nao-e-url"},
    {"topico": "t", "url": "ftp://x/y"},
    {"topico": "t"},
    {"url": URL},
    {"topico": "   ", "url": URL},
])
def test_assinar_invalido_devolve_422(cliente, corpo):
    assert cliente.post("/assinar", json=corpo).status_code == 422


def test_topicos_e_filas(cliente):
    assinar(cliente, "jogador.criado")
    assinar(cliente, "troca.criada", "http://trocas/eventos")
    assert cliente.get("/topicos").json() == {"topicos": ["jogador.criado", "troca.criada"]}
    filas = cliente.get("/filas").json()["filas"]
    assert len(filas) == 3 and "fila_de_erros" in filas


def test_assinante_indisponivel_e_reentregue(cliente, destinos):
    assinar(cliente)
    destinos.status[URL] = 503
    cliente.post("/publicar", json={"topico": "jogador.criado", "dados": {"jogador_id": 1}})
    assert cliente.post("/reentregas").json() == {"entregues": 0}

    destinos.status[URL] = 200                      # assinante voltou
    assert cliente.post("/reentregas").json() == {"entregues": 1}
    assert cliente.get("/erros").json() == {"erros": []}


def test_tentativas_esgotadas_aparecem_em_erros(cliente, destinos):
    assinar(cliente)
    destinos.status[URL] = 503
    r = cliente.post("/publicar", json={"topico": "jogador.criado", "dados": {"jogador_id": 7}})
    cliente.post("/reentregas")
    cliente.post("/reentregas")                     # 3ª tentativa: esgota

    erros = cliente.get("/erros").json()["erros"]
    assert len(erros) == 1
    assert erros[0]["id"] == r.json()["id"]
    assert erros[0]["dados"] == {"jogador_id": 7}
    assert "503" in erros[0]["motivos"][0]


def test_assinante_com_falha_nao_impede_os_outros(cliente, destinos):
    assinar(cliente, url="http://quebrado/eventos")
    assinar(cliente, url="http://saudavel/eventos")
    destinos.status["http://quebrado/eventos"] = 500
    cliente.post("/publicar", json={"topico": "jogador.criado", "dados": {}})
    urls = [u for u, _ in destinos.recebidos]
    assert "http://saudavel/eventos" in urls


# ---- chave de API ----------------------------------------------------------
@pytest.fixture
def cliente_com_chave(broker, destinos):
    http = httpx.Client(transport=httpx.MockTransport(destinos.handler))
    app = criar_aplicacao(broker, lambda url: AssinanteWebhook(url, http), chave_api="segredo")
    return TestClient(app)


@pytest.mark.parametrize("metodo,caminho", [
    ("post", "/publicar"), ("post", "/assinar"), ("get", "/topicos"),
    ("get", "/filas"), ("get", "/erros"), ("post", "/reentregas"),
])
def test_sem_chave_devolve_401(cliente_com_chave, metodo, caminho):
    r = getattr(cliente_com_chave, metodo)(caminho)
    assert r.status_code == 401


def test_chave_errada_devolve_401(cliente_com_chave):
    r = cliente_com_chave.get("/topicos", headers={"X-API-Key": "errada"})
    assert r.status_code == 401


def test_chave_correta_libera(cliente_com_chave):
    r = cliente_com_chave.get("/topicos", headers={"X-API-Key": "segredo"})
    assert r.status_code == 200


def test_saude_nao_exige_chave(cliente_com_chave):
    assert cliente_com_chave.get("/saude").status_code == 200


def test_cliente_http_de_ponta_a_ponta_contra_a_api(broker, destinos):
    """ClienteHttpBroker + Publicador falando com a API (em memória)."""
    from app.cliente.cliente_http import ClienteHttpBroker
    from app.cliente.publicador import Publicador

    http_saida = httpx.Client(transport=httpx.MockTransport(destinos.handler))
    app = criar_aplicacao(broker, lambda url: AssinanteWebhook(url, http_saida), chave_api="k")
    cliente_http = ClienteHttpBroker("http://testserver", chave_api="k", cliente=TestClient(app))

    cliente_http.assinar_por_url("jogador.criado", URL)
    ack = Publicador("jogadores", cliente_http).publicar("jogador.criado", {"jogador_id": 5})

    assert destinos.recebidos[0][1]["id"] == ack
    assert cliente_http.listar_topicos() == ["jogador.criado"]
