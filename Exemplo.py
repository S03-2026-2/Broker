"""
1. Publish / Subscribe

#A ideia é que, sempre que uma aplicação realizar um evento importante que possa interessar a outras aplicações, 
ela publique esse evento.

Por exemplo, quando um jogador for criado: """

broker.publish(
"jogador.criado",
{"jogador_id": 42}
)

#A Distribuição de Cartas pode estar inscrita nesse tópico através de:

broker.subscribe(
"jogador.criado",
distribuir_cartas
)

"""
2. Request

O request será utilizado quando uma aplicação precisar solicitar diretamente alguma informação ou operação de outra.

Por exemplo, a Visualização de Cartas precisa descobrir quais cartas pertencem ao jogador 42: """

broker.request(
destino="distribuicao",
operacao="cartas_do_jogador",
dados={"jogador_id": 42}
)

"""
O Broker recebe essa requisição, identifica o destino e a operação e encaminha a mensagem para a Distribuição.

A parte importante é que o Broker NÃO sabe como buscar as cartas.

Nós não temos acesso ao banco de dados da Distribuição e nem devemos ter.

A própria Distribuição implementa a função responsável por responder essa operação.

Conceitualmente, ela faria algo como: """

broker.register(
"cartas_do_jogador",
cartas_do_jogador
)

#A função cartas_do_jogador pertence à própria Distribuição e é ela que sabe como consultar o banco e montar a resposta.
