"""
Point d'entrée CLI (F2) : lit les nouvelles entrées du journal d'audit de
m14_ocr (fichier local, même machine) et les enregistre comme métriques
Prometheus. Ponctuel (traite "ce qui est nouveau depuis la dernière fois"
puis s'arrête) : relancer périodiquement pour un suivi continu, jusqu'à
l'arrivée d'un endpoint `/metrics` persistant.

Usage :
    CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT=<chemin> CHSA_TRIAGE_CONFIGURATION=<config> \\
        uv run instrumenter-journal
"""

from __future__ import annotations

# Bibliothèques standard
import os
import sys
from pathlib import Path

# Lecture du .env
from dotenv import load_dotenv

# Cas d'usage
from chsa_triage_observabilite.application.services.service_instrumentation_journal import (
    ServiceInstrumentationJournal,
)

# Adaptateurs concrets
from chsa_triage_observabilite.infrastructure.adapters.jsonl_lecteur_journal_audit import (
    JsonlLecteurJournalAudit,
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


def _chemin_metriques(configuration: str | None) -> Path:
    """Même convention que `verifier_environnement.py` : un fichier par
    configuration, jamais partagé."""
    if configuration:
        return DOSSIER_METRIQUES / f"metriques_journal__{configuration}.prom"
    return DOSSIER_METRIQUES / "metriques_journal.prom"


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
    lecteur               = JsonlLecteurJournalAudit(chemin_journal)
    exportateur_metriques = PrometheusExportateurMetriques()

    rapport = ServiceInstrumentationJournal(
        lecteur, exportateur_metriques, etiquettes_globales
    ).executer()

    print("=" * LARGEUR_SEPARATEUR)
    print("INSTRUMENTATION DU JOURNAL D'AUDIT")
    print("=" * LARGEUR_SEPARATEUR)
    print(f"  Fichier lu...................: {chemin_journal}")
    print(f"  Configuration.................: {etiquettes_globales.get('configuration', '(aucune)')}")
    print(f"  Nouvelles entrées traitées....: {rapport.nombre_entrees}")
    print("=" * LARGEUR_SEPARATEUR)

    chemin_metriques = _chemin_metriques(etiquettes_globales.get("configuration"))
    chemin_metriques.parent.mkdir(parents=True, exist_ok=True)
    chemin_metriques.write_bytes(exportateur_metriques.exposer_texte())
    print(f"Métriques Prometheus écrites dans {chemin_metriques}")


if __name__ == "__main__":
    main()
