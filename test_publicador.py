import pytest

from app.cliente.publicador import Publicador
from tests.doubles import ServicoEspiao


def test_publicar_cria_mensagem_e_entrega_ao_servico():
    espiao = ServicoEspiao()
    publicador = Publicador("jogadores", espiao)
    ack = publicador.publicar("jogador.criado", {"jogador_id": 42})
    mensagem = espiao.recebidas[0]
    assert mensagem.topico == "jogador.criado"
    assert mensagem.dados == {"jogador_id": 42}
    assert ack == mensagem.id


def test_publicador_exige_identificador():
    with pytest.raises(ValueError):
        Publicador("", ServicoEspiao())
