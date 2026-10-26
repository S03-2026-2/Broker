"""Lado cliente: é isto que as outras aplicações usam para publicar."""
from __future__ import annotations

from typing import Any

from app.comum.contratos import ServicoDePublicacao
from app.comum.mensagem import Mensagem


class Publicador:
    def __init__(self, identificador: str, servico: ServicoDePublicacao) -> None:
        if not isinstance(identificador, str) or not identificador.strip():
            raise ValueError("O publicador precisa de um identificador.")
        self._identificador = identificador
        self._servico = servico  # depende da abstração, não do Broker concreto

    @property
    def identificador(self) -> str:
        return self._identificador

    def publicar(self, topico: str, dados: dict[str, Any]) -> str:
        """Cria a mensagem e a entrega ao serviço. Devolve o id (ACK)."""
        return self._servico.publicar(Mensagem.criar(topico, dados))
