"""Formato (JSON) das entradas e saídas da API."""
from __future__ import annotations

from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field


class PublicarEntrada(BaseModel):
    topico: str = Field(min_length=1, examples=["jogador.criado"])
    dados: dict[str, Any] = Field(examples=[{"jogador_id": 42}])
    id: str | None = Field(
        default=None,
        description="Opcional. Se informado, é usado como id da mensagem.",
    )


class PublicarSaida(BaseModel):
    id: str
    status: str = "aceito"


class AssinarEntrada(BaseModel):
    topico: str = Field(min_length=1, examples=["jogador.criado"])
    url: AnyHttpUrl = Field(examples=["http://distribuicao:9000/eventos"])


class AssinarSaida(BaseModel):
    topico: str
    url: str


class TopicosSaida(BaseModel):
    topicos: list[str]


class FilasSaida(BaseModel):
    filas: list[str]


class FalhaSaida(BaseModel):
    id: str
    topico: str
    dados: dict[str, Any]
    motivos: list[str]
    destinos: list[str | None] = []


class ErrosSaida(BaseModel):
    erros: list[FalhaSaida]


class ReentregaSaida(BaseModel):
    entregues: int


class AssinanteEstado(BaseModel):
    nome: str
    destino: str
    ativa: bool
    pendentes: int
    entregues: int
    falhas: int


class TopicoEstado(BaseModel):
    nome: str
    publicadas: int
    assinantes: list[AssinanteEstado]


class FilaEstado(BaseModel):
    nome: str
    pendentes: int


class TotaisEstado(BaseModel):
    publicadas: int
    entregues: int
    falhas: int
    na_fila_de_erros: int


class EstadoSaida(BaseModel):
    topicos: list[TopicoEstado]
    filas: list[FilaEstado]
    totais: TotaisEstado


class EventoSaida(BaseModel):
    id: int
    hora: str
    tipo: str
    topico: str | None = None
    mensagem: str | None = None
    destino: str | None = None
    tentativa: int | None = None
    detalhe: str | None = None


class HistoricoSaida(BaseModel):
    eventos: list[EventoSaida]


class ReprocessamentoSaida(BaseModel):
    reprocessadas: int
