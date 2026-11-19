import pytest

from app.comum.erros import MensagemNaoEncontradaError
from app.comum.mensagem import Mensagem
from app.servidor.broker import Broker
from tests.doubles import AssinanteGravador, AssinanteInstavel, AssinanteSempreFalha


def tipos(broker, mensagem=None):
    return [e["tipo"] for e in broker.registro.listar()
            if mensagem is None or e["mensagem"] == mensagem.id]


# ---- tópicos passam a existir ao publicar --------------------------------
def test_topico_publicado_sem_assinantes_ja_aparece_na_listagem():
    broker = Broker()
    broker.publicar(Mensagem.criar("jogador.criado", {}))
    assert broker.listar_topicos() == ["jogador.criado"]


def test_publicacao_sem_assinantes_e_registrada_como_descartada():
    broker = Broker()
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    assert tipos(broker, m) == ["publicada", "descartada"]


def test_publicar_e_assinar_o_mesmo_topico_nao_duplica_o_topico():
    broker = Broker()
    broker.publicar(Mensagem.criar("t", {}))
    broker.assinar("t", AssinanteGravador())
    assert broker.listar_topicos() == ["t"]


# ---- histórico do caminho feliz e do retry --------------------------------
def test_entrega_com_sucesso_gera_publicada_e_entregue():
    broker = Broker()
    broker.assinar("t", AssinanteGravador())
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    assert tipos(broker, m) == ["publicada", "entregue"]


def test_historico_completo_de_retry_ate_a_fila_de_erros():
    broker = Broker(max_tentativas=3)
    broker.assinar("t", AssinanteSempreFalha())
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    broker.processar_pendentes()
    broker.processar_pendentes()
    assert tipos(broker, m) == ["publicada", "falhou", "falhou", "esgotada"]


def test_historico_de_retry_que_se_recupera():
    broker = Broker(max_tentativas=3)
    broker.assinar("t", AssinanteInstavel(falhas_antes_de_funcionar=2))
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    broker.processar_pendentes()
    broker.processar_pendentes()
    assert tipos(broker, m) == ["publicada", "falhou", "falhou", "entregue"]
    entregue = [e for e in broker.registro.listar() if e["tipo"] == "entregue"][0]
    assert entregue["tentativa"] == 3 and "3 tentativas" in entregue["detalhe"]


def test_falha_registra_a_tentativa_e_o_erro():
    broker = Broker(max_tentativas=3)
    broker.assinar("t", AssinanteSempreFalha())
    broker.publicar(Mensagem.criar("t", {}))
    falhou = [e for e in broker.registro.listar() if e["tipo"] == "falhou"][0]
    assert "tentativa 1/3" in falhou["detalhe"] and "ConnectionError" in falhou["detalhe"]


def test_assinatura_inativa_registra_retida():
    broker = Broker()
    broker.assinar("t", AssinanteGravador())
    broker._topicos["t"].assinaturas[0].ativa = False
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    assert tipos(broker, m) == ["publicada", "retida"]


def test_mensagem_invalida_nao_gera_evento():
    broker = Broker()
    with pytest.raises(Exception):
        broker.publicar(Mensagem(topico="", dados={}))
    assert broker.registro.listar() == []


# ---- situação ----------------------------------------------------------------
def test_situacao_traz_contadores_filas_e_totais():
    broker = Broker(max_tentativas=3)
    broker.assinar("t", AssinanteGravador())
    broker.assinar("t", AssinanteSempreFalha())
    broker.publicar(Mensagem.criar("t", {}))
    s = broker.situacao()

    topico = s["topicos"][0]
    assert topico["nome"] == "t" and topico["publicadas"] == 1
    por_destino = {a["destino"]: a for a in topico["assinantes"]}
    assert por_destino["AssinanteGravador"]["entregues"] == 1
    assert por_destino["AssinanteSempreFalha"]["falhas"] == 1
    assert por_destino["AssinanteSempreFalha"]["pendentes"] == 1
    assert s["totais"] == {"publicadas": 1, "entregues": 1, "falhas": 1, "na_fila_de_erros": 0}
    assert {"nome": "fila_de_erros", "pendentes": 0} in s["filas"]


def test_situacao_de_topico_sem_assinantes():
    broker = Broker()
    broker.publicar(Mensagem.criar("solto", {}))
    assert broker.situacao()["topicos"] == [{"nome": "solto", "publicadas": 1, "assinantes": []}]


# ---- reprocessar só o assinante que falhou ---------------------------------
def test_reprocessar_reenvia_somente_ao_assinante_que_falhou():
    broker = Broker(max_tentativas=1)
    saudavel = AssinanteGravador()
    instavel = AssinanteInstavel(falhas_antes_de_funcionar=1)
    broker.assinar("t", saudavel)
    broker.assinar("t", instavel)
    m = Mensagem.criar("t", {})
    broker.publicar(m)                       # o instável falha e esgota (max 1)
    assert len(saudavel.recebidas) == 1 and len(broker.fila_de_erros) == 1

    assert broker.reprocessar_erro(m.id) == 1

    assert len(saudavel.recebidas) == 1      # NÃO recebeu de novo
    assert instavel.recebidas == [m]         # o que falhou recebeu agora
    assert broker.fila_de_erros.esta_vazia()
    assert "reprocessada" in tipos(broker, m)


def test_reprocessar_recomeca_as_tentativas_do_zero():
    broker = Broker(max_tentativas=2)
    quebrado = AssinanteSempreFalha()
    broker.assinar("t", quebrado)
    m = Mensagem.criar("t", {})
    broker.publicar(m)
    broker.processar_pendentes()             # 2 tentativas: esgota
    assert len(broker.fila_de_erros) == 1

    broker.reprocessar_erro(m.id)            # 1ª tentativa do novo ciclo falha de novo
    assert len(broker.fila_de_erros) == 0
    broker.processar_pendentes()             # 2ª do novo ciclo: esgota outra vez
    assert len(broker.fila_de_erros) == 1
    assert quebrado.chamadas == 4


def test_reprocessar_id_inexistente_lanca_erro():
    with pytest.raises(MensagemNaoEncontradaError):
        Broker().reprocessar_erro("nao-existe")
