"""
Point d'entrée CLI (F3) : analyse les conversations complètes (nombre de
tours avant diagnostic, temps jusqu'au diagnostic, taux de reformulation)
depuis le journal d'audit de m14_ocr. Ponctuel, même discipline que
`instrumenter-journal` : relancer périodiquement pour un suivi continu,
ou utiliser `servir-metriques` qui l'inclut déjà.

Utilise un curseur ET un fichier d'état DISTINCTS de ceux
d'`instrumenter-journal` (dérivés du même chemin de journal, suffixes
différents) : les deux cas d'usage lisent le même fichier indépendamment,
jamais en se partageant un seul curseur.

Usage :
    CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT=<chemin> CHSA_TRIAGE_CONFIGURATION=<config> \\
        uv run analyser-conversations
"""

from __future__ import annotations

# Bibliothèques standard
import os
import sys
from pathlib import Path

# Lecture du .env
from dotenv import load_dotenv

# Cas d'usage
from chsa_triage_observabilite.application.services.service_analyse_conversations import (
    ServiceAnalyseConversations,
)

# Adaptateurs concrets
from chsa_triage_observabilite.infrastructure.adapters.fichier_accumulateur_conversations import (
    FichierAccumulateurConversations,
)
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

SUFFIXE_CURSEUR_CONVERSATIONS = ".curseur_conversations"
SUFFIXE_ETAT_CONVERSATIONS    = ".conversations_en_cours.json"


def _chemin_metriques(configuration: str | None) -> Path:
    """Même convention que les autres CLI : un fichier par configuration."""
    if configuration:
        return DOSSIER_METRIQUES / f"metriques_conversations__{configuration}.prom"
    return DOSSIER_METRIQUES / "metriques_conversations.prom"


def construire_service_analyse_conversations(
    chemin_journal        : str,
    exportateur_metriques : PrometheusExportateurMetriques,
    etiquettes_globales    : dict[str, str],
) -> ServiceAnalyseConversations:
    """Fabrique partagée avec `servir_metriques.py` : construit le cas
    d'usage avec son curseur et son fichier d'état dédiés, dérivés du
    chemin du journal."""
    chemin = Path(chemin_journal)
    lecteur = JsonlLecteurJournalAudit(
        chemin, chemin_curseur=chemin.with_name(chemin.name + SUFFIXE_CURSEUR_CONVERSATIONS)
    )
    accumulateur = FichierAccumulateurConversations(
        chemin.with_name(chemin.name + SUFFIXE_ETAT_CONVERSATIONS)
    )
    return ServiceAnalyseConversations(
        lecteur, accumulateur, exportateur_metriques, etiquettes_globales
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
    service = construire_service_analyse_conversations(
        chemin_journal, exportateur_metriques, etiquettes_globales
    )

    nombre_cloturees = service.executer()

    print("=" * LARGEUR_SEPARATEUR)
    print("ANALYSE DES CONVERSATIONS")
    print("=" * LARGEUR_SEPARATEUR)
    print(f"  Fichier lu...................: {chemin_journal}")
    print(f"  Configuration.................: {etiquettes_globales.get('configuration', '(aucune)')}")
    print(f"  Conversations clôturées.......: {nombre_cloturees}")
    print("=" * LARGEUR_SEPARATEUR)

    chemin_metriques = _chemin_metriques(etiquettes_globales.get("configuration"))
    chemin_metriques.parent.mkdir(parents=True, exist_ok=True)
    chemin_metriques.write_bytes(exportateur_metriques.exposer_texte())
    print(f"Métriques Prometheus écrites dans {chemin_metriques}")


if __name__ == "__main__":
    main()
