"""
Point d'entrée CLI (mécanisme de scraping continu) : sert les métriques
Prometheus sur un endpoint HTTP `/metrics` en continu, au lieu d'un
instantané ponctuel écrit sur disque (`verifier-environnement`,
`instrumenter-journal`). Prometheus peut alors scraper directement cette
URL à intervalle régulier, construisant une vraie série temporelle.

Un SEUL registre Prometheus, créé une fois au démarrage, jamais recréé à
chaque sondage : sinon chaque compteur "repartirait de zéro" à chaque
cycle, cassant la sémantique monotone croissante qu'attend Prometheus
d'un compteur (voir `PrometheusExportateurMetriques.registre`).

Usage :
    uv run servir-metriques
    # Prometheus scrape alors http://<host>:<port>/metrics en continu.

Variables d'environnement :
- `CHSA_PORT_METRIQUES` (défaut 9200) : port HTTP du endpoint `/metrics`.
- `CHSA_INTERVALLE_SONDAGE_SECONDES` (défaut 30) : fréquence à laquelle
  ce processus relit lui-même ses sources (vérificateurs de connectivité,
  journal d'audit), PAS la fréquence à laquelle Prometheus scrape — ce
  processus garde toujours la dernière valeur connue entre deux sondages.
"""

from __future__ import annotations

# Bibliothèques standard
import os
import time

# Lecture du .env
from dotenv import load_dotenv

# Serveur HTTP Prometheus natif
from prometheus_client import start_http_server

# Cas d'usage
from chsa_triage_observabilite.application.services.service_instrumentation_journal import (
    ServiceInstrumentationJournal,
)
from chsa_triage_observabilite.application.services.service_verification_environnement import (
    ServiceVerificationEnvironnement,
)

# Adaptateurs concrets
from chsa_triage_observabilite.infrastructure.adapters.jsonl_lecteur_journal_audit import (
    JsonlLecteurJournalAudit,
)
from chsa_triage_observabilite.infrastructure.adapters.prometheus_exportateur_metriques import (
    PrometheusExportateurMetriques,
)

# Fabrique commune (composition root partagée entre points d'entrée)
from chsa_triage_observabilite.interfaces.cli.analyser_conversations import (
    construire_service_analyse_conversations,
)
from chsa_triage_observabilite.interfaces.cli.fabrique_adaptateurs import (
    construire_etiquettes_globales,
    construire_verificateurs,
)
from tools.rafael.log_tool import LogTool

PORT_METRIQUES_PAR_DEFAUT               = 9200
INTERVALLE_SONDAGE_SECONDES_PAR_DEFAUT  = 30

log = LogTool(origin="interfaces")


# #############################################################################
# Un seul cycle de sondage : réexécute les deux cas d'usage existants contre
# le MÊME exportateur persistant. Chaque appel accumule dans le registre
# plutôt que de repartir de zéro — c'est tout l'intérêt de ce point d'entrée
# par rapport aux deux CLI ponctuels.
# #############################################################################
def _sonder_une_fois(
    verificateurs,
    lecteur_journal,
    service_analyse_conversations,
    exportateur_metriques,
    etiquettes_globales,
) -> None:
    if verificateurs:
        ServiceVerificationEnvironnement(
            verificateurs, exportateur_metriques, etiquettes_globales
        ).executer()

    if lecteur_journal is not None:
        ServiceInstrumentationJournal(
            lecteur_journal, exportateur_metriques, etiquettes_globales
        ).executer()

    if service_analyse_conversations is not None:
        service_analyse_conversations.executer()


def main() -> None:
    load_dotenv()

    port       = int(os.environ.get("CHSA_PORT_METRIQUES", PORT_METRIQUES_PAR_DEFAUT))
    intervalle = int(
        os.environ.get(
            "CHSA_INTERVALLE_SONDAGE_SECONDES", INTERVALLE_SONDAGE_SECONDES_PAR_DEFAUT
        )
    )
    chemin_journal = os.environ.get("CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT")

    etiquettes_globales   = construire_etiquettes_globales()
    verificateurs         = construire_verificateurs()
    exportateur_metriques = PrometheusExportateurMetriques()
    lecteur_journal        = JsonlLecteurJournalAudit(chemin_journal) if chemin_journal else None
    service_analyse_conversations = (
        construire_service_analyse_conversations(
            chemin_journal, exportateur_metriques, etiquettes_globales
        )
        if chemin_journal
        else None
    )

    start_http_server(port, registry=exportateur_metriques.registre)

    log.STEP(
        1,
        "Serveur de métriques démarré",
        f"port={port}, intervalle={intervalle}s",
    )
    log.PARAMETER_VALUE("configuration", etiquettes_globales.get("configuration", "(aucune)"))
    log.PARAMETER_VALUE("verificateurs", len(verificateurs))
    log.PARAMETER_VALUE("lecteur_journal", "oui" if lecteur_journal else "non (CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT absente)")
    log.PARAMETER_VALUE("analyse_conversations", "oui" if service_analyse_conversations else "non")
    print(f"Métriques servies en continu sur http://0.0.0.0:{port}/metrics (Ctrl+C pour arrêter)")

    while True:
        _sonder_une_fois(
            verificateurs,
            lecteur_journal,
            service_analyse_conversations,
            exportateur_metriques,
            etiquettes_globales,
        )
        time.sleep(intervalle)


if __name__ == "__main__":
    main()
