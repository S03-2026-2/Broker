import pytest

from app.comum.erros import FilaVaziaError
from app.comum.mensagem import Mensagem
from app.servidor.fila import Fila


def msg(n):
    return Mensagem.criar("t", {"n": n})


def test_fila_exige_nome():
    with pytest.raises(ValueError):
        Fila("  ")


def test_fila_comeca_vazia():
    fila = Fila("f")
    assert fila.esta_vazia() and len(fila) == 0


def test_ordem_fifo():
    fila = Fila("f")
    a, b = msg(1), msg(2)
    fila.enfileirar(a)
    fila.enfileirar(b)
    assert fila.retirar() is a
    assert fila.retirar() is b


def test_retirar_de_fila_vazia_lanca_erro():
    with pytest.raises(FilaVaziaError):
        Fila("f").retirar()


def test_listar_pendentes_nao_remove_nem_expoe_a_fila_interna():
    fila = Fila("f")
    fila.enfileirar(msg(1))
    lista = fila.listar_pendentes()
    lista.clear()
    assert len(fila) == 1
