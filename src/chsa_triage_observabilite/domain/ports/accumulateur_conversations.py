"""
Port générique (F3, métriques niveau conversation) : accumuler l'état
d'une conversation en cours (nombre de tours, horodatage du premier
tour) à travers plusieurs cycles de lecture, et le restituer UNE SEULE
FOIS quand la conversation se clôture (réception d'un événement
"diagnostic"). Un seul contrat, indépendant de l'endroit où cet état
survit entre deux appels (fichier JSON local aujourd'hui).
"""

from __future__ import annotations

from typing import Protocol

from chsa_triage_observabilite.domain.model.etat_conversation_accumule import (
    EtatConversationAccumule,
)


class AccumulateurConversations(Protocol):
    """Port générique : accumuler puis restituer l'état d'une conversation."""

    def enregistrer_tour(self, conversation_id: str, horodatage: str) -> None:
        """Compte un tour d'entretien de plus pour cette conversation.
        Mémorise `horodatage` comme premier tour SEULEMENT si c'est le
        premier tour jamais enregistré pour cette conversation."""
        ...

    def enregistrer_echec(self, conversation_id: str, horodatage: str) -> None:
        """Marque cette conversation comme ayant eu au moins un échec
        d'inférence (C6). `horodatage` sert de repli pour
        `horodatage_premier_tour` si c'est le tout premier événement
        jamais vu pour cette conversation (ex. le premier message échoue
        avant tout tour réussi) : jamais une chaîne vide qui ferait
        planter un calcul de durée plus tard."""
        ...

    def cloturer_conversation(
        self, conversation_id: str
    ) -> EtatConversationAccumule | None:
        """Retire l'état accumulé de cette conversation et le retourne —
        appelé une seule fois, à la réception d'un événement "diagnostic".
        Retourne `None` si aucun tour n'a été enregistré pour cette
        conversation (ex. elle a commencé avant que ce service ne tourne) :
        jamais une valeur par défaut devinée."""
        ...
