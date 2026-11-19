"""Falhas reais entre processos: erro no receptor, recuperação, timeout e duplicata."""
import httpx

from app.cliente.cliente_http import ClienteHttpBroker
from app.cliente.publicador import Publicador
from tests.system.ajudantes import ambiente, esperar


def tipos_da_mensagem(url_broker, id_msg):
    eventos = httpx.get(f"{url_broker}/historico").json()["eventos"]
    return [e["tipo"] for e in eventos if e["mensagem"] == id_msg]


def test_receptor_com_erro_vai_para_fila_de_erros_e_e_reprocessado_depois():
    with ambiente() as (broker, receptor):
        cliente = ClienteHttpBroker(broker)
        httpx.post(f"{receptor}/simulacao", json={"modo": "erro"})
        cliente.assinar_por_url("jogador.criado", f"{receptor}/eventos")

        id_msg = Publicador("jogadores", cliente).publicar("jogador.criado", {"jogador_id": 42})
        assert esperar(lambda: "falhou" in tipos_da_mensagem(broker, id_msg))

        httpx.post(f"{broker}/reentregas")
        httpx.post(f"{broker}/reentregas")            # 3ª tentativa: esgota
        erros = httpx.get(f"{broker}/erros").json()["erros"]
        assert [e["id"] for e in erros] == [id_msg]
        assert "503" in erros[0]["motivos"][0]
        assert httpx.get(f"{receptor}/eventos").json() == []

        httpx.post(f"{receptor}/simulacao", json={"modo": "normal"})   # o receptor se recupera
        r = httpx.post(f"{broker}/erros/{id_msg}/reprocessar")
        assert r.json() == {"reprocessadas": 1}

        eventos = httpx.get(f"{receptor}/eventos").json()
        assert [e["id"] for e in eventos] == [id_msg]
        assert httpx.get(f"{broker}/erros").json() == {"erros": []}
        assert tipos_da_mensagem(broker, id_msg) == [
            "publicada", "falhou", "falhou", "esgotada", "reprocessada", "entregue"]


def test_timeout_gera_reentrega_e_o_receptor_ignora_a_duplicata():
    with ambiente(env_broker={"BROKER_TIMEOUT_WEBHOOK": 1}) as (broker, receptor):
        cliente = ClienteHttpBroker(broker)
        httpx.post(f"{receptor}/simulacao", json={"modo": "lento", "atraso_s": 2.5})
        cliente.assinar_por_url("jogador.criado", f"{receptor}/eventos")

        id_msg = Publicador("jogadores", cliente).publicar("jogador.criado", {"jogador_id": 7})

        # O Broker desiste após 1 s (timeout), mas o receptor termina o processamento depois.
        assert esperar(lambda: "falhou" in tipos_da_mensagem(broker, id_msg))
        falhou = [e for e in httpx.get(f"{broker}/historico").json()["eventos"]
                  if e["tipo"] == "falhou"][0]
        assert "Timeout" in falhou["detalhe"]
        assert esperar(lambda: len(httpx.get(f"{receptor}/eventos").json()) == 1, limite=8)

        httpx.post(f"{receptor}/simulacao", json={"modo": "normal"})
        assert httpx.post(f"{broker}/reentregas").json() == {"entregues": 1}

        # Entregue de novo (at-least-once), mas o receptor reconheceu o id e não duplicou.
        assert len(httpx.get(f"{receptor}/eventos").json()) == 1
        assert tipos_da_mensagem(broker, id_msg)[-1] == "entregue"


def test_painel_e_estado_acompanham_um_receptor_fora_do_ar():
    with ambiente() as (broker, receptor):
        cliente = ClienteHttpBroker(broker)
        cliente.assinar_por_url("jogador.criado", f"{receptor}/eventos")
        httpx.post(f"{receptor}/simulacao", json={"modo": "erro"})
        Publicador("jogadores", cliente).publicar("jogador.criado", {"jogador_id": 1})
        assert esperar(lambda: httpx.get(f"{broker}/estado").json()["totais"]["falhas"] == 1)

        estado = httpx.get(f"{broker}/estado").json()
        assinante = estado["topicos"][0]["assinantes"][0]
        assert assinante["pendentes"] == 1 and assinante["destino"].endswith("/eventos")
        assert httpx.get(f"{broker}/painel").status_code == 200
