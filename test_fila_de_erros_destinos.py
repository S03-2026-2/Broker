from app.comum.mensagem import Mensagem
from app.servidor.fila_de_erros import FilaDeErros


def test_registra_o_destino_da_falha():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    fe.registrar_falha(m, "offline", destino="t.App.1")
    assert fe.destinos_da_falha(m.id) == ["t.App.1"]


def test_destino_e_opcional():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    fe.registrar_falha(m, "offline")
    assert fe.destinos_da_falha(m.id) == [None]


def test_retirar_todas_devolve_as_falhas_e_esvazia():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    outra = Mensagem.criar("t", {})
    fe.registrar_falha(m, "a", "dest1")
    fe.registrar_falha(m, "b", "dest2")
    fe.registrar_falha(outra, "c", "dest1")

    retiradas = fe.retirar_todas(m.id)

    assert [(motivo, destino) for _, motivo, destino in retiradas] == [("a", "dest1"), ("b", "dest2")]
    assert all(x[0] is m for x in retiradas)
    assert fe.listar_pendentes() == [outra]
    assert fe.motivos_da_falha(m.id) == []


def test_retirar_todas_de_id_inexistente_devolve_lista_vazia():
    assert FilaDeErros().retirar_todas("nada") == []


def test_reprocessar_mantem_o_destino_das_demais_falhas():
    fe = FilaDeErros()
    m = Mensagem.criar("t", {})
    fe.registrar_falha(m, "a", "dest1")
    fe.registrar_falha(m, "b", "dest2")
    fe.reprocessar(m.id)
    assert fe.destinos_da_falha(m.id) == ["dest2"]
