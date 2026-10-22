"""
Cas d'usage (F2) : lire les nouvelles entrées du journal d'audit via un
`LecteurJournalAudit` et les convertir en métriques via un
`ExportateurMetriques`. Ne connaît ni le format du fichier, ni Prometheus
— seulement les deux ports, même discipline que
`ServiceVerificationEnvironnement`.
"""

from __future__ import annotations

from dataclasses import dataclass

from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)
from chsa_triage_observabilite.domain.ports.exportateur_metriques import (
    ExportateurMetriques,
)
from chsa_triage_observabilite.domain.ports.lecteur_journal_audit import (
    LecteurJournalAudit,
)
from tools.rafael.log_tool import LogTool

NOM_METRIQUE_ENTREES          = "chsa_journal_entrees_total"
NOM_METRIQUE_ERREURS          = "chsa_journal_erreurs_total"
NOM_METRIQUE_LATENCE          = "chsa_journal_latence_secondes"
NOM_METRIQUE_FORMAT_RESPECTE  = "chsa_diagnostic_format_respecte_total"
NOM_METRIQUE_TOKENS_SORTIE    = "chsa_journal_tokens_sortie"


@dataclass(frozen=True, slots=True)
class RapportInstrumentationJournal:
    """Combien d'entrées ont été traitées lors de cette exécution."""

    nombre_entrees : int


class ServiceInstrumentationJournal:
    """Lit les nouvelles entrées du journal et les enregistre comme métriques."""

    def __init__(
        self,
        lecteur               : LecteurJournalAudit,
        exportateur_metriques : ExportateurMetriques,
        etiquettes_globales   : dict[str, str] | None = None,
    ) -> None:
        self._lecteur               = lecteur
        self._exportateur_metriques = exportateur_metriques
        self._etiquettes_globales   = etiquettes_globales or {}
        self._log                   = LogTool(origin="application")

    # #########################################################################
    # Lit les nouvelles entrées et enregistre une métrique par entrée.
    # Chronométré de bout en bout (START_ACTION/FINISH_ACTION), même
    # discipline que `ServiceVerificationEnvironnement.executer()`.
    # #########################################################################
    def executer(self) -> RapportInstrumentationJournal:
        self._log.START_ACTION(
            "ServiceInstrumentationJournal", "executer", "lecture du journal d'audit"
        )

        entrees = self._lecteur.lire_nouvelles_entrees()
        for entree in entrees:
            self._enregistrer_metriques(entree)

        self._log.PARAMETER_VALUE("nombre_entrees", len(entrees))
        self._log.FINISH_ACTION(
            "ServiceInstrumentationJournal",
            "executer",
            f"{len(entrees)} entrée(s) traitée(s)",
        )
        return RapportInstrumentationJournal(nombre_entrees=len(entrees))

    # -------------------------------------------------------------------------
    # Traduit une entrée en un ou plusieurs points de métrique. Les clés de
    # `metadonnees` varient selon `type_evenement` (voir m14_ocr,
    # E4_00/E4_01_uc_*.py) : chaque métrique n'est enregistrée que si sa clé
    # est effectivement présente, jamais une valeur par défaut devinée.
    # -------------------------------------------------------------------------
    def _enregistrer_metriques(self, entree: EntreeJournalAudit) -> None:
        etiquettes_base = {
            "type_evenement": entree.type_evenement,
            **self._etiquettes_globales,
        }
        self._exportateur_metriques.incrementer_compteur(
            NOM_METRIQUE_ENTREES, etiquettes_base
        )

        if entree.type_evenement == "echec_inference":
            etiquettes = {
                **etiquettes_base,
                "type_erreur": str(entree.metadonnees.get("type_erreur", "inconnu")),
            }
            self._exportateur_metriques.incrementer_compteur(
                NOM_METRIQUE_ERREURS, etiquettes
            )
            return

        latence_ms = entree.metadonnees.get("latence_ms")
        if latence_ms is not None:
            self._exportateur_metriques.observer_duree(
                NOM_METRIQUE_LATENCE, latence_ms / 1000, etiquettes_base
            )

        # R2 (tour_entretien) et D3 (diagnostic) partagent la même métrique :
        # même champ brut (nombre_tokens_sortie), distingué en aval par
        # l'étiquette type_evenement déjà posée dans etiquettes_base.
        nombre_tokens_sortie = entree.metadonnees.get("nombre_tokens_sortie")
        if nombre_tokens_sortie is not None:
            self._exportateur_metriques.observer_duree(
                NOM_METRIQUE_TOKENS_SORTIE, float(nombre_tokens_sortie), etiquettes_base
            )

        if "format_respecte" in entree.metadonnees:
            etiquettes = {
                **etiquettes_base,
                "format_respecte": str(entree.metadonnees["format_respecte"]),
            }
            self._exportateur_metriques.incrementer_compteur(
                NOM_METRIQUE_FORMAT_RESPECTE, etiquettes
            )
