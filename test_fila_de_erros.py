import pytest

from app.comum.erros import MensagemNaoEncontradaError
from app.comum.mensagem import Mensagem
from app.servidor.fila import Fila
from app.servidor.fila_de_erros import FilaDeErros


def test_fila_de_erros_e_uma_fila():
    assert isinstance(FilaDeErros(), Fila)


def test_registrar_falha_guarda_mensagem_e_motivo():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    fe.registrar_falha(m, "destino offline")
    assert fe.listar_pendentes() == [m]
    assert fe.motivos_da_falha(m.id) == ["destino offline"]


def test_mesma_mensagem_pode_falhar_para_dois_assinantes():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    fe.registrar_falha(m, "a")
    fe.registrar_falha(m, "b")
    assert fe.motivos_da_falha(m.id) == ["a", "b"]
    assert len(fe) == 2


def test_reprocessar_devolve_e_remove_a_mensagem():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    fe.registrar_falha(m, "x")
    assert fe.reprocessar(m.id) is m
    assert fe.esta_vazia()
    assert fe.motivos_da_falha(m.id) == []


def test_reprocessar_mensagem_inexistente_lanca_erro():
    with pytest.raises(MensagemNaoEncontradaError):
        FilaDeErros().reprocessar("nao-existe")
