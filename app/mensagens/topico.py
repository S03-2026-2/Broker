from abc import ABC, abstractmethod


class Topico(ABC):

    @abstractmethod
    def envioDeMensagem(self):
        """Define o comportamento básico de uma mensagem."""
        pass
