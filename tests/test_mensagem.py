import pytest

from app.mensagens.topico import Topico
from app.mensagens.pedido import Pedido
from app.mensagens.resposta import Resposta


def test_pedido_herda_de_topico():
    pedido = Pedido()

    assert isinstance(pedido, Topico)


def test_resposta_herda_de_topico():
    resposta = Resposta()

    assert isinstance(resposta, Topico)


def test_topico_e_abstrato():
    with pytest.raises(TypeError):
        Topico()


def test_pedido_possui_metodos_do_uml():
    pedido = Pedido()

    assert hasattr(pedido, "envioDeMensagem")
    assert hasattr(pedido, "envioDePedido")
    assert hasattr(pedido, "envioDeNotificacao")


def test_resposta_possui_metodos_do_uml():
    resposta = Resposta()

    assert hasattr(resposta, "envioDeMensagem")
    assert hasattr(resposta, "respostaMensagem")
    assert hasattr(resposta, "enviaDLO")
