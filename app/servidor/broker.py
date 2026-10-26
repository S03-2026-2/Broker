"""O Broker: aceita, roteia, reentrega e informa o status de cada entrega."""
from __future__ import annotations

import logging

from app.comum.contratos import (
    Assinante,
    ServicoDeAssinatura,
    ServicoDeInspecao,
    ServicoDePublicacao,
)
from app.comum.erros import MensagemInvalidaError
from app.comum.mensagem import Mensagem
from app.servidor.assinatura import Assinatura
from app.servidor.fila import Fila
from app.servidor.fila_de_erros import FilaDeErros
from app.servidor.topico import Topico

logger = logging.getLogger(__name__)


class Broker(ServicoDePublicacao, ServicoDeAssinatura, ServicoDeInspecao):
    def __init__(
        self,
        max_tentativas: int = 3,
        fila_de_erros: FilaDeErros | None = None,
    ) -> None:
        self._topicos: dict[str, Topico] = {}
        self._max_tentativas = max_tentativas
        self._fila_de_erros = fila_de_erros if fila_de_erros is not None else FilaDeErros()

    @property
    def fila_de_erros(self) -> FilaDeErros:
        return self._fila_de_erros

    # --- ServicoDeAssinatura -------------------------------------------------
    def assinar(self, topico: str, assinante: Assinante) -> None:
        if not isinstance(topico, str) or not topico.strip():
            raise ValueError("O nome do tópico é obrigatório.")
        objeto_topico = self._topicos.get(topico)
        if objeto_topico is None:
            objeto_topico = Topico(topico)
        nome_fila = f"{topico}.{type(assinante).__name__}.{len(objeto_topico.assinaturas) + 1}"
        assinatura = Assinatura(assinante, Fila(nome_fila), self._max_tentativas)
        objeto_topico.adicionar_assinatura(assinatura)  # pode lançar duplicidade
        self._topicos[topico] = objeto_topico

    # --- ServicoDePublicacao -------------------------------------------------
    def publicar(self, mensagem: Mensagem) -> str:
        """Devolve o id da mensagem (ACK). O ACK diz 'aceitei', não 'foi processada'."""
        if not mensagem.validar():
            raise MensagemInvalidaError("Mensagem inválida: tópico e dados são obrigatórios.")
        topico = self._topicos.get(mensagem.topico)
        if topico is None or not topico.assinaturas:
            logger.info("Tópico '%s' sem assinantes: mensagem %s descartada.",
                        mensagem.topico, mensagem.id)
            return mensagem.id
        for assinatura in topico.assinaturas:
            self._entregar(assinatura, mensagem)
        return mensagem.id

    # --- ServicoDeInspecao ---------------------------------------------------
    def listar_topicos(self) -> list[str]:
        return list(self._topicos)

    def listar_filas(self) -> list[str]:
        filas = [a.nome for t in self._topicos.values() for a in t.assinaturas]
        filas.append(self._fila_de_erros.nome)
        return filas

    # --- Reentrega -----------------------------------------------------------
    def processar_pendentes(self) -> int:
        """Uma rodada de reentrega. Devolve quantas mensagens foram entregues.

        Hoje é chamada manualmente; mais tarde pode ser disparada por um timer.
        """
        entregues = 0
        for topico in self._topicos.values():
            for assinatura in topico.assinaturas:
                if not assinatura.ativa:
                    continue
                for _ in range(len(assinatura.fila)):
                    mensagem = assinatura.fila.retirar()
                    if assinatura.notificar(mensagem):
                        entregues += 1
                    else:
                        self._tratar_falha(assinatura, mensagem)
        return entregues

    # --- Internos ------------------------------------------------------------
    def _entregar(self, assinatura: Assinatura, mensagem: Mensagem) -> None:
        if not assinatura.ativa:
            assinatura.fila.enfileirar(mensagem)
            return
        if not assinatura.notificar(mensagem):
            self._tratar_falha(assinatura, mensagem)

    def _tratar_falha(self, assinatura: Assinatura, mensagem: Mensagem) -> None:
        if assinatura.esgotou_tentativas(mensagem):
            motivo = f"{assinatura.nome}: {assinatura.ultimo_erro}"
            self._fila_de_erros.registrar_falha(mensagem, motivo)
            assinatura.esquecer(mensagem)
        else:
            assinatura.fila.enfileirar(mensagem)
