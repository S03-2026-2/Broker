"""Dispara a reentrega periodicamente, em segundo plano."""
from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class AgendadorDeReentrega:
    def __init__(self, acao: Callable[[], object], intervalo_s: float = 5.0) -> None:
        self._acao = acao
        self._intervalo_s = intervalo_s
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def ativo(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def iniciar(self) -> None:
        if self.ativo:
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, name="reentrega", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _laco(self) -> None:
        while not self._parar.wait(self._intervalo_s):
            try:
                self._acao()
            except Exception:  # uma rodada com erro não derruba o agendador
                logger.exception("Erro na rodada de reentrega.")
