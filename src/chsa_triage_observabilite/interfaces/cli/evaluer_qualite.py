"""
Point d'entrée CLI (F4, garde-fous) : fait évaluer chaque diagnostic du
journal d'audit de m14_ocr par un juge-LLM LOCAL et DÉDIÉ (jamais le même
modèle que celui audité). Ponctuel, même discipline que
`analyser-conversations` : relancer périodiquement pour un suivi continu,
ou utiliser `servir-metriques` qui l'inclut déjà.

GARDE-FOU RÉTROSPECTIF, PAS PRÉVENTIF (voir
`service_evaluation_qualite.py`) : ce CLI lit des diagnostics déjà
délivrés, il ne bloque jamais rien en temps réel.

Utilise un curseur DISTINCT de celui d'`instrumenter-journal`/
`analyser-conversations` (dérivé du même chemin de journal, suffixe
différent) : chaque cas d'usage lit le même fichier indépendamment.

Usage :
    CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT=<chemin> CHSA_JUGE_URL_BASE=<url> \\
        uv run evaluer-qualite
"""

from __future__ import annotations

# Bibliothèques standard
import os
import sys
from pathlib import Path

# Lecture du .env
from dotenv import load_dotenv

# Cas d'usage
from chsa_triage_observabilite.application.services.service_evaluation_qualite import (
    SEUIL_ALERTE_DEFAUT,
    ServiceEvaluationQualite,
)

# Adaptateurs concrets
from chsa_triage_observabilite.infrastructure.adapters.jsonl_lecteur_journal_audit import (
    JsonlLecteurJournalAudit,
)
from chsa_triage_observabilite.infrastructure.adapters.llama_server_evaluateur_qualite import (
    LlamaServerEvaluateurQualite,
)
from chsa_triage_observabilite.infrastructure.adapters.prometheus_exportateur_metriques import (
    PrometheusExportateurMetriques,
)

# Fabrique commune (composition root partagée entre points d'entrée)
from chsa_triage_observabilite.interfaces.cli.fabrique_adaptateurs import (
    construire_etiquettes_globales,
)

LARGEUR_SEPARATEUR = 80
DOSSIER_METRIQUES  = Path("data")

SUFFIXE_CURSEUR_QUALITE = ".curseur_qualite"

URL_JUGE_PAR_DEFAUT               = "http://127.0.0.1:8001"
DELAI_MAX_JUGE_SECONDES_PAR_DEFAUT = 60.0


def _chemin_metriques(configuration: str | None) -> Path:
    """Même convention que les autres CLI : un fichier par configuration."""
    if configuration:
        return DOSSIER_METRIQUES / f"metriques_qualite__{configuration}.prom"
    return DOSSIER_METRIQUES / "metriques_qualite.prom"


def construire_service_evaluation_qualite(
    chemin_journal        : str,
    exportateur_metriques : PrometheusExportateurMetriques,
    etiquettes_globales    : dict[str, str],
) -> ServiceEvaluationQualite:
    """Fabrique partagée avec `servir_metriques.py` : construit le cas
    d'usage avec son curseur dédié et son adaptateur juge, dérivés des
    variables d'environnement."""
    chemin = Path(chemin_journal)
    lecteur = JsonlLecteurJournalAudit(
        chemin, chemin_curseur=chemin.with_name(chemin.name + SUFFIXE_CURSEUR_QUALITE)
    )
    evaluateur = LlamaServerEvaluateurQualite(
        url_base           = os.environ.get("CHSA_JUGE_URL_BASE", URL_JUGE_PAR_DEFAUT),
        delai_max_secondes = float(
            os.environ.get(
                "CHSA_JUGE_DELAI_MAX_SECONDES", DELAI_MAX_JUGE_SECONDES_PAR_DEFAUT
            )
        ),
    )
    seuil_alerte = float(os.environ.get("CHSA_JUGE_SEUIL_ALERTE", SEUIL_ALERTE_DEFAUT))
    return ServiceEvaluationQualite(
        lecteur, evaluateur, exportateur_metriques, etiquettes_globales, seuil_alerte
    )


def main() -> None:
    load_dotenv()

    chemin_journal = os.environ.get("CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT")
    if not chemin_journal:
        print(
            "CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT doit être définie "
            "(chemin local vers le .jsonl de m14_ocr à lire)."
        )
        sys.exit(1)

    etiquettes_globales   = construire_etiquettes_globales()
    exportateur_metriques = PrometheusExportateurMetriques()
    service = construire_service_evaluation_qualite(
        chemin_journal, exportateur_metriques, etiquettes_globales
    )

    nombre_evalues = service.executer()

    print("=" * LARGEUR_SEPARATEUR)
    print("EVALUATION QUALITE (F4, garde-fous -- juge-LLM)")
    print("=" * LARGEUR_SEPARATEUR)
    print(f"  Fichier lu...................: {chemin_journal}")
    print(f"  Juge..........................: {os.environ.get('CHSA_JUGE_URL_BASE', URL_JUGE_PAR_DEFAUT)}")
    print(f"  Configuration.................: {etiquettes_globales.get('configuration', '(aucune)')}")
    print(f"  Diagnostics evalues............: {nombre_evalues}")
    print("=" * LARGEUR_SEPARATEUR)

    chemin_metriques = _chemin_metriques(etiquettes_globales.get("configuration"))
    chemin_metriques.parent.mkdir(parents=True, exist_ok=True)
    chemin_metriques.write_bytes(exportateur_metriques.exposer_texte())
    print(f"Métriques Prometheus écrites dans {chemin_metriques}")


if __name__ == "__main__":
    main()
