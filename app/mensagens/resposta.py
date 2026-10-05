from .topico import Topico


class Resposta(Topico):

    def envioDeMensagem(self):
        raise NotImplementedError

    def respostaMensagem(self):
        raise NotImplementedError

    def enviaDLO(self):
        raise NotImplementedError
