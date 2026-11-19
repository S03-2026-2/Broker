"""Broker + Topico + Assinatura + Fila + FilaDeErros reais, juntos."""
from app.comum.mensagem import Mensagem
from app.servidor.broker import Broker
from tests.doubles import AssinanteGravador, AssinanteInstavel, AssinanteSempreFalha


def test_assinante_que_se_recupera_recebe_na_reentrega():
    broker = Broker(max_tentativas=3)
    instavel = AssinanteInstavel(falhas_antes_de_funcionar=2)
    broker.assinar("t", instavel)
    m = Mensagem.criar("t", {"x": 1})

    broker.publicar(m)                       # tentativa 1: falha
    assert broker.processar_pendentes() == 0  # tentativa 2: falha
    assert broker.processar_pendentes() == 1  # tentativa 3: sucesso

    assert instavel.recebidas == [m]
    assert broker.fila_de_erros.esta_vazia()


def test_tentativas_esgotadas_vao_para_a_fila_de_erros():
    broker = Broker(max_tentativas=3)
    quebrado = AssinanteSempreFalha()
    broker.assinar("t", quebrado)
    m = Mensagem.criar("t", {})

    broker.publicar(m)
    broker.processar_pendentes()
    broker.processar_pendentes()

    assert quebrado.chamadas == 3
    assert broker.fila_de_erros.listar_pendentes() == [m]
    assert "ConnectionError" in broker.fila_de_erros.motivos_da_falha(m.id)[0]


def test_nao_ha_novas_tentativas_depois_de_esgotar():
    broker = Broker(max_tentativas=2)
    quebrado = AssinanteSempreFalha()
    broker.assinar("t", quebrado)
    broker.publicar(Mensagem.criar("t", {}))
    for _ in range(5):
        broker.processar_pendentes()
    assert quebrado.chamadas == 2


def test_assinante_com_falha_nao_impede_os_outros():
    broker = Broker()
    quebrado, saudavel = AssinanteSempreFalha(), AssinanteGravador()
    broker.assinar("t", quebrado)
    broker.assinar("t", saudavel)
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    assert saudavel.recebidas == [m]


def test_assinatura_reativada_recebe_o_que_ficou_pendente():
    broker = Broker()
    a = AssinanteGravador()
    broker.assinar("t", a)
    assinatura = broker._topicos["t"].assinaturas[0]
    assinatura.ativa = False
    m = Mensagem.criar("t", {})
    broker.publicar(m)

    assinatura.ativa = True
    assert broker.processar_pendentes() == 1
    assert a.recebidas == [m]


def test_reprocessar_da_fila_de_erros_permite_republicar():
    broker = Broker(max_tentativas=1)
    instavel = AssinanteInstavel(falhas_antes_de_funcionar=1)
    broker.assinar("t", instavel)
    m = Mensagem.criar("t", {})
    broker.publicar(m)                       # falha e esgota (max 1)
    assert not broker.fila_de_erros.esta_vazia()

    reenviada = broker.fila_de_erros.reprocessar(m.id)
    broker.publicar(reenviada)               # agora o assinante já se recuperou

    assert instavel.recebidas == [m]
    assert broker.fila_de_erros.esta_vazia()
