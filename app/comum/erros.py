"""Exceções do domínio do Broker."""


class BrokerError(Exception):
    """Base de todos os erros do Broker."""


class MensagemInvalidaError(BrokerError):
    """A mensagem não passou na validação do envelope."""


class FilaVaziaError(BrokerError):
    """Tentativa de retirar uma mensagem de uma fila vazia."""


class AssinaturaDuplicadaError(BrokerError):
    """O mesmo assinante já está inscrito neste tópico."""


class MensagemNaoEncontradaError(BrokerError):
    """A mensagem pedida não existe na fila."""
