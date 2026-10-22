"""
Cas d'usage (F0) : exécuter une liste de `VerificateurConnectivite` et
agréger leurs résultats. Ne connaît aucun adaptateur concret, seulement le
port, même discipline que le reste de `application/` (orchestration pure,
zéro détail d'infrastructure).
"""

from __future__ import annotations

from dataclasses import dataclass

# Modèle et ports de domaine
from chsa_triage_observabilite.domain.model.resultat_verification import (
    ResultatVerification,
)
from chsa_triage_observabilite.domain.ports.exportateur_metriques import (
    ExportateurMetriques,
)
from chsa_triage_observabilite.domain.ports.verificateur_connectivite import (
    VerificateurConnectivite,
)

# Journalisation
from tools.rafael.log_tool import LogTool

NOM_METRIQUE_DISPONIBILITE = "chsa_verification_dependance_disponible"
NOM_METRIQUE_DUREE         = "chsa_verification_dependance_duree_secondes"


@dataclass(frozen=True, slots=True)
class RapportVerificationEnvironnement:
    """Résultat global : tous les résultats individuels, plus un verdict."""

    resultats  : list[ResultatVerification]
    tout_dispo : bool  # True seulement si CHAQUE dépendance est disponible


class ServiceVerificationEnvironnement:
    """Exécute chaque vérificateur enregistré et agrège le verdict final."""

    def __init__(
        self,
        verificateurs: list[VerificateurConnectivite],
        exportateur_metriques: ExportateurMetriques | None = None,
        etiquettes_globales: dict[str, str] | None = None,
    ) -> None:
        """`etiquettes_globales` (ex. `{"configuration": "staging1_local_gguf"}`)
        est fusionnée dans CHAQUE métrique émise par cette exécution, jamais
        déduite automatiquement : m15 audite depuis l'extérieur, par HTTP,
        et n'a aucun accès au processus réel de m14_ocr pour deviner sa
        configuration (encore moins dans le cas d'un Space HF distant).
        C'est à l'appelant de la fournir, comme pour toute étiquette d'un
        scrape Prometheus classique."""
        self._verificateurs         = verificateurs
        self._exportateur_metriques = exportateur_metriques
        self._etiquettes_globales   = etiquettes_globales or {}
        self._log                   = LogTool(origin="application")

    # #########################################################################
    # Exécute chaque vérificateur enregistré et retourne le rapport agrégé.
    # Chronométré de bout en bout (START_ACTION/FINISH_ACTION) pour détecter
    # une dépendance anormalement lente sans attendre le dashboard Grafana.
    # `exportateur_metriques` est optionnel : sans lui, ce cas d'usage se
    # comporte exactement comme avant (compatible avec le CLI F0 existant).
    # #########################################################################
    def executer(self) -> RapportVerificationEnvironnement:
        self._log.START_ACTION(
            "ServiceVerificationEnvironnement",
            "executer",
            f"{len(self._verificateurs)} vérificateur(s) à exécuter",
        )

        # --- Exécution séquentielle de chaque vérificateur enregistré --------
        resultats = [v.verifier() for v in self._verificateurs]

        # --- Export métriques, un point de donnée par dépendance vérifiée ----
        for resultat in resultats:
            self._enregistrer_metriques(resultat)

        # --- Agrégation du verdict final --------------------------------------
        rapport = RapportVerificationEnvironnement(
            resultats  = resultats,
            tout_dispo = all(r.disponible for r in resultats),
        )

        self._log.PARAMETER_VALUE("tout_dispo", rapport.tout_dispo)
        self._log.FINISH_ACTION(
            "ServiceVerificationEnvironnement",
            "executer",
            f"tout_dispo={rapport.tout_dispo}",
        )
        return rapport

    # -------------------------------------------------------------------------
    # Enregistre un résultat individuel dans l'exportateur de métriques, s'il
    # y en a un. Jamais appelé si `exportateur_metriques` est absent.
    # -------------------------------------------------------------------------
    def _enregistrer_metriques(self, resultat: ResultatVerification) -> None:
        if self._exportateur_metriques is None:
            return

        etiquettes = {
            "nom": resultat.nom,
            "disponible": str(resultat.disponible),
            **self._etiquettes_globales,
        }
        self._exportateur_metriques.incrementer_compteur(
            NOM_METRIQUE_DISPONIBILITE, etiquettes
        )
        self._exportateur_metriques.observer_duree(
            NOM_METRIQUE_DUREE,
            resultat.duree_ms / 1000,
            {"nom": resultat.nom, **self._etiquettes_globales},
        )
