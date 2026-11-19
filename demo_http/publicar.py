"""Exemplo de quem publica: python -m demo_http.publicar [url_do_broker]"""
import sys

from app.cliente.cliente_http import ClienteHttpBroker
from app.cliente.publicador import Publicador

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
broker = ClienteHttpBroker(url)
jogadores = Publicador("jogadores", broker)

ack = jogadores.publicar("jogador.criado", {"jogador_id": 42})
print(f"Mensagem {ack} aceita pelo Broker")
print("Tópicos:", broker.listar_topicos())
print("Filas:  ", broker.listar_filas())
