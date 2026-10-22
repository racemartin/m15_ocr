"""
Cas d'usage (F3, métriques niveau conversation) : accumule l'état de
chaque conversation (nombre de tours, horodatage du premier tour) au fil
des entrées du journal, et émet des métriques UNE SEULE FOIS par
conversation, à sa clôture (événement "diagnostic") — jamais à chaque
tour individuel, contrairement à `ServiceInstrumentationJournal`.

Lit le MÊME fichier journal que `ServiceInstrumentationJournal`, mais
via un `LecteurJournalAudit` INDÉPENDANT (curseur distinct) : les deux
cas d'usage ne doivent jamais se partager un seul curseur, sinon l'un
des deux ne verrait jamais aucune entrée.
"""

from __future__ import annotations

from datetime import datetime

from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)
from chsa_triage_observabilite.domain.ports.accumulateur_conversations import (
    AccumulateurConversations,
)
from chsa_triage_observabilite.domain.ports.exportateur_metriques import (
    ExportateurMetriques,
)
from chsa_triage_observabilite.domain.ports.lecteur_journal_audit import (
    LecteurJournalAudit,
)
from tools.rafael.log_tool import LogTool

NOM_METRIQUE_NOMBRE_TOURS     = "chsa_conversation_nombre_tours"
NOM_METRIQUE_TEMPS_DIAGNOSTIC = "chsa_conversation_temps_diagnostic_secondes"
NOM_METRIQUE_REFORMULATION    = "chsa_conversation_reformulation_total"
NOM_METRIQUE_AVEC_ECHEC       = "chsa_conversation_avec_echec_total"


def _secondes_entre(horodatage_debut: str, horodatage_fin: str) -> float:
    debut = datetime.fromisoformat(horodatage_debut)
    fin   = datetime.fromisoformat(horodatage_fin)
    return (fin - debut).total_seconds()


class ServiceAnalyseConversations:
    """Accumule les tours par conversation et émet des métriques à la clôture."""

    def __init__(
        self,
        lecteur               : LecteurJournalAudit,
        accumulateur           : AccumulateurConversations,
        exportateur_metriques : ExportateurMetriques,
        etiquettes_globales   : dict[str, str] | None = None,
    ) -> None:
        self._lecteur               = lecteur
        self._accumulateur           = accumulateur
        self._exportateur_metriques = exportateur_metriques
        self._etiquettes_globales   = etiquettes_globales or {}
        self._log                   = LogTool(origin="application")

    # #########################################################################
    # Lit les nouvelles entrées et met à jour l'accumulateur ou émet des
    # métriques selon le type d'événement. Chronométré de bout en bout,
    # même discipline que les autres cas d'usage.
    # #########################################################################
    def executer(self) -> int:
        self._log.START_ACTION(
            "ServiceAnalyseConversations", "executer", "analyse des conversations"
        )

        entrees = self._lecteur.lire_nouvelles_entrees()
        nombre_conversations_cloturees = 0
        for entree in entrees:
            if self._traiter_entree(entree):
                nombre_conversations_cloturees += 1

        self._log.PARAMETER_VALUE("conversations_cloturees", nombre_conversations_cloturees)
        self._log.FINISH_ACTION(
            "ServiceAnalyseConversations",
            "executer",
            f"{nombre_conversations_cloturees} conversation(s) clôturée(s)",
        )
        return nombre_conversations_cloturees

    # -------------------------------------------------------------------------
    # Retourne True si cette entrée a effectivement clôturé une conversation
    # (utilisé seulement pour le compte-rendu, pas pour la logique elle-même).
    # -------------------------------------------------------------------------
    def _traiter_entree(self, entree: EntreeJournalAudit) -> bool:
        if entree.type_evenement == "tour_entretien":
            self._accumulateur.enregistrer_tour(entree.conversation_id, entree.horodatage)
            return False

        if entree.type_evenement == "echec_inference":
            self._accumulateur.enregistrer_echec(entree.conversation_id, entree.horodatage)
            return False

        if entree.type_evenement == "diagnostic_reformule":
            self._exportateur_metriques.incrementer_compteur(
                NOM_METRIQUE_REFORMULATION, dict(self._etiquettes_globales)
            )
            return False

        if entree.type_evenement == "diagnostic":
            etat = self._accumulateur.cloturer_conversation(entree.conversation_id)
            if etat is None:
                return False

            self._exportateur_metriques.observer_duree(
                NOM_METRIQUE_NOMBRE_TOURS,
                float(etat.nombre_tours),
                dict(self._etiquettes_globales),
            )
            self._exportateur_metriques.observer_duree(
                NOM_METRIQUE_TEMPS_DIAGNOSTIC,
                _secondes_entre(etat.horodatage_premier_tour, entree.horodatage),
                dict(self._etiquettes_globales),
            )
            self._exportateur_metriques.incrementer_compteur(
                NOM_METRIQUE_AVEC_ECHEC,
                {**self._etiquettes_globales, "avec_echec": str(etat.a_eu_un_echec)},
            )
            return True

        return False
