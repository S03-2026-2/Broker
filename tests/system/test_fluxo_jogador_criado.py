"""Fluxo completo pela API pública, sem tocar em classes internas."""
import random
import subprocess
import sys
from pathlib import Path

from app.cliente.publicador import Publicador
from app.exemplos import AplicacaoOffline, DistribuicaoDeCartas
from app.servidor.broker import Broker

RAIZ = Path(__file__).resolve().parents[2]


def test_jogador_criado_gera_cinco_cartas_sem_repeticao():
    broker = Broker()
    distribuicao = DistribuicaoDeCartas(rng=random.Random(7))
    broker.assinar("jogador.criado", distribuicao)
    jogadores = Publicador("jogadores", broker)

    ack = jogadores.publicar("jogador.criado", {"jogador_id": 42})

    assert ack
    cartas = distribuicao.banco[42]
    assert len(cartas) == 5 and len(set(cartas)) == 5


def test_varios_jogadores_recebem_cartas_independentes():
    broker = Broker()
    distribuicao = DistribuicaoDeCartas()
    broker.assinar("jogador.criado", distribuicao)
    jogadores = Publicador("jogadores", broker)

    for jogador_id in (1, 2, 3):
        jogadores.publicar("jogador.criado", {"jogador_id": jogador_id})

    assert set(distribuicao.banco) == {1, 2, 3}
    assert all(len(c) == 5 for c in distribuicao.banco.values())


def test_mensagem_duplicada_nao_distribui_cartas_duas_vezes():
    broker = Broker()
    distribuicao = DistribuicaoDeCartas()
    broker.assinar("jogador.criado", distribuicao)
    from app.comum.mensagem import Mensagem
    m = Mensagem.criar("jogador.criado", {"jogador_id": 9})

    broker.publicar(m)
    broker.publicar(m)  # reentrega duplicada (at-least-once)

    assert len(distribuicao.banco[9]) == 5


def test_aplicacao_offline_acaba_na_fila_de_erros_sem_travar_o_cadastro():
    broker = Broker(max_tentativas=3)
    distribuicao = DistribuicaoDeCartas()
    broker.assinar("jogador.criado", distribuicao)
    broker.assinar("jogador.criado", AplicacaoOffline())
    jogadores = Publicador("jogadores", broker)

    jogadores.publicar("jogador.criado", {"jogador_id": 42})  # não levanta erro
    broker.processar_pendentes()
    broker.processar_pendentes()

    assert len(distribuicao.banco[42]) == 5
    assert len(broker.fila_de_erros) == 1


def test_inspecao_mostra_topicos_e_filas_disponiveis():
    broker = Broker()
    broker.assinar("jogador.criado", DistribuicaoDeCartas())
    assert broker.listar_topicos() == ["jogador.criado"]
    assert "fila_de_erros" in broker.listar_filas()


def test_demonstracao_roda_de_ponta_a_ponta():
    resultado = subprocess.run(
        [sys.executable, "-m", "app.main"],
        cwd=RAIZ, capture_output=True, text=True, timeout=30,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "jogador.criado" in resultado.stdout
    assert "fila de erros" in resultado.stdout
