"""Aplicações de exemplo, usadas na demonstração e nos testes de sistema.

No projeto real, cada uma destas seria uma aplicação separada (de outra equipe).
"""
from __future__ import annotations

import random

from app.comum.contratos import Assinante
from app.comum.mensagem import Mensagem

TOTAL_POKEMON = 151  # ids da PokéAPI usados no exemplo


class DistribuicaoDeCartas(Assinante):
    """Ao receber 'jogador.criado', sorteia 5 Pokémon sem repetir para o jogador."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.banco: dict[int, list[int]] = {}
        self._processadas: set[str] = set()

    def receber(self, mensagem: Mensagem) -> None:
        if mensagem.id in self._processadas:  # idempotência: ignora duplicatas
            return
        jogador_id = mensagem.dados["jogador_id"]
        ja_tem = self.banco.get(jogador_id, [])
        disponiveis = [p for p in range(1, TOTAL_POKEMON + 1) if p not in ja_tem]
        self.banco[jogador_id] = ja_tem + self._rng.sample(disponiveis, 5)
        self._processadas.add(mensagem.id)


class AplicacaoOffline(Assinante):
    """Simula uma aplicação que está fora do ar: sempre falha."""

    def receber(self, mensagem: Mensagem) -> None:
        raise ConnectionError("aplicação offline")
