"""Abstrações (contratos) do Broker.

Ficam em um pacote neutro para que cliente e servidor dependam apenas de
abstrações, nunca um do outro (Princípio da Inversão de Dependência).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.comum.mensagem import Mensagem


class Assinante(ABC):
    """Quem recebe mensagens. Deve lançar exceção se não conseguir processar."""

    @abstractmethod
    def receber(self, mensagem: Mensagem) -> None:
        ...


class ServicoDePublicacao(ABC):
    """Contrato mínimo para quem só publica."""

    @abstractmethod
    def publicar(self, mensagem: Mensagem) -> str:
        """Aceita a mensagem e devolve seu id (o ACK de aceite)."""


class ServicoDeAssinatura(ABC):
    """Contrato mínimo para quem só assina tópicos."""

    @abstractmethod
    def assinar(self, topico: str, assinante: Assinante) -> None:
        ...


class ServicoDeInspecao(ABC):
    """Contrato de consulta: tópicos e filas existentes."""

    @abstractmethod
    def listar_topicos(self) -> list[str]:
        ...

    @abstractmethod
    def listar_filas(self) -> list[str]:
        ...
