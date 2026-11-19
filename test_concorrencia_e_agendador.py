import threading
import time

import httpx
from fastapi.testclient import TestClient

from app.api.agendador import AgendadorDeReentrega
from app.api.aplicacao import criar_aplicacao
from app.api.assinante_webhook import AssinanteWebhook
from app.comum.mensagem import Mensagem
from app.servidor.broker import Broker
from tests.doubles import AssinanteGravador


def test_varias_threads_publicando_nao_perdem_mensagens():
    broker = Broker()
    gravador = AssinanteGravador()
    broker.assinar("t", gravador)

    def publicar_varias():
        for _ in range(50):
            broker.publicar(Mensagem.criar("t", {}))

    threads = [threading.Thread(target=publicar_varias) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(gravador.recebidas) == 400
    assert len({m.id for m in gravador.recebidas}) == 400


def test_assinar_e_publicar_ao_mesmo_tempo_nao_quebra():
    broker = Broker()
    erros = []

    def assinar_varios(prefixo):
        try:
            for i in range(30):
                broker.assinar(f"{prefixo}.{i}", AssinanteGravador())
        except Exception as e:  # pragma: no cover
            erros.append(e)

    def publicar_varias():
        try:
            for i in range(300):
                broker.publicar(Mensagem.criar("a.1", {}))
        except Exception as e:  # pragma: no cover
            erros.append(e)

    threads = [threading.Thread(target=assinar_varios, args=(p,)) for p in "abc"]
    threads.append(threading.Thread(target=publicar_varias))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert erros == []
    assert len(broker.listar_topicos()) == 90


def test_agendador_reentrega_sozinho_quando_a_api_esta_no_ar():
    """Com a API em execução, o assinante que volta recebe sem ninguém chamar /reentregas."""
    estado = {"status": 503, "recebidos": 0}

    def handler(request):
        if estado["status"] == 200:
            estado["recebidos"] += 1
        return httpx.Response(estado["status"])

    broker = Broker(max_tentativas=50)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    agendador = AgendadorDeReentrega(broker.processar_pendentes, intervalo_s=0.02)
    app = criar_aplicacao(broker, lambda url: AssinanteWebhook(url, http), agendador=agendador)

    with TestClient(app) as cliente:        # entrar no 'with' liga o agendador
        cliente.post("/assinar", json={"topico": "t", "url": "http://x/e"})
        cliente.post("/publicar", json={"topico": "t", "dados": {}})
        assert agendador.ativo
        estado["status"] = 200              # o assinante volta
        fim = time.time() + 3
        while estado["recebidos"] == 0 and time.time() < fim:
            time.sleep(0.02)

    assert estado["recebidos"] == 1
    assert not agendador.ativo              # saiu do 'with': agendador parado
