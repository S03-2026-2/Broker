import json

import httpx
import pytest

from app.api.assinante_webhook import AssinanteWebhook
from app.comum.contratos import Assinante
from app.comum.erros import ErroDeComunicacaoError
from app.comum.mensagem import Mensagem


def webhook_com(handler, url="http://destino/eventos"):
    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    return AssinanteWebhook(url, cliente)


def test_e_um_assinante():
    assert isinstance(AssinanteWebhook("http://x/"), Assinante)


def test_envia_o_envelope_em_json_por_post():
    capturado = {}

    def handler(request):
        capturado["metodo"] = request.method
        capturado["url"] = str(request.url)
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    m = Mensagem.criar("jogador.criado", {"jogador_id": 42})
    webhook_com(handler).receber(m)

    assert capturado["metodo"] == "POST"
    assert capturado["url"] == "http://destino/eventos"
    assert capturado["corpo"]["id"] == m.id
    assert capturado["corpo"]["topico"] == "jogador.criado"
    assert capturado["corpo"]["dados"] == {"jogador_id": 42}
    assert "data_criacao" in capturado["corpo"]


@pytest.mark.parametrize("status", [200, 201, 204])
def test_qualquer_2xx_e_sucesso(status):
    webhook_com(lambda r: httpx.Response(status)).receber(Mensagem.criar("t", {}))


@pytest.mark.parametrize("status", [301, 400, 404, 500, 503])
def test_resposta_fora_de_2xx_vira_erro(status):
    with pytest.raises(ErroDeComunicacaoError, match=str(status)):
        webhook_com(lambda r: httpx.Response(status)).receber(Mensagem.criar("t", {}))


def test_falha_de_conexao_vira_erro():
    def handler(request):
        raise httpx.ConnectError("recusada")

    with pytest.raises(ErroDeComunicacaoError, match="http://destino/eventos"):
        webhook_com(handler).receber(Mensagem.criar("t", {}))


def test_timeout_vira_erro():
    def handler(request):
        raise httpx.ReadTimeout("lento")

    with pytest.raises(ErroDeComunicacaoError):
        webhook_com(handler).receber(Mensagem.criar("t", {}))


def test_mesma_url_e_o_mesmo_assinante():
    assert AssinanteWebhook("http://a/") == AssinanteWebhook("http://a/")
    assert AssinanteWebhook("http://a/") != AssinanteWebhook("http://b/")
    assert len({AssinanteWebhook("http://a/"), AssinanteWebhook("http://a/")}) == 1
