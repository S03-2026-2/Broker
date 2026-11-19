"""Demonstração do Broker: python -m app.main"""
from __future__ import annotations

from app.cliente.publicador import Publicador
from app.exemplos import AplicacaoOffline, DistribuicaoDeCartas
from app.servidor.broker import Broker


def main() -> int:
    broker = Broker(max_tentativas=3)
    distribuicao = DistribuicaoDeCartas()
    auditoria = AplicacaoOffline()

    broker.assinar("jogador.criado", distribuicao)
    broker.assinar("jogador.criado", auditoria)
    jogadores = Publicador("jogadores", broker)

    print("Broker iniciado.")
    print(f"Tópicos: {broker.listar_topicos()}")
    print(f"Filas:   {broker.listar_filas()}")

    print("\n1) Jogadores publica 'jogador.criado' (jogador 42)")
    ack = jogadores.publicar("jogador.criado", {"jogador_id": 42})
    print(f"   ACK: mensagem {ack} aceita")
    print(f"   Distribuição entregou as cartas: {distribuicao.banco[42]}")

    print("\n2) A aplicação de auditoria está offline: reentregas")
    for rodada in (1, 2):
        broker.processar_pendentes()
        print(f"   rodada {rodada}: pendentes em {broker.listar_filas()[1]!r}")

    print("\n3) Tentativas esgotadas: mensagem vai para a fila de erros")
    for mensagem in broker.fila_de_erros.listar_pendentes():
        motivos = broker.fila_de_erros.motivos_da_falha(mensagem.id)
        print(f"   {mensagem.topico} {mensagem.dados} -> {motivos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
