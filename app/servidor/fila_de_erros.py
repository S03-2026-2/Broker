"""Fila de mensagens que esgotaram as tentativas de entrega (dead letter)."""
from __future__ import annotations

import threading

from app.comum.erros import MensagemNaoEncontradaError
from app.comum.mensagem import Mensagem
from app.servidor.fila import Fila


class FilaDeErros(Fila):
    def __init__(self, nome: str = "fila_de_erros") -> None:
        super().__init__(nome)
        # Uma mesma mensagem pode falhar para mais de um assinante: guardamos
        # (motivo, destino) de cada falha, na mesma ordem da fila.
        self._falhas: dict[str, list[tuple[str, str | None]]] = {}
        self._lock = threading.Lock()

    def registrar_falha(self, mensagem: Mensagem, motivo: str, destino: str | None = None) -> None:
        with self._lock:
            self.enfileirar(mensagem)
            self._falhas.setdefault(mensagem.id, []).append((motivo, destino))

    def motivos_da_falha(self, id_mensagem: str) -> list[str]:
        with self._lock:
            return [motivo for motivo, _ in self._falhas.get(id_mensagem, [])]

    def destinos_da_falha(self, id_mensagem: str) -> list[str | None]:
        with self._lock:
            return [destino for _, destino in self._falhas.get(id_mensagem, [])]

    def reprocessar(self, id_mensagem: str) -> Mensagem:
        """Retira a primeira ocorrência da mensagem e a devolve a quem vai reenviá-la."""
        with self._lock:
            for mensagem in self._mensagens:
                if mensagem.id == id_mensagem:
                    self._mensagens.remove(mensagem)
                    falhas = self._falhas.get(id_mensagem, [])
                    if falhas:
                        falhas.pop(0)
                    if not falhas:
                        self._falhas.pop(id_mensagem, None)
                    return mensagem
        raise MensagemNaoEncontradaError(
            f"Mensagem '{id_mensagem}' não está na fila de erros."
        )

    def retirar_todas(self, id_mensagem: str) -> list[tuple[Mensagem, str, str | None]]:
        """Retira todas as falhas da mensagem: (mensagem, motivo, destino)."""
        with self._lock:
            falhas = self._falhas.pop(id_mensagem, [])
            retiradas = [m for m in self._mensagens if m.id == id_mensagem]
            for m in retiradas:
                self._mensagens.remove(m)
        return [(m, motivo, destino) for m, (motivo, destino) in zip(retiradas, falhas)]
