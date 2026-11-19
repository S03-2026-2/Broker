"""Vínculo entre um tópico e um assinante, com sua fila de pendentes."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from app.comum.contratos import Assinante
from app.comum.mensagem import Mensagem
from app.servidor.fila import Fila


@dataclass(frozen=True)
class ResultadoDaTentativa:
    sucesso: bool
    tentativa: int          # número da tentativa que acabou de ser feita
    erro: str | None = None


class Assinatura:
    def __init__(self, assinante: Assinante, fila: Fila, max_tentativas: int = 3) -> None:
        if max_tentativas < 1:
            raise ValueError("max_tentativas deve ser pelo menos 1.")
        self._assinante = assinante
        self._fila = fila
        self._max_tentativas = max_tentativas
        self._tentativas: dict[str, int] = {}
        self._ultimo_erro: str | None = None
        self._entregues = 0
        self._falhas = 0
        self._lock = threading.Lock()
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

    @property
    def max_tentativas(self) -> int:
        return self._max_tentativas

    @property
    def entregues(self) -> int:
        return self._entregues

    @property
    def falhas(self) -> int:
        return self._falhas

    def tentar(self, mensagem: Mensagem) -> ResultadoDaTentativa:
        """Uma tentativa de entrega, com o detalhe do que aconteceu."""
        if not self.ativa:
            return ResultadoDaTentativa(False, 0, "assinatura inativa")
        with self._lock:
            numero = self._tentativas.get(mensagem.id, 0) + 1
            self._tentativas[mensagem.id] = numero
        try:
            self._assinante.receber(mensagem)
        except Exception as erro:  # o assinante é código de terceiros
            texto = f"{type(erro).__name__}: {erro}"
            with self._lock:
                self._ultimo_erro = texto
                self._falhas += 1
            return ResultadoDaTentativa(False, numero, texto)
        with self._lock:
            self._tentativas.pop(mensagem.id, None)
            self._entregues += 1
        return ResultadoDaTentativa(True, numero)

    def notificar(self, mensagem: Mensagem) -> bool:
        """True se o assinante processou; False se falhou ou está inativa."""
        return self.tentar(mensagem).sucesso

    def tentativas(self, mensagem: Mensagem) -> int:
        return self._tentativas.get(mensagem.id, 0)

    def esgotou_tentativas(self, mensagem: Mensagem) -> bool:
        return self.tentativas(mensagem) >= self._max_tentativas

    def esquecer(self, mensagem: Mensagem) -> None:
        with self._lock:
            self._tentativas.pop(mensagem.id, None)
