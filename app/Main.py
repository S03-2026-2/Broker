from app.mensagens.pedido import Pedido
from app.mensagens.resposta import Resposta


def main():
    pedido = Pedido()
    resposta = Resposta()

    print("Broker iniciado.")
    print(f"Pedido: {type(pedido)._name_}")
    print(f"Resposta: {type(resposta)._name_}")


if _name_ == "_main_":
    main()
