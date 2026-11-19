from dataclasses import FrozenInstanceError

import pytest

from app.comum.mensagem import Mensagem


def test_criar_gera_id_e_data():
    m = Mensagem.criar("jogador.criado", {"jogador_id": 1})
    assert m.id and m.data_criacao is not None
    assert m.topico == "jogador.criado"
    assert m.dados == {"jogador_id": 1}


def test_ids_sao_unicos():
    ids = {Mensagem.criar("t", {}).id for _ in range(100)}
    assert len(ids) == 100


def test_criar_copia_os_dados():
    dados = {"a": 1}
    m = Mensagem.criar("t", dados)
    dados["a"] = 2
    assert m.dados == {"a": 1}


def test_mensagem_e_imutavel():
    m = Mensagem.criar("t", {})
    with pytest.raises(FrozenInstanceError):
        m.topico = "outro"


def test_validar_aceita_envelope_correto():
    assert Mensagem.criar("t", {"x": 1}).validar() is True


@pytest.mark.parametrize("topico", ["", "   ", None, 123])
def test_validar_rejeita_topico_invalido(topico):
    assert Mensagem(topico=topico, dados={}).validar() is False


def test_validar_rejeita_dados_que_nao_sao_dict():
    assert Mensagem(topico="t", dados=[1, 2]).validar() is False


def test_validar_rejeita_id_vazio():
    assert Mensagem(topico="t", dados={}, id="").validar() is False
