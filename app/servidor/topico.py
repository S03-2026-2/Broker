"""Tópico genérico: identificado só pelo nome, gerencia suas assinaturas."""
from __future__ import annotations

import threading

from app.comum.contratos import Assinante
from app.comum.erros import AssinaturaDuplicadaError
from app.servidor.assinatura import Assinatura


class Topico:
    def __init__(self, nome: str) -> None:
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("O tópico precisa de um nome.")
        self._nome = nome
        self._assinaturas: list[Assinatura] = []
        self._publicadas = 0
        self._lock = threading.Lock()

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def publicadas(self) -> int:
        return self._publicadas

    def registrar_publicacao(self) -> None:
        with self._lock:
            self._publicadas += 1

    @property
    def assinaturas(self) -> tuple[Assinatura, ...]:
        return tuple(self._assinaturas)

    def adicionar_assinatura(self, assinatura: Assinatura) -> None:
        if any(a.assinante == assinatura.assinante for a in self._assinaturas):
            raise AssinaturaDuplicadaError(
                f"Este assinante já está inscrito em '{self._nome}'."
            )
        self._assinaturas.append(assinatura)

    def remover_assinatura(self, assinatura: Assinatura) -> None:
        """Idempotente: remover algo que não está inscrito não é erro."""
        if assinatura in self._assinaturas:
            self._assinaturas.remove(assinatura)

    def listar_assinantes(self) -> list[Assinante]:
        return [a.assinante for a in self._assinaturas]
