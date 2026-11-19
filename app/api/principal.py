"""Ponto de entrada do serviço: uvicorn app.api.principal:app

Configuração por variáveis de ambiente:
  BROKER_MAX_TENTATIVAS       tentativas de entrega por assinante (padrão 3)
  BROKER_INTERVALO_REENTREGA  segundos entre rodadas de reentrega (padrão 5)
  BROKER_TIMEOUT_WEBHOOK      timeout, em segundos, da chamada ao assinante (padrão 5)
  BROKER_CHAVE_API            se definida, exige o header X-API-Key
"""
from __future__ import annotations

import logging
import os

import httpx
from fastapi import FastAPI

from app.api.agendador import AgendadorDeReentrega
from app.api.aplicacao import criar_aplicacao
from app.api.assinante_webhook import AssinanteWebhook
from app.servidor.broker import Broker


def criar_aplicacao_padrao() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    broker = Broker(max_tentativas=int(os.getenv("BROKER_MAX_TENTATIVAS", "3")))
    cliente = httpx.Client(timeout=float(os.getenv("BROKER_TIMEOUT_WEBHOOK", "5")))
    agendador = AgendadorDeReentrega(
        broker.processar_pendentes,
        float(os.getenv("BROKER_INTERVALO_REENTREGA", "5")),
    )
    return criar_aplicacao(
        broker,
        fabrica_assinante=lambda url: AssinanteWebhook(url, cliente),
        chave_api=os.getenv("BROKER_CHAVE_API") or None,
        agendador=agendador,
    )


app = criar_aplicacao_padrao()
