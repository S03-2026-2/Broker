"""Aplicação de exemplo que recebe eventos do Broker (simula uma equipe).

  uvicorn demo_http.receptor:app --port 9000

Falhas controláveis em tempo de execução, para demonstrar o tratamento de erros:
  POST /simulacao {"modo": "erro"}                    responde 503 a toda chamada
  POST /simulacao {"modo": "lento", "atraso_s": 8}    demora a responder (o Broker dá timeout)
  POST /simulacao {"falhas": 2}                       as próximas 2 chamadas respondem 503
  POST /simulacao {"modo": "normal"}                  volta ao funcionamento normal

RECEPTOR_FALHAS_INICIAIS=N faz as N primeiras chamadas falharem desde o início.
O receptor ignora ids repetidos (idempotência), como toda aplicação assinante deve fazer.
"""
import os
import threading
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Receptor de exemplo")
eventos: list[dict] = []
_vistos: set[str] = set()
_trava = threading.Lock()
_estado = {
    "modo": "normal",
    "falhas_restantes": int(os.getenv("RECEPTOR_FALHAS_INICIAIS", "0")),
    "atraso_s": 8.0,
}


class Simulacao(BaseModel):
    modo: Literal["normal", "erro", "lento"] = "normal"
    falhas: int = 0
    atraso_s: float = 8.0


@app.post("/eventos")
def receber(evento: dict) -> dict:
    with _trava:
        falhar = _estado["falhas_restantes"] > 0
        if falhar:
            _estado["falhas_restantes"] -= 1
        modo, atraso = _estado["modo"], _estado["atraso_s"]
    if falhar or modo == "erro":
        print(f"[receptor] erro simulado (503) para {evento.get('topico')}", flush=True)
        raise HTTPException(status_code=503, detail="indisponível (simulado)")
    if modo == "lento":
        print(f"[receptor] processando devagar ({atraso}s)...", flush=True)
        time.sleep(atraso)
    with _trava:
        if evento["id"] in _vistos:
            print(f"[receptor] duplicada ignorada: {evento['id'][:8]}", flush=True)
            return {"ok": True, "duplicada": True}
        _vistos.add(evento["id"])
        eventos.append(evento)
    print(f"[receptor] recebi {evento['topico']} {evento['dados']}", flush=True)
    return {"ok": True}


@app.get("/eventos")
def listar() -> list[dict]:
    return eventos


@app.get("/simulacao")
def ver_simulacao() -> dict:
    return dict(_estado)


@app.post("/simulacao")
def definir_simulacao(entrada: Simulacao) -> dict:
    with _trava:
        _estado["modo"] = entrada.modo
        _estado["falhas_restantes"] = entrada.falhas
        _estado["atraso_s"] = entrada.atraso_s
    print(f"[receptor] simulação: {_estado}", flush=True)
    return dict(_estado)


@app.get("/saude")
def saude() -> dict:
    return {"status": "ok"}
