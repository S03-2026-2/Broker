import pytest

from app.comum.contratos import ServicoDeAssinatura, ServicoDeInspecao, ServicoDePublicacao
from app.comum.erros import AssinaturaDuplicadaError, MensagemInvalidaError
from app.comum.mensagem import Mensagem
from app.servidor.broker import Broker
from tests.doubles import AssinanteGravador, AssinanteSempreFalha


def test_broker_implementa_as_tres_interfaces():
    broker = Broker()
    assert isinstance(broker, ServicoDePublicacao)
    assert isinstance(broker, ServicoDeAssinatura)
    assert isinstance(broker, ServicoDeInspecao)


def test_publicar_entrega_a_todos_os_assinantes():
    broker = Broker()
    a, b = AssinanteGravador(), AssinanteGravador()
    broker.assinar("t", a)
    broker.assinar("t", b)
    m = Mensagem.criar("t", {"x": 1})
    assert broker.publicar(m) == m.id
    assert a.recebidas == [m] and b.recebidas == [m]


def test_publicar_nao_entrega_para_outro_topico():
    broker = Broker()
    a = AssinanteGravador()
    broker.assinar("a", a)
    broker.publicar(Mensagem.criar("b", {}))
    assert a.recebidas == []


def test_publicar_em_topico_sem_assinantes_aceita_e_descarta():
    m = Mensagem.criar("ninguem.ouve", {})
    assert Broker().publicar(m) == m.id


def test_publicar_mensagem_invalida_lanca_erro():
    with pytest.raises(MensagemInvalidaError):
        Broker().publicar(Mensagem(topico="", dados={}))


def test_assinar_mesmo_assinante_duas_vezes_lanca_erro():
    broker = Broker()
    a = AssinanteGravador()
    broker.assinar("t", a)
    with pytest.raises(AssinaturaDuplicadaError):
        broker.assinar("t", a)


def test_assinar_exige_nome_de_topico():
    with pytest.raises(ValueError):
        Broker().assinar("  ", AssinanteGravador())


def test_listar_topicos_e_filas():
    broker = Broker()
    broker.assinar("jogador.criado", AssinanteGravador())
    broker.assinar("troca.criada", AssinanteGravador())
    assert broker.listar_topicos() == ["jogador.criado", "troca.criada"]
    filas = broker.listar_filas()
    assert len(filas) == 3 and "fila_de_erros" in filas


def test_falha_na_primeira_entrega_deixa_mensagem_pendente():
    broker = Broker(max_tentativas=3)
    broker.assinar("t", AssinanteSempreFalha())
    broker.publicar(Mensagem.criar("t", {}))
    fila_do_assinante = broker.listar_filas()[0]
    assert fila_do_assinante.startswith("t.AssinanteSempreFalha")
    assert broker.fila_de_erros.esta_vazia()


def test_assinatura_inativa_acumula_na_fila():
    broker = Broker()
    a = AssinanteGravador()
    broker.assinar("t", a)
    broker._topicos["t"].assinaturas[0].ativa = False
    broker.publicar(Mensagem.criar("t", {}))
    assert a.recebidas == []
    assert len(broker._topicos["t"].assinaturas[0].fila) == 1
