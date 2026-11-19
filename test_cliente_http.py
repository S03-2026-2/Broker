import json

import httpx
import pytest

from app.cliente.cliente_http import ClienteHttpBroker
from app.cliente.publicador import Publicador
from app.comum.contratos import ServicoDeInspecao, ServicoDePublicacao
from app.comum.erros import ErroDeComunicacaoError
from app.comum.mensagem import Mensagem


def cliente_com(handler, chave=None):
    http = httpx.Client(base_url="http://broker", transport=httpx.MockTransport(handler))
    return ClienteHttpBroker("http://broker", chave_api=chave, cliente=http)


def test_implementa_os_contratos_de_publicacao_e_inspecao():
    c = cliente_com(lambda r: httpx.Response(200, json={}))
    assert isinstance(c, ServicoDePublicacao) and isinstance(c, ServicoDeInspecao)


def test_publicar_envia_post_e_devolve_o_id():
    visto = {}

    def handler(request):
        visto["metodo"], visto["caminho"] = request.method, request.url.path
        visto["corpo"] = json.loads(request.content)
        return httpx.Response(202, json={"id": visto["corpo"]["id"], "status": "aceito"})

    m = Mensagem.criar("jogador.criado", {"jogador_id": 42})
    assert cliente_com(handler).publicar(m) == m.id
    assert (visto["metodo"], visto["caminho"]) == ("POST", "/publicar")
    assert visto["corpo"] == {"topico": "jogador.criado", "dados": {"jogador_id": 42}, "id": m.id}


def test_publicador_funciona_sem_alteracao_com_o_cliente_http():
    c = cliente_com(lambda r: httpx.Response(202, json={"id": json.loads(r.content)["id"]}))
    ack = Publicador("jogadores", c).publicar("t", {"x": 1})
    assert ack


def test_assinar_por_url():
    visto = {}

    def handler(request):
        visto["corpo"] = json.loads(request.content)
        return httpx.Response(201, json={})

    cliente_com(handler).assinar_por_url("t", "http://app/eventos")
    assert visto["corpo"] == {"topico": "t", "url": "http://app/eventos"}


def test_listar_topicos_e_filas():
    def handler(request):
        if request.url.path == "/topicos":
            return httpx.Response(200, json={"topicos": ["a", "b"]})
        return httpx.Response(200, json={"filas": ["f1", "fila_de_erros"]})

    c = cliente_com(handler)
    assert c.listar_topicos() == ["a", "b"]
    assert c.listar_filas() == ["f1", "fila_de_erros"]


def test_envia_a_chave_de_api():
    visto = {}

    def handler(request):
        visto["chave"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"topicos": []})

    cliente_com(handler, chave="segredo").listar_topicos()
    assert visto["chave"] == "segredo"


@pytest.mark.parametrize("status", [401, 409, 422, 500])
def test_resposta_de_erro_vira_excecao(status):
    with pytest.raises(ErroDeComunicacaoError, match=str(status)):
        cliente_com(lambda r: httpx.Response(status, text="falhou")).listar_topicos()


def test_broker_fora_do_ar_vira_excecao():
    def handler(request):
        raise httpx.ConnectError("recusada")

    with pytest.raises(ErroDeComunicacaoError):
        cliente_com(handler).listar_topicos()
