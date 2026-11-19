from app.comum.mensagem import Mensagem
from app.servidor.assinatura import Assinatura, ResultadoDaTentativa
from app.servidor.fila import Fila
from tests.doubles import AssinanteGravador, AssinanteInstavel, AssinanteSempreFalha


def nova(assinante, max_tentativas=3):
    return Assinatura(assinante, Fila("f"), max_tentativas)


def test_tentar_devolve_o_numero_da_tentativa_e_o_erro():
    a = nova(AssinanteSempreFalha())
    m = Mensagem.criar("t", {})
    r1, r2 = a.tentar(m), a.tentar(m)
    assert (r1.sucesso, r1.tentativa) == (False, 1)
    assert (r2.sucesso, r2.tentativa) == (False, 2)
    assert "ConnectionError" in r2.erro and "destino offline" in r2.erro


def test_tentar_com_sucesso_informa_quantas_tentativas_foram_necessarias():
    a = nova(AssinanteInstavel(falhas_antes_de_funcionar=2))
    m = Mensagem.criar("t", {})
    a.tentar(m)
    a.tentar(m)
    r = a.tentar(m)
    assert r == ResultadoDaTentativa(True, 3, None)


def test_contadores_de_entregas_e_falhas():
    a = nova(AssinanteInstavel(falhas_antes_de_funcionar=1))
    m = Mensagem.criar("t", {})
    a.tentar(m)
    a.tentar(m)
    assert (a.falhas, a.entregues) == (1, 1)


def test_assinatura_inativa_nao_conta_tentativa():
    assinante = AssinanteGravador()
    a = nova(assinante)
    a.ativa = False
    r = a.tentar(Mensagem.criar("t", {}))
    assert (r.sucesso, r.tentativa) == (False, 0)
    assert (a.falhas, a.entregues) == (0, 0)


def test_expoe_o_limite_de_tentativas():
    assert nova(AssinanteGravador(), max_tentativas=5).max_tentativas == 5
