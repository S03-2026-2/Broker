from .topico import Topico


class Pedido(Topico):

    def envioDeMensagem(self):
        raise NotImplementedError

    def envioDePedido(self):
        raise NotImplementedError

    def envioDeNotificacao(self):
        raise NotImplementedError
