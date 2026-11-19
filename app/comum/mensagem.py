"""Envelope de mensagem trafegado pelo Broker."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Mensagem:
    """Envelope imutável. O Broker só olha o tópico e o id; `dados` é opaco."""

    topico: str
    dados: dict[str, Any]
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    data_criacao: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def criar(cls, topico: str, dados: dict[str, Any]) -> "Mensagem":
        """Cria uma mensagem nova, copiando `dados` para evitar efeitos colaterais."""
        return cls(topico=topico, dados=dict(dados))

    def validar(self) -> bool:
        """Valida apenas o envelope. Regras de negócio são da aplicação destino."""
        return (
            isinstance(self.topico, str)
            and self.topico.strip() != ""
            and isinstance(self.dados, dict)
            and isinstance(self.id, str)
            and self.id != ""
        )
