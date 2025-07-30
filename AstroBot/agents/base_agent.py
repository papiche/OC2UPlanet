import json
import os

class Agent:
    """
    Classe de base pour tous les agents.
    Chaque agent a accès à un état partagé et à un logger.
    """
    def __init__(self, shared_state):
        self.shared_state = shared_state
        self.logger = shared_state['logger']

    def run(self):
        """
        La méthode principale que chaque agent doit implémenter.
        C'est ici que la logique de l'agent est exécutée.
        """
        raise NotImplementedError("Chaque agent doit implémenter une méthode run().")

    def get_status(self):
        """
        Retourne le statut actuel de l'agent.
        """
        return self.shared_state['status'].get(self.__class__.__name__, "Inactif") 