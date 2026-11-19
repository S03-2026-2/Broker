"""O Broker: aceita, roteia, reentrega e informa o status de cada entrega."""
from __future__ import annotations

import logging
import threading
from typing import Any

from app.comum.contratos import (
    Assinante,
    ServicoDeAssinatura,
    ServicoDeInspecao,
    ServicoDePublicacao,
)
from app.comum.erros import MensagemInvalidaError, MensagemNaoEncontradaError
from app.comum.mensagem import Mensagem
from app.servidor.assinatura import Assinatura, ResultadoDaTentativa
from app.servidor.fila import Fila
from app.servidor.fila_de_erros import FilaDeErros
from app.servidor.registro import RegistroDeEventos
from app.servidor.topico import Topico

logger = logging.getLogger(__name__)


class Broker(ServicoDePublicacao, ServicoDeAssinatura, ServicoDeInspecao):
    """Seguro para uso com várias threads (a API HTTP atende pedidos em paralelo).

    - `_lock` protege só a topologia (tópicos e assinaturas). Nunca é mantido
      durante uma entrega, para um assinante lento não travar os demais.
    - `_lock_reentrega` garante uma única rodada de reentrega por vez.
    """

    def __init__(
        self,
        max_tentativas: int = 3,
        fila_de_erros: FilaDeErros | None = None,
        registro: RegistroDeEventos | None = None,
    ) -> None:
        self._topicos: dict[str, Topico] = {}
        self._max_tentativas = max_tentativas
        self._fila_de_erros = fila_de_erros if fila_de_erros is not None else FilaDeErros()
        self._registro = registro if registro is not None else RegistroDeEventos()
        self._lock = threading.RLock()
        self._lock_reentrega = threading.Lock()

    @property
    def fila_de_erros(self) -> FilaDeErros:
        return self._fila_de_erros

    @property
    def registro(self) -> RegistroDeEventos:
        return self._registro

    # --- ServicoDeAssinatura -------------------------------------------------
    def assinar(self, topico: str, assinante: Assinante) -> None:
        if not isinstance(topico, str) or not topico.strip():
            raise ValueError("O nome do tópico é obrigatório.")
        with self._lock:
            objeto_topico = self._obter_ou_criar_topico(topico)
            nome_fila = (
                f"{topico}.{type(assinante).__name__}.{len(objeto_topico.assinaturas) + 1}"
            )
            assinatura = Assinatura(assinante, Fila(nome_fila), self._max_tentativas)
            objeto_topico.adicionar_assinatura(assinatura)  # pode lançar duplicidade

    # --- ServicoDePublicacao -------------------------------------------------
    def publicar(self, mensagem: Mensagem) -> str:
        """Devolve o id da mensagem (ACK). O ACK diz 'aceitei', não 'foi processada'.

        O tópico passa a existir já na primeira publicação, mesmo sem assinantes.
        """
        if not mensagem.validar():
            raise MensagemInvalidaError("Mensagem inválida: tópico e dados são obrigatórios.")
        with self._lock:
            topico = self._obter_ou_criar_topico(mensagem.topico)
            assinaturas = topico.assinaturas
        topico.registrar_publicacao()
        self._registro.registrar(
            "publicada", mensagem.topico, mensagem.id,
            detalhe=f"{len(assinaturas)} assinante(s)",
        )
        if not assinaturas:
            self._registro.registrar(
                "descartada", mensagem.topico, mensagem.id,
                detalhe="tópico sem assinantes: mensagem descartada",
            )
            return mensagem.id
        for assinatura in assinaturas:  # entrega fora do lock
            self._entregar(assinatura, mensagem)
        return mensagem.id

    # --- ServicoDeInspecao ---------------------------------------------------
    def listar_topicos(self) -> list[str]:
        with self._lock:
            return list(self._topicos)

    def listar_filas(self) -> list[str]:
        with self._lock:
            filas = [a.nome for t in self._topicos.values() for a in t.assinaturas]
        filas.append(self._fila_de_erros.nome)
        return filas

    def situacao(self) -> dict[str, Any]:
        """Retrato do Broker neste instante: tópicos, assinantes, filas e totais."""
        with self._lock:
            topicos = list(self._topicos.values())
        saida_topicos, filas = [], []
        total_publicadas = total_entregues = total_falhas = 0
        for t in topicos:
            assinantes = []
            for a in t.assinaturas:
                destino = getattr(a.assinante, "url", None) or type(a.assinante).__name__
                assinantes.append({
                    "nome": a.nome, "destino": destino, "ativa": a.ativa,
                    "pendentes": len(a.fila), "entregues": a.entregues, "falhas": a.falhas,
                })
                filas.append({"nome": a.nome, "pendentes": len(a.fila)})
                total_entregues += a.entregues
                total_falhas += a.falhas
            total_publicadas += t.publicadas
            saida_topicos.append(
                {"nome": t.nome, "publicadas": t.publicadas, "assinantes": assinantes}
            )
        filas.append({"nome": self._fila_de_erros.nome, "pendentes": len(self._fila_de_erros)})
        return {
            "topicos": saida_topicos,
            "filas": filas,
            "totais": {
                "publicadas": total_publicadas,
                "entregues": total_entregues,
                "falhas": total_falhas,
                "na_fila_de_erros": len(self._fila_de_erros),
            },
        }

    # --- Reentrega -----------------------------------------------------------
    def processar_pendentes(self) -> int:
        """Uma rodada de reentrega. Devolve quantas mensagens foram entregues."""
        with self._lock_reentrega:
            with self._lock:
                assinaturas = [a for t in self._topicos.values() for a in t.assinaturas]
            entregues = 0
            for assinatura in assinaturas:
                if not assinatura.ativa:
                    continue
                for _ in range(len(assinatura.fila)):
                    mensagem = assinatura.fila.retirar()
                    if self._tentar_e_tratar(assinatura, mensagem):
                        entregues += 1
            return entregues

    def reprocessar_erro(self, id_mensagem: str) -> int:
        """Reenvia uma mensagem da fila de erros SÓ ao assinante que falhou.

        As tentativas do assinante recomeçam do zero. Devolve quantas entregas
        foram retomadas e lança MensagemNaoEncontradaError se o id não está na fila.
        """
        entradas = self._fila_de_erros.retirar_todas(id_mensagem)
        if not entradas:
            raise MensagemNaoEncontradaError(
                f"Mensagem '{id_mensagem}' não está na fila de erros."
            )
        retomadas = 0
        for mensagem, motivo, destino in entradas:
            alvos = self._assinaturas_para(mensagem.topico, destino)
            if not alvos:
                self._fila_de_erros.registrar_falha(
                    mensagem, f"{motivo} | assinatura '{destino}' não existe mais", destino)
                continue
            for assinatura in alvos:
                assinatura.esquecer(mensagem)
                self._registro.registrar(
                    "reprocessada", mensagem.topico, mensagem.id, assinatura.nome,
                    detalhe="reenvio manual a partir da fila de erros",
                )
                self._entregar(assinatura, mensagem)
                retomadas += 1
        return retomadas

    # --- Internos ------------------------------------------------------------
    def _obter_ou_criar_topico(self, nome: str) -> Topico:
        with self._lock:
            topico = self._topicos.get(nome)
            if topico is None:
                topico = Topico(nome)
                self._topicos[nome] = topico
            return topico

    def _assinaturas_para(self, nome_topico: str, destino: str | None) -> list[Assinatura]:
        with self._lock:
            topico = self._topicos.get(nome_topico)
            assinaturas = list(topico.assinaturas) if topico is not None else []
        if destino is None:
            return assinaturas
        return [a for a in assinaturas if a.nome == destino]

    def _entregar(self, assinatura: Assinatura, mensagem: Mensagem) -> None:
        if not assinatura.ativa:
            assinatura.fila.enfileirar(mensagem)
            self._registro.registrar(
                "retida", mensagem.topico, mensagem.id, assinatura.nome,
                detalhe="assinatura inativa: mensagem aguarda na fila",
            )
            return
        self._tentar_e_tratar(assinatura, mensagem)

    def _tentar_e_tratar(self, assinatura: Assinatura, mensagem: Mensagem) -> bool:
        resultado = assinatura.tentar(mensagem)
        if resultado.sucesso:
            detalhe = f"após {resultado.tentativa} tentativas" if resultado.tentativa > 1 else None
            self._registro.registrar(
                "entregue", mensagem.topico, mensagem.id, assinatura.nome,
                resultado.tentativa, detalhe,
            )
            return True
        self._tratar_falha(assinatura, mensagem, resultado)
        return False

    def _tratar_falha(
        self, assinatura: Assinatura, mensagem: Mensagem, resultado: ResultadoDaTentativa
    ) -> None:
        if assinatura.esgotou_tentativas(mensagem):
            motivo = f"{assinatura.nome}: {resultado.erro}"
            self._fila_de_erros.registrar_falha(mensagem, motivo, assinatura.nome)
            assinatura.esquecer(mensagem)
            self._registro.registrar(
                "esgotada", mensagem.topico, mensagem.id, assinatura.nome, resultado.tentativa,
                f"{resultado.tentativa} tentativas sem sucesso; enviada à fila de erros: "
                f"{resultado.erro}",
            )
        else:
            assinatura.fila.enfileirar(mensagem)
            self._registro.registrar(
                "falhou", mensagem.topico, mensagem.id, assinatura.nome, resultado.tentativa,
                f"tentativa {resultado.tentativa}/{assinatura.max_tentativas}: {resultado.erro}; "
                "nova tentativa em breve",
            )
