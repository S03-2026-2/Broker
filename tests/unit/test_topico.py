import pytest

from app.comum.erros import AssinaturaDuplicadaError
from app.servidor.assinatura import Assinatura
from app.servidor.fila import Fila
from app.servidor.topico import Topico
from tests.doubles import AssinanteGravador


def nova_assinatura(assinante=None):
    return Assinatura(assinante or AssinanteGravador(), Fila("f"))


def test_topico_exige_nome():
    with pytest.raises(ValueError):
        Topico("")


def test_adicionar_e_listar_assinantes():
    topico = Topico("jogador.criado")
    a = AssinanteGravador()
    topico.adicionar_assinatura(nova_assinatura(a))
    assert topico.listar_assinantes() == [a]


def test_mesmo_assinante_duas_vezes_e_rejeitado():
    topico = Topico("t")
    a = AssinanteGravador()
    topico.adicionar_assinatura(nova_assinatura(a))
    with pytest.raises(AssinaturaDuplicadaError):
        topico.adicionar_assinatura(nova_assinatura(a))


def test_remover_assinatura():
    topico = Topico("t")
    assinatura = nova_assinatura()
    topico.adicionar_assinatura(assinatura)
    topico.remover_assinatura(assinatura)
    assert topico.listar_assinantes() == []


def test_remover_assinatura_inexistente_nao_da_erro():
    Topico("t").remover_assinatura(nova_assinatura())


def test_assinaturas_expostas_nao_permitem_alterar_o_topico():
    topico = Topico("t")
    assert isinstance(topico.assinaturas, tuple)
