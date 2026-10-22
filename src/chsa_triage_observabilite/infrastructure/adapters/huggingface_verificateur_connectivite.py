"""
Adaptateur du port `VerificateurConnectivite` : vérifie l'accès au Hugging
Face Hub (authentification du token, et optionnellement l'existence d'un
dataset précis, ex. le futur dataset de journal d'audit `hf_dataset`).
"""

from __future__ import annotations

import time

# Client Hugging Face
from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

# Modèle de domaine
from chsa_triage_observabilite.domain.model.resultat_verification import (
    ResultatVerification,
)

# Journalisation
from tools.rafael.log_tool import LogTool


class HuggingFaceVerificateurConnectivite:
    """Implémente `VerificateurConnectivite` pour le Hugging Face Hub.

    `depot_dataset` est optionnel : si fourni, vérifie aussi que ce dataset
    précis existe et est accessible avec le token fourni (pas seulement que
    le token est valide en général)."""

    def __init__(self, token: str | None, depot_dataset: str | None = None) -> None:
        self._token         = token
        self._depot_dataset = depot_dataset
        self._log           = LogTool(origin="infrastructure")

    # #########################################################################
    # Vérifie le token, puis optionnellement l'accès à un dataset précis.
    # Jamais de levée d'exception : un échec de connectivité est un résultat
    # normal (`disponible=False`), pas une erreur du programme.
    # #########################################################################
    def verifier(self) -> ResultatVerification:
        self._log.START_CALL_MANAGER_FUNCTION(
            "HuggingFaceVerificateurConnectivite", "verifier", "début"
        )
        self._log.PARAMETER_VALUE("depot_dataset", self._depot_dataset or "(aucun)")
        debut = time.perf_counter()

        if not self._token:
            resultat = ResultatVerification(
                nom        = "Hugging Face Hub",
                disponible = False,
                detail     = "HF_TOKEN absent (voir .env.example)",
                duree_ms   = 0.0,
            )
            self._log.FINISH_CALL_MANAGER_FUNCTION(
                "HuggingFaceVerificateurConnectivite", "verifier", resultat.detail
            )
            return resultat

        api = HfApi(token=self._token)
        try:
            info_utilisateur = api.whoami()
        except HfHubHTTPError as erreur:
            duree_ms = (time.perf_counter() - debut) * 1000
            resultat = ResultatVerification(
                nom        = "Hugging Face Hub",
                disponible = False,
                detail     = f"Token invalide ou expiré : {erreur}",
                duree_ms   = duree_ms,
            )
            self._log.FINISH_CALL_MANAGER_FUNCTION(
                "HuggingFaceVerificateurConnectivite", "verifier", resultat.detail
            )
            return resultat

        # --- Vérification optionnelle d'un dataset précis -------------------
        if self._depot_dataset:
            try:
                api.dataset_info(self._depot_dataset)
            except HfHubHTTPError as erreur:
                duree_ms = (time.perf_counter() - debut) * 1000
                resultat = ResultatVerification(
                    nom        = "Hugging Face Hub",
                    disponible = False,
                    detail     = (
                        f"Token valide ({info_utilisateur['name']}) mais "
                        f"dataset '{self._depot_dataset}' inaccessible : {erreur}"
                    ),
                    duree_ms   = duree_ms,
                )
                self._log.FINISH_CALL_MANAGER_FUNCTION(
                    "HuggingFaceVerificateurConnectivite", "verifier", resultat.detail
                )
                return resultat

        duree_ms = (time.perf_counter() - debut) * 1000
        resultat = ResultatVerification(
            nom        = "Hugging Face Hub",
            disponible = True,
            detail     = f"Connecté en tant que '{info_utilisateur['name']}'",
            duree_ms   = duree_ms,
        )
        self._log.FINISH_CALL_MANAGER_FUNCTION(
            "HuggingFaceVerificateurConnectivite", "verifier", resultat.detail
        )
        return resultat
