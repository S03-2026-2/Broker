"""Cliente HTTP: é o que as outras equipes usam para falar com o Broker pela rede."""
from __future__ import annotations

import httpx

from app.comum.contratos import ServicoDeInspecao, ServicoDePublicacao
from app.comum.erros import ErroDeComunicacaoError
from app.comum.mensagem import Mensagem


class ClienteHttpBroker(ServicoDePublicacao, ServicoDeInspecao):
    """Implementa os mesmos contratos do Broker local, então o `Publicador`
    funciona com ele sem nenhuma alteração.

    Não implementa `ServicoDeAssinatura`: pela rede o assinante é uma URL, não
    um objeto, por isso a operação tem outro formato (`assinar_por_url`).
    """

    def __init__(
        self,
        url_base: str,
        chave_api: str | None = None,
        cliente: httpx.Client | None = None,
        timeout: float = 5.0,
    ) -> None:
        cabecalhos = {"X-API-Key": chave_api} if chave_api else {}
        self._cliente = cliente if cliente is not None else httpx.Client(
            base_url=url_base.rstrip("/"), headers=cabecalhos, timeout=timeout
        )
        self._extra = cabecalhos if cliente is not None else {}

    def publicar(self, mensagem: Mensagem) -> str:
        corpo = {"topico": mensagem.topico, "dados": mensagem.dados, "id": mensagem.id}
        return self._chamar("POST", "/publicar", json=corpo)["id"]

    def assinar_por_url(self, topico: str, url: str) -> None:
        self._chamar("POST", "/assinar", json={"topico": topico, "url": url})

    def listar_topicos(self) -> list[str]:
        return self._chamar("GET", "/topicos")["topicos"]

    def listar_filas(self) -> list[str]:
        return self._chamar("GET", "/filas")["filas"]

    def _chamar(self, metodo: str, caminho: str, **opcoes) -> dict:
        try:
            resposta = self._cliente.request(metodo, caminho, headers=self._extra, **opcoes)
        except httpx.HTTPError as erro:
            raise ErroDeComunicacaoError(
                f"Falha ao contatar o Broker: {type(erro).__name__}: {erro}"
            ) from erro
        if not resposta.is_success:
            raise ErroDeComunicacaoError(
                f"O Broker respondeu HTTP {resposta.status_code}: {resposta.text}"
            )
        return resposta.json()
