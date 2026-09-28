from abc import ABC, abstractmethod


class Topico(ABC):

    @abstractmethod
    def envioDeMensagem(self):
        pass
