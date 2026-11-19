"""Fila FIFO de mensagens pendentes."""
from __future__ import annotations

from collections import deque

from app.comum.erros import FilaVaziaError
from app.comum.mensagem import Mensagem


class Fila:
    def __init__(self, nome: str) -> None:
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("A fila precisa de um nome.")
        self._nome = nome
        self._mensagens: deque[Mensagem] = deque()

    @property
    def nome(self) -> str:
        return self._nome

    def enfileirar(self, mensagem: Mensagem) -> None:
        self._mensagens.append(mensagem)

    def retirar(self) -> Mensagem:
        if not self._mensagens:
            raise FilaVaziaError(f"A fila '{self._nome}' está vazia.")
        return self._mensagens.popleft()

    def listar_pendentes(self) -> list[Mensagem]:
        """Devolve uma cópia, para ninguém alterar a fila por fora."""
        return list(self._mensagens)

    def esta_vazia(self) -> bool:
        return not self._mensagens

    def __len__(self) -> int:
        return len(self._mensagens)
