"""
Port générique (F0, pré-requis) : vérifier qu'une dépendance externe est
accessible avant d'aller plus loin. Chaque dépendance (Hugging Face Hub,
MLflow, API chsa-triage, Prometheus, Grafana...) a son propre adaptateur,
mais tous partagent ce même contrat, de la même façon que `JournalAudit`
dans le projet m14_ocr : le port ne sait pas où ni comment la vérification
est faite.
"""

from __future__ import annotations

from typing import Protocol

from chsa_triage_observabilite.domain.model.resultat_verification import (
    ResultatVerification,
)


class VerificateurConnectivite(Protocol):
    """Port générique : vérifier une dépendance externe, sans savoir laquelle."""

    def verifier(self) -> ResultatVerification:
        """Exécute la vérification et retourne son résultat, jamais une levée
        d'exception : un échec de connectivité est un résultat normal
        (`disponible=False`), pas une erreur du programme."""
        ...
