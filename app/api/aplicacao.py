"""API HTTP do Broker. Só traduz HTTP <-> Broker: nenhuma regra mora aqui."""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from app.api.agendador import AgendadorDeReentrega
from app.api.painel import PAINEL_HTML
from app.api.esquemas import (
    AssinarEntrada,
    AssinarSaida,
    ErrosSaida,
    EstadoSaida,
    FalhaSaida,
    FilasSaida,
    HistoricoSaida,
    PublicarEntrada,
    PublicarSaida,
    ReentregaSaida,
    ReprocessamentoSaida,
    TopicosSaida,
)
from app.comum.contratos import Assinante
from app.comum.erros import AssinaturaDuplicadaError, MensagemNaoEncontradaError
from app.comum.mensagem import Mensagem
from app.servidor.broker import Broker

logger = logging.getLogger(__name__)


def criar_aplicacao(
    broker: Broker,
    fabrica_assinante: Callable[[str], Assinante],
    chave_api: str | None = None,
    agendador: AgendadorDeReentrega | None = None,
) -> FastAPI:
    """Monta a API. Tudo que varia (Broker, assinante remoto, chave, agendador)
    entra por parâmetro, o que permite trocar peças nos testes."""

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        if agendador is not None:
            agendador.iniciar()
        yield
        if agendador is not None:
            agendador.parar()

    app = FastAPI(
        title="Broker",
        description="Mensageria publish/subscribe do projeto Pokémon.",
        version="1.0.0",
        lifespan=ciclo_de_vida,
    )

    def exigir_chave(x_api_key: str | None = Header(default=None)) -> None:
        if chave_api is None:
            return  # modo desenvolvimento: sem chave configurada
        if not secrets.compare_digest(x_api_key or "", chave_api):
            raise HTTPException(status_code=401, detail="Chave de API ausente ou inválida.")

    protegido = [Depends(exigir_chave)]

    def entregar_em_segundo_plano(mensagem: Mensagem) -> None:
        try:
            broker.publicar(mensagem)
        except Exception:
            logger.exception("Erro ao entregar a mensagem %s.", mensagem.id)

    @app.get("/saude")
    def saude() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/publicar", status_code=202, response_model=PublicarSaida, dependencies=protegido)
    def publicar(entrada: PublicarEntrada, tarefas: BackgroundTasks) -> PublicarSaida:
        campos = {"topico": entrada.topico, "dados": dict(entrada.dados)}
        if entrada.id:
            campos["id"] = entrada.id
        mensagem = Mensagem(**campos)
        if not mensagem.validar():
            raise HTTPException(status_code=422, detail="Mensagem inválida: tópico vazio.")
        tarefas.add_task(entregar_em_segundo_plano, mensagem)  # ACK primeiro, entrega depois
        return PublicarSaida(id=mensagem.id)

    @app.post("/assinar", status_code=201, response_model=AssinarSaida, dependencies=protegido)
    def assinar(entrada: AssinarEntrada) -> AssinarSaida:
        url = str(entrada.url)
        try:
            broker.assinar(entrada.topico, fabrica_assinante(url))
        except AssinaturaDuplicadaError as erro:
            raise HTTPException(status_code=409, detail=str(erro))
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro))
        return AssinarSaida(topico=entrada.topico, url=url)

    @app.get("/topicos", response_model=TopicosSaida, dependencies=protegido)
    def topicos() -> TopicosSaida:
        return TopicosSaida(topicos=broker.listar_topicos())

    @app.get("/filas", response_model=FilasSaida, dependencies=protegido)
    def filas() -> FilasSaida:
        return FilasSaida(filas=broker.listar_filas())

    @app.get("/erros", response_model=ErrosSaida, dependencies=protegido)
    def erros() -> ErrosSaida:
        vistos: dict[str, FalhaSaida] = {}
        for m in broker.fila_de_erros.listar_pendentes():
            if m.id not in vistos:
                vistos[m.id] = FalhaSaida(
                    id=m.id,
                    topico=m.topico,
                    dados=m.dados,
                    motivos=broker.fila_de_erros.motivos_da_falha(m.id),
                    destinos=broker.fila_de_erros.destinos_da_falha(m.id),
                )
        return ErrosSaida(erros=list(vistos.values()))

    @app.post("/reentregas", response_model=ReentregaSaida, dependencies=protegido)
    def reentregas() -> ReentregaSaida:
        return ReentregaSaida(entregues=broker.processar_pendentes())

    @app.post("/erros/{id_mensagem}/reprocessar", response_model=ReprocessamentoSaida,
              dependencies=protegido)
    def reprocessar(id_mensagem: str) -> ReprocessamentoSaida:
        try:
            return ReprocessamentoSaida(reprocessadas=broker.reprocessar_erro(id_mensagem))
        except MensagemNaoEncontradaError as erro:
            raise HTTPException(status_code=404, detail=str(erro))

    @app.get("/estado", response_model=EstadoSaida, dependencies=protegido)
    def estado() -> EstadoSaida:
        return EstadoSaida(**broker.situacao())

    @app.get("/historico", response_model=HistoricoSaida, dependencies=protegido)
    def historico(desde: int = 0, limite: int = 100) -> HistoricoSaida:
        return HistoricoSaida(eventos=broker.registro.listar(desde=desde, limite=limite))

    @app.get("/painel", response_class=HTMLResponse, include_in_schema=False)
    def painel() -> str:
        return PAINEL_HTML  # a página só traz código; os dados vêm de /estado e /historico

    return app
