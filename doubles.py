"""Dublês de teste: aplicações falsas e um espião do serviço de publicação."""
from app.comum.contratos import Assinante, ServicoDePublicacao
from app.comum.mensagem import Mensagem


class AssinanteGravador(Assinante):
    """Guarda tudo o que recebe."""

    def __init__(self):
        self.recebidas: list[Mensagem] = []

    def receber(self, mensagem):
        self.recebidas.append(mensagem)


class AssinanteInstavel(Assinante):
    """Falha N vezes e depois passa a funcionar."""

    def __init__(self, falhas_antes_de_funcionar: int):
        self._restantes = falhas_antes_de_funcionar
        self.chamadas = 0
        self.recebidas: list[Mensagem] = []

    def receber(self, mensagem):
        self.chamadas += 1
        if self._restantes > 0:
            self._restantes -= 1
            raise ConnectionError("destino offline")
        self.recebidas.append(mensagem)


class AssinanteSempreFalha(Assinante):
    def __init__(self):
        self.chamadas = 0

    def receber(self, mensagem):
        self.chamadas += 1
        raise ConnectionError("destino offline")


class ServicoEspiao(ServicoDePublicacao):
    """Substitui o Broker nos testes do Publicador."""

    def __init__(self):
        self.recebidas: list[Mensagem] = []

    def publicar(self, mensagem):
        self.recebidas.append(mensagem)
        return mensagem.id
