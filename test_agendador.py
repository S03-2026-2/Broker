import threading
import time

from app.api.agendador import AgendadorDeReentrega


def esperar(condicao, limite=2.0):
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(0.005)
    return False


def test_chama_a_acao_periodicamente_e_para():
    chamadas = []
    agendador = AgendadorDeReentrega(lambda: chamadas.append(1), intervalo_s=0.01)
    agendador.iniciar()
    assert agendador.ativo
    assert esperar(lambda: len(chamadas) >= 3)
    agendador.parar()
    assert not agendador.ativo
    total = len(chamadas)
    time.sleep(0.05)
    assert len(chamadas) == total  # parou de verdade


def test_erro_em_uma_rodada_nao_derruba_o_agendador():
    chamadas = []

    def acao():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("falha pontual")

    agendador = AgendadorDeReentrega(acao, intervalo_s=0.01)
    agendador.iniciar()
    assert esperar(lambda: len(chamadas) >= 3)
    agendador.parar()


def test_iniciar_duas_vezes_nao_cria_duas_threads():
    agendador = AgendadorDeReentrega(lambda: None, intervalo_s=0.01)
    agendador.iniciar()
    n = threading.active_count()
    agendador.iniciar()
    assert threading.active_count() == n
    agendador.parar()
