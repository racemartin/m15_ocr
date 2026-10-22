"""
Adaptateur générique du port `VerificateurConnectivite` : vérifie qu'une
URL HTTP répond, avec un code attendu. Réutilisable pour toute dépendance
qui s'exprime comme "un endpoint doit répondre" (API chsa-triage `/sante`,
MLflow, Prometheus `/-/healthy`, Grafana `/api/health`...), sans dupliquer
cette logique à chaque fois, même esprit que `JsonlJournalAudit` dans
m14_ocr : un seul mécanisme, réutilisé par plusieurs appelants.
"""

from __future__ import annotations

import time

# E/S et réseau
import httpx

# Modèle de domaine
from chsa_triage_observabilite.domain.model.resultat_verification import (
    ResultatVerification,
)

# Journalisation
from tools.rafael.log_tool import LogTool


class UrlVerificateurConnectivite:
    """Implémente `VerificateurConnectivite` pour un endpoint HTTP simple."""

    def __init__(
        self,
        nom                : str,
        url                : str,
        en_tetes           : dict[str, str] | None = None,
        code_attendu       : int = 200,
        delai_max_secondes : float = 5.0,
    ) -> None:
        self._nom                = nom
        self._url                = url
        self._en_tetes           = en_tetes or {}
        self._code_attendu       = code_attendu
        self._delai_max_secondes = delai_max_secondes
        self._log                = LogTool(origin="infrastructure")

    # #########################################################################
    # Appelle l'URL configurée et compare le code HTTP reçu au code attendu.
    # Jamais de levée d'exception : une erreur réseau devient un résultat
    # `disponible=False`, pas un plantage du programme appelant.
    # #########################################################################
    def verifier(self) -> ResultatVerification:
        self._log.START_CALL_MANAGER_FUNCTION(
            "UrlVerificateurConnectivite", "verifier", f"nom={self._nom}"
        )
        self._log.PARAMETER_VALUE("url", self._url)
        debut = time.perf_counter()

        try:
            reponse = httpx.get(
                self._url,
                headers = self._en_tetes,
                timeout = self._delai_max_secondes,
            )
        except httpx.RequestError as erreur:
            duree_ms = (time.perf_counter() - debut) * 1000
            resultat = ResultatVerification(
                nom        = self._nom,
                disponible = False,
                detail     = f"Injoignable ({self._url}) : {erreur}",
                duree_ms   = duree_ms,
            )
            self._log.FINISH_CALL_MANAGER_FUNCTION(
                "UrlVerificateurConnectivite", "verifier", resultat.detail
            )
            return resultat

        duree_ms = (time.perf_counter() - debut) * 1000

        if reponse.status_code != self._code_attendu:
            resultat = ResultatVerification(
                nom        = self._nom,
                disponible = False,
                detail     = (
                    f"Code HTTP {reponse.status_code} reçu, "
                    f"{self._code_attendu} attendu ({self._url})"
                ),
                duree_ms   = duree_ms,
            )
            self._log.FINISH_CALL_MANAGER_FUNCTION(
                "UrlVerificateurConnectivite", "verifier", resultat.detail
            )
            return resultat

        resultat = ResultatVerification(
            nom        = self._nom,
            disponible = True,
            detail     = f"Répond en {duree_ms:.0f} ms ({self._url})",
            duree_ms   = duree_ms,
        )
        self._log.FINISH_CALL_MANAGER_FUNCTION(
            "UrlVerificateurConnectivite", "verifier", resultat.detail
        )
        return resultat
