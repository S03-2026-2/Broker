import pytest

from app.comum.mensagem import Mensagem
from app.servidor.assinatura import Assinatura
from app.servidor.fila import Fila
from tests.doubles import AssinanteGravador, AssinanteSempreFalha


def nova(assinante, max_tentativas=3):
    return Assinatura(assinante, Fila("f"), max_tentativas)


def test_notificar_com_sucesso_entrega_e_devolve_true():
    assinante = AssinanteGravador()
    m = Mensagem.criar("t", {})
    assert nova(assinante).notificar(m) is True
    assert assinante.recebidas == [m]


def test_notificar_com_falha_devolve_false_e_guarda_o_erro():
    a = nova(AssinanteSempreFalha())
    assert a.notificar(Mensagem.criar("t", {})) is False
    assert "ConnectionError" in a.ultimo_erro


def test_assinatura_inativa_nao_chama_o_assinante():
    assinante = AssinanteGravador()
    a = nova(assinante)
    a.ativa = False
    assert a.notificar(Mensagem.criar("t", {})) is False
    assert assinante.recebidas == []


def test_conta_tentativas_ate_esgotar():
    a = nova(AssinanteSempreFalha(), max_tentativas=2)
    m = Mensagem.criar("t", {})
    a.notificar(m)
    assert a.tentativas(m) == 1 and not a.esgotou_tentativas(m)
    a.notificar(m)
    assert a.esgotou_tentativas(m)


def test_sucesso_zera_o_contador():
    a = nova(AssinanteGravador())
    m = Mensagem.criar("t", {})
    a.notificar(m)
    assert a.tentativas(m) == 0


def test_esquecer_zera_o_contador():
    a = nova(AssinanteSempreFalha())
    m = Mensagem.criar("t", {})
    a.notificar(m)
    a.esquecer(m)
    assert a.tentativas(m) == 0


def test_max_tentativas_invalido():
    with pytest.raises(ValueError):
        nova(AssinanteGravador(), max_tentativas=0)
