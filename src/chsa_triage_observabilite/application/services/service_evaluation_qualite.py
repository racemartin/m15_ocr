"""
Cas d'usage (F4, garde-fous) : fait évaluer chaque diagnostic par un
juge-LLM dédié (sécurité/forme, jamais l'exactitude clinique — voir
`docs/00_architecture.md` "Juge-LLM (F4)") et émet un score ainsi qu'une
alerte distincte sous un seuil.

GARDE-FOU RÉTROSPECTIF, PAS PRÉVENTIF : ce service lit le journal
d'audit APRÈS que chsa-triage a déjà répondu (même discipline de sondage
périodique que F2/F3) — il ne peut jamais bloquer ni corriger une réponse
avant qu'elle n'atteigne son destinataire. Sa valeur est la détection et
la traçabilité pour un superviseur (tendance, configuration en cause...),
jamais une intervention en temps réel.

Lit le MÊME fichier journal que `ServiceInstrumentationJournal`/
`ServiceAnalyseConversations`, via un `LecteurJournalAudit` INDÉPENDANT
(curseur distinct) : chaque cas d'usage lit le même fichier
indépendamment, jamais en partageant un seul curseur.
"""

from __future__ import annotations

from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)
from chsa_triage_observabilite.domain.ports.evaluateur_qualite import (
    EvaluateurQualite,
)
from chsa_triage_observabilite.domain.ports.exportateur_metriques import (
    ExportateurMetriques,
)
from chsa_triage_observabilite.domain.ports.lecteur_journal_audit import (
    LecteurJournalAudit,
)
from tools.rafael.log_tool import LogTool

NOM_METRIQUE_SCORE   = "chsa_garde_fou_score"
NOM_METRIQUE_ALERTE  = "chsa_garde_fou_alerte_total"
SEUIL_ALERTE_DEFAUT  = 5.0  # sur 10 ; sous ce score, le diagnostic est alerté


class ServiceEvaluationQualite:
    """Fait évaluer chaque diagnostic par le juge et émet score + alerte."""

    def __init__(
        self,
        lecteur               : LecteurJournalAudit,
        evaluateur             : EvaluateurQualite,
        exportateur_metriques : ExportateurMetriques,
        etiquettes_globales    : dict[str, str] | None = None,
        seuil_alerte           : float = SEUIL_ALERTE_DEFAUT,
    ) -> None:
        self._lecteur               = lecteur
        self._evaluateur             = evaluateur
        self._exportateur_metriques = exportateur_metriques
        self._etiquettes_globales   = etiquettes_globales or {}
        self._seuil_alerte           = seuil_alerte
        self._log                    = LogTool(origin="application")

    # #########################################################################
    # Lit les nouvelles entrées, évalue chaque diagnostic, émet le score et,
    # sous le seuil, une alerte distincte (compteur + log, jamais une
    # notification en temps réel au soignant — voir docstring du module).
    # #########################################################################
    def executer(self) -> int:
        self._log.START_ACTION(
            "ServiceEvaluationQualite", "executer", "evaluation des diagnostics (F4)"
        )

        entrees = self._lecteur.lire_nouvelles_entrees()
        nombre_evalues = 0
        for entree in entrees:
            if self._traiter_entree(entree):
                nombre_evalues += 1

        self._log.PARAMETER_VALUE("diagnostics_evalues", nombre_evalues)
        self._log.FINISH_ACTION(
            "ServiceEvaluationQualite",
            "executer",
            f"{nombre_evalues} diagnostic(s) evalue(s)",
        )
        return nombre_evalues

    # -------------------------------------------------------------------------
    def _traiter_entree(self, entree: EntreeJournalAudit) -> bool:
        if entree.type_evenement != "diagnostic" or not entree.sortie:
            return False

        resultat = self._evaluateur.evaluer(entree.sortie)
        if resultat is None:
            return False

        self._exportateur_metriques.observer_duree(
            NOM_METRIQUE_SCORE, resultat.score, dict(self._etiquettes_globales)
        )

        if resultat.score < self._seuil_alerte:
            self._exportateur_metriques.incrementer_compteur(
                NOM_METRIQUE_ALERTE, dict(self._etiquettes_globales)
            )
            self._log.LEVEL_5_WARNING(
                "ServiceEvaluationQualite",
                f"garde-fou sous le seuil (score={resultat.score}, "
                f"conversation_id={entree.conversation_id}) : "
                f"{resultat.justification}",
            )

        return True
