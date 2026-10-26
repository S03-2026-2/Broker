"""Fila de mensagens que esgotaram as tentativas de entrega (dead letter)."""
from __future__ import annotations

from app.comum.erros import MensagemNaoEncontradaError
from app.comum.mensagem import Mensagem
from app.servidor.fila import Fila


class FilaDeErros(Fila):
    def __init__(self, nome: str = "fila_de_erros") -> None:
        super().__init__(nome)
        # Uma mesma mensagem pode falhar para mais de um assinante.
        self._motivos: dict[str, list[str]] = {}

    def registrar_falha(self, mensagem: Mensagem, motivo: str) -> None:
        self.enfileirar(mensagem)
        self._motivos.setdefault(mensagem.id, []).append(motivo)

    def motivos_da_falha(self, id_mensagem: str) -> list[str]:
        return list(self._motivos.get(id_mensagem, []))

    def reprocessar(self, id_mensagem: str) -> Mensagem:
        """Retira a mensagem da fila de erros e a devolve a quem vai reenviá-la."""
        for mensagem in self._mensagens:
            if mensagem.id == id_mensagem:
                self._mensagens.remove(mensagem)
                motivos = self._motivos.get(id_mensagem, [])
                if motivos:
                    motivos.pop(0)
                if not motivos:
                    self._motivos.pop(id_mensagem, None)
                return mensagem
        raise MensagemNaoEncontradaError(
            f"Mensagem '{id_mensagem}' não está na fila de erros."
        )
