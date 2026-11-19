# Broker (S03_Broker)

Intermediário de mensagens publish/subscribe do projeto de Arquitetura de Software.
Funciona como biblioteca Python (uso local) e como serviço HTTP (integração entre aplicações).

## Como rodar

    python -m venv venv
    venv\Scripts\activate            # Windows  (Linux/Mac: source venv/bin/activate)
    pip install -r requirements-dev.txt

    python -m app.main                                  # demonstração local, sem rede
    uvicorn app.api.principal:app --port 8000           # serviço HTTP
    pytest                                              # todos os testes
    pytest -m unit | integration | system               # por nível
    pytest --cov=app --cov-report=term-missing

Com o serviço no ar:

    http://localhost:8000/docs     documentação interativa da API
    http://localhost:8000/painel   painel em tempo real (tópicos, filas, falhas e histórico)

## Docker

    docker compose up --build        # Broker na porta 8000 e um receptor de exemplo na 9000

## API

| Método e caminho    | O que faz                                              | Resposta |
|---------------------|--------------------------------------------------------|----------|
| POST /publicar      | `{"topico": "...", "dados": {...}}`                     | 202 `{"id", "status"}` |
| POST /assinar       | `{"topico": "...", "url": "http://app/eventos"}`        | 201 (409 se já assinado) |
| GET  /topicos       | lista os tópicos                                       | 200 |
| GET  /filas         | lista as filas                                         | 200 |
| GET  /erros         | mensagens que esgotaram as tentativas, com os motivos  | 200 |
| POST /reentregas    | executa uma rodada de reentrega agora                  | 200 `{"entregues"}` |
| POST /erros/{id}/reprocessar | reenvia uma mensagem da fila de erros, só ao assinante que falhou | 200 `{"reprocessadas"}` (404 se não existe) |
| GET  /estado        | retrato atual: tópicos, assinantes, contadores, filas  | 200 |
| GET  /historico     | eventos recentes (`?desde=N&limite=N`)                 | 200 |
| GET  /painel        | página HTML de acompanhamento em tempo real            | 200 |
| GET  /saude         | verificação de funcionamento (sem chave)               | 200 |

Um tópico passa a existir **na primeira publicação ou assinatura**. Publicar em um
tópico sem assinantes é aceito (202), aparece em `/topicos` e a mensagem é descartada.

O assinante recebe um POST na URL cadastrada com
`{"id", "topico", "dados", "data_criacao"}` e deve responder 2xx. Qualquer outra
resposta, ou falta de resposta, conta como falha e entra no fluxo de reentrega.
Como a entrega é "pelo menos uma vez", o assinante deve ignorar ids repetidos.

## Demonstração de falhas e recuperação

Com `docker compose up --build`, abra o painel (`http://localhost:8000/painel`) e a
documentação do receptor de exemplo (`http://localhost:9000/docs`). No `/docs` do Broker
(`http://localhost:8000/docs`), em cada passo:

1. `POST /assinar` com `{"topico": "jogador.criado", "url": "http://distribuicao:9000/eventos"}`
   (dentro do Docker, os contêineres se chamam pelo nome do serviço, não por `localhost`).
2. **Caminho feliz:** `POST /publicar` com `{"topico": "jogador.criado", "dados": {"jogador_id": 42}}`.
   No painel: `publicada` e `entregue`. Em `http://localhost:9000/eventos` o evento aparece.
3. **Falha do receptor:** no `/docs` do receptor, `POST /simulacao` com `{"modo": "erro"}`, e
   publique de novo. No painel: `falhou` (1/3), depois (a cada 5 s, ou em `POST /reentregas`)
   `falhou` (2/3) e `esgotada`: a mensagem vai para a **fila de erros**, com o motivo.
4. **Recuperação:** `POST /simulacao` com `{"modo": "normal"}` e, no painel, clique em
   **Reprocessar** (ou `POST /erros/{id}/reprocessar`). A mensagem é entregue só ao assinante
   que falhou, e as tentativas recomeçam do zero.
5. **Timeout e duplicata:** `{"modo": "lento", "atraso_s": 8}` e publique. O Broker desiste
   após 5 s (`falhou`, com `ReadTimeout`), mas o receptor termina o processamento. Volte para
   `normal`: na reentrega o receptor reconhece o id e registra `duplicada ignorada`. É a
   garantia "pelo menos uma vez" e a idempotência em ação.
6. **Contêiner fora do ar de verdade:** `docker compose stop distribuicao`, publique e veja
   `falhou` com `ConnectError`. Depois `docker compose start distribuicao`: a reentrega
   automática entrega a mensagem.

Para acompanhar pelo terminal: `docker compose logs -f broker distribuicao`.

Simulações do receptor (`POST /simulacao`): `{"modo": "erro"}` responde 503 sempre;
`{"modo": "lento", "atraso_s": N}` demora N segundos; `{"falhas": N}` falha só as próximas N
chamadas; `{"modo": "normal"}` volta ao normal.

## Configuração (variáveis de ambiente)

    BROKER_MAX_TENTATIVAS=3         tentativas por assinante antes da fila de erros
    BROKER_INTERVALO_REENTREGA=5    segundos entre rodadas automáticas de reentrega
    BROKER_TIMEOUT_WEBHOOK=5        timeout da chamada ao assinante
    BROKER_CHAVE_API=               se definida, exige o header X-API-Key

## Estrutura

    app/comum      Mensagem, erros e contratos (Assinante, Servico*)
    app/servidor   Broker, Topico, Assinatura, Fila, FilaDeErros, RegistroDeEventos
    app/cliente    Publicador e ClienteHttpBroker
    app/api        API HTTP, painel, AssinanteWebhook, agendador de reentrega
    demo_http      receptor de exemplo (com falhas controláveis) e publicador de exemplo
    tests/unit | integration | system
