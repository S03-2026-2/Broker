"""Vínculo entre um tópico e um assinante, com sua fila de pendentes."""
from __future__ import annotations

from app.comum.contratos import Assinante
from app.comum.mensagem import Mensagem
from app.servidor.fila import Fila


class Assinatura:
    def __init__(self, assinante: Assinante, fila: Fila, max_tentativas: int = 3) -> None:
        if max_tentativas < 1:
            raise ValueError("max_tentativas deve ser pelo menos 1.")
        self._assinante = assinante
        self._fila = fila
        self._max_tentativas = max_tentativas
        self._tentativas: dict[str, int] = {}
        self._ultimo_erro: str | None = None
        self.ativa = True

    @property
    def assinante(self) -> Assinante:
        return self._assinante

    @property
    def fila(self) -> Fila:
        return self._fila

    @property
    def nome(self) -> str:
        return self._fila.nome

    @property
    def ultimo_erro(self) -> str | None:
        return self._ultimo_erro

    def notificar(self, mensagem: Mensagem) -> bool:
        """Tenta entregar. True se o assinante processou; False se falhou ou está inativa."""
        if not self.ativa:
            return False
        self._tentativas[mensagem.id] = self._tentativas.get(mensagem.id, 0) + 1
        try:
            self._assinante.receber(mensagem)
        except Exception as erro:  # o assinante é código de terceiros
            self._ultimo_erro = f"{type(erro).__name__}: {erro}"
            return False
        self._tentativas.pop(mensagem.id, None)
        return True

    def tentativas(self, mensagem: Mensagem) -> int:
        return self._tentativas.get(mensagem.id, 0)

    def esgotou_tentativas(self, mensagem: Mensagem) -> bool:
        return self.tentativas(mensagem) >= self._max_tentativas

    def esquecer(self, mensagem: Mensagem) -> None:
        self._tentativas.pop(mensagem.id, None)
