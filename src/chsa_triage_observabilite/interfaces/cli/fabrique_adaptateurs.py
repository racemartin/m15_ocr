"""
Fabrique commune (composition root) aux points d'entrée CLI : construit
les adaptateurs concrets à partir de `.env`, pour ne pas dupliquer cette
logique à chaque nouveau point d'entrée (`verifier_environnement`,
`instrumenter_journal`, `servir_metriques`...). Seule couche, avec les
CLI eux-mêmes, qui lit `os.environ` directement.
"""

from __future__ import annotations

import os

from chsa_triage_observabilite.domain.ports.verificateur_connectivite import (
    VerificateurConnectivite,
)
from chsa_triage_observabilite.infrastructure.adapters.huggingface_verificateur_connectivite import (
    HuggingFaceVerificateurConnectivite,
)
from chsa_triage_observabilite.infrastructure.adapters.url_verificateur_connectivite import (
    UrlVerificateurConnectivite,
)


def construire_verificateurs() -> list[VerificateurConnectivite]:
    """Construit un vérificateur par dépendance EFFECTIVEMENT configurée dans
    `.env`. Une dépendance absente du `.env` est silencieusement ignorée ici
    (pas encore nécessaire à ce stade du projet), jamais levée en erreur."""
    verificateurs: list[VerificateurConnectivite] = []

    # --- Hugging Face Hub (dataset du journal d'audit, HF Jobs) -------------
    jeton_hf = os.environ.get("HF_TOKEN")
    if jeton_hf:
        verificateurs.append(
            HuggingFaceVerificateurConnectivite(
                token         = jeton_hf,
                depot_dataset = os.environ.get("CHSA_JOURNAL_AUDIT_REPO"),
            )
        )

    # --- API chsa-triage (le système audité, m14_ocr) ------------------------
    # Une seule URL DE BASE, locale ou distante (Space HF) : c'est la même
    # variable dans les deux cas, jamais un "mode" séparé à maintenir ici.
    url_base_chsa = os.environ.get("CHSA_TRIAGE_URL_BASE")
    if url_base_chsa:
        verificateurs.append(
            UrlVerificateurConnectivite(
                nom = "API chsa-triage (/sante)",
                url = f"{url_base_chsa.rstrip('/')}/sante",
            )
        )

    # --- MLflow (suivi d'expérimentation, réutilisé du m14_ocr) --------------
    url_mlflow = os.environ.get("MLFLOW_TRACKING_URI")
    if url_mlflow:
        verificateurs.append(
            UrlVerificateurConnectivite(nom="MLflow", url=f"{url_mlflow}/health")
        )

    return verificateurs


def construire_etiquettes_globales() -> dict[str, str]:
    """Étiquette "configuration", déclarée dans `.env` par l'opérateur — voir
    `.env.example` pour les 4 valeurs reprises du diagramme de déploiement
    de m14_ocr. Absente si `CHSA_TRIAGE_CONFIGURATION` n'est pas renseignée,
    jamais une valeur par défaut devinée."""
    configuration = os.environ.get("CHSA_TRIAGE_CONFIGURATION")
    return {"configuration": configuration} if configuration else {}
