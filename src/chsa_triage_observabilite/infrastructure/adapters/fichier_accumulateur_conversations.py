"""
Adaptateur du port `AccumulateurConversations` : persiste l'état des
conversations en cours dans un petit fichier JSON local, même esprit que
le curseur de `JsonlLecteurJournalAudit` — l'état doit survivre entre
deux exécutions de `instrumenter-journal`, ou entre deux cycles de
`servir-metriques`.
"""

from __future__ import annotations

import json
from pathlib import Path

from chsa_triage_observabilite.domain.model.etat_conversation_accumule import (
    EtatConversationAccumule,
)
from tools.rafael.log_tool import LogTool


class FichierAccumulateurConversations:
    """Implémente `AccumulateurConversations` avec un fichier JSON local."""

    def __init__(self, chemin_etat: str | Path) -> None:
        self._chemin_etat = Path(chemin_etat)
        self._log         = LogTool(origin="infrastructure")

    # #########################################################################
    # Charge l'état courant, ajoute un tour (incrémente le compteur, fixe
    # l'horodatage du premier tour s'il n'existait pas), puis réécrit le
    # fichier en entier — un fichier JSON unique, pas un append-only.
    # #########################################################################
    def enregistrer_tour(self, conversation_id: str, horodatage: str) -> None:
        etat = self._charger()
        conversation = etat.get(conversation_id, self._nouvelle_conversation(horodatage))
        conversation["nombre_tours"] += 1
        etat[conversation_id] = conversation
        self._sauvegarder(etat)
        self._log.PARAMETER_VALUE(f"tour enregistré ({conversation_id[:8]}...)", conversation["nombre_tours"])

    # #########################################################################
    # Marque un échec pour cette conversation (C6), en créant l'entrée si
    # c'est le tout premier événement vu pour elle (ex. le premier message
    # échoue avant tout tour réussi).
    # #########################################################################
    def enregistrer_echec(self, conversation_id: str, horodatage: str) -> None:
        etat = self._charger()
        conversation = etat.get(conversation_id, self._nouvelle_conversation(horodatage))
        conversation["a_eu_un_echec"] = True
        etat[conversation_id] = conversation
        self._sauvegarder(etat)

    # #########################################################################
    # Retire l'état de cette conversation (clôture) et le retourne. `None`
    # si la conversation n'a jamais eu de tour enregistré par CE service
    # (ex. elle a commencé avant son premier lancement).
    # #########################################################################
    def cloturer_conversation(
        self, conversation_id: str
    ) -> EtatConversationAccumule | None:
        etat = self._charger()
        conversation = etat.pop(conversation_id, None)
        self._sauvegarder(etat)

        if conversation is None:
            self._log.LEVEL_5_WARNING(
                "FichierAccumulateurConversations",
                f"conversation {conversation_id[:8]}... clôturée sans tour connu",
            )
            return None

        return EtatConversationAccumule(
            nombre_tours            = conversation["nombre_tours"],
            horodatage_premier_tour = conversation["horodatage_premier_tour"],
            a_eu_un_echec           = conversation.get("a_eu_un_echec", False),
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def _nouvelle_conversation(horodatage: str) -> dict:
        return {
            "nombre_tours"            : 0,
            "horodatage_premier_tour" : horodatage,
            "a_eu_un_echec"           : False,
        }

    def _charger(self) -> dict:
        if not self._chemin_etat.exists():
            return {}
        try:
            return json.loads(self._chemin_etat.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _sauvegarder(self, etat: dict) -> None:
        self._chemin_etat.parent.mkdir(parents=True, exist_ok=True)
        self._chemin_etat.write_text(json.dumps(etat), encoding="utf-8")
