"""Assinante remoto: entrega a mensagem fazendo um POST na URL cadastrada."""
from __future__ import annotations

import httpx

from app.comum.contratos import Assinante
from app.comum.erros import ErroDeComunicacaoError
from app.comum.mensagem import Mensagem


class AssinanteWebhook(Assinante):
    """Para o Broker é um Assinante comum; por dentro, fala HTTP.

    Qualquer falha (conexão, timeout, resposta fora de 2xx) vira exceção, que o
    mecanismo de reentrega e fila de erros já existente sabe tratar.
    """

    def __init__(
        self,
        url: str,
        cliente: httpx.Client | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._url = url
        self._cliente = cliente if cliente is not None else httpx.Client(timeout=timeout)

    @property
    def url(self) -> str:
        return self._url

    def receber(self, mensagem: Mensagem) -> None:
        corpo = {
            "id": mensagem.id,
            "topico": mensagem.topico,
            "dados": mensagem.dados,
            "data_criacao": mensagem.data_criacao.isoformat(),
        }
        try:
            resposta = self._cliente.post(self._url, json=corpo)
        except httpx.HTTPError as erro:
            raise ErroDeComunicacaoError(
                f"Falha ao contatar {self._url}: {type(erro).__name__}: {erro}"
            ) from erro
        if not resposta.is_success:
            raise ErroDeComunicacaoError(
                f"{self._url} respondeu HTTP {resposta.status_code}"
            )

    # Dois webhooks com a mesma URL são o mesmo assinante (evita assinatura duplicada).
    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, AssinanteWebhook) and outro._url == self._url

    def __hash__(self) -> int:
        return hash(self._url)
