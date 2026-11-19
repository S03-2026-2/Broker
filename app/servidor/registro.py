"""Histórico recente do que acontece no Broker: publicação, entrega, falha, reentrega."""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class RegistroDeEventos:
    """Guarda os últimos eventos em memória (os mais antigos são descartados)."""

    def __init__(self, capacidade: int = 500) -> None:
        self._eventos: deque[dict[str, Any]] = deque(maxlen=capacidade)
        self._proximo_id = 1
        self._lock = threading.Lock()

    def registrar(
        self,
        tipo: str,
        topico: str | None = None,
        mensagem: str | None = None,
        destino: str | None = None,
        tentativa: int | None = None,
        detalhe: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            evento = {
                "id": self._proximo_id,
                "hora": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "tipo": tipo,
                "topico": topico,
                "mensagem": mensagem,
                "destino": destino,
                "tentativa": tentativa,
                "detalhe": detalhe,
            }
            self._proximo_id += 1
            self._eventos.append(evento)
        logger.info("%s topico=%s mensagem=%s destino=%s tentativa=%s %s",
                    tipo, topico, mensagem, destino, tentativa, detalhe or "")
        return dict(evento)

    def listar(self, desde: int = 0, limite: int = 100) -> list[dict[str, Any]]:
        """Eventos com id maior que `desde`, limitados aos `limite` mais recentes."""
        with self._lock:
            selecionados = [dict(e) for e in self._eventos if e["id"] > desde]
        return selecionados[-limite:] if limite > 0 else []
